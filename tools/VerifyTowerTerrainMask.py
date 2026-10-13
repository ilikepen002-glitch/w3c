#!/usr/bin/env python3
"""Source-map/texture regression tests; run with Python 3 standard library only."""

import math
import re
import struct
import unittest
import zlib

import GenerateTowerTerrainMask as g


class TowerTerrainMaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_bytes = g.baseline_bytes()
        cls.original = g.Mpq(cls.original_bytes)
        cls.source_bytes = (g.ROOT / g.MAP_PATH).read_bytes()
        cls.source = g.Mpq(cls.source_bytes)
        cls.w3e = cls.original.extract("war3map.w3e")
        cls.wpm = cls.original.extract("war3map.wpm")
        cls.mask, cls.base, cls.quads = g.make_mask(cls.w3e, cls.wpm)
        cls.outputs = g.generate()

    def at(self, matrix, x, y):
        return matrix[math.floor((y - g.ORIGIN) / 32)][math.floor((x - g.ORIGIN) / 32)]

    def test_pinned_source_identity(self):
        self.assertEqual(g.sha(self.original_bytes),
                         "627a64c012dcc46e1b5acc48dcbb20eeca0b465093718800799a2df37ded0b5e")
        self.assertEqual(g.sha(self.w3e),
                         "997468b2761ae013507a2696cdb1deb1644b8fd1c1e4cecb4d5da26ffee1f087")

    def test_terrain_and_all_other_members_unchanged(self):
        before, after = self.original.members(), self.source.members()
        self.assertEqual(before.keys(), after.keys())
        self.assertEqual(len(before), 18)
        for name in before:
            if name not in ("war3map.wpm", "(attributes)"):
                self.assertEqual(before[name], after[name], name)

    def test_only_wpm_attribute_crc_changed_and_matches_new_payload(self):
        before = self.original.extract("(attributes)")
        after = self.source.extract("(attributes)")
        offset = 8 + self.original.block_index("war3map.wpm") * 4
        self.assertEqual(before[:offset], after[:offset])
        self.assertEqual(before[offset + 4:], after[offset + 4:])
        self.assertEqual(struct.unpack_from("<I", before, offset)[0], zlib.crc32(self.wpm))
        self.assertEqual(struct.unpack_from("<I", after, offset)[0],
                         zlib.crc32(self.source.extract("war3map.wpm")))

    def test_only_unbuildable_bit_added_and_walking_unchanged(self):
        actual = self.source.extract("war3map.wpm")
        self.assertEqual(actual[:16], self.wpm[:16])
        self.assertEqual(len(actual), len(self.wpm))
        changes = 0
        for i, (before, after) in enumerate(zip(self.wpm[16:], actual[16:])):
            self.assertEqual(before & ~0x08, after & ~0x08)
            self.assertEqual(before & after, before)
            self.assertEqual(after, before if self.mask[i // 256][i % 256] else before | 8)
            changes += before != after
        self.assertEqual(changes, 7424)
        self.assertEqual(sum(map(sum, self.mask)), 24324)

    def test_append_writer_preserves_unknown_payloads_and_other_block_records(self):
        # This also covers MPQ members that a future listfile might not name.
        original_prefix, actual_prefix = bytearray(self.original_bytes), bytearray(self.source_bytes[:len(self.original_bytes)])
        header_length = self.original.offset + 8
        actual_prefix[header_length:header_length + 4] = original_prefix[header_length:header_length + 4]
        start = self.original.offset + self.original.bt
        actual_prefix[start:start + len(self.original.block_bytes)] = original_prefix[start:start + len(self.original.block_bytes)]
        self.assertEqual(actual_prefix, original_prefix)
        indices = {self.original.block_index(name) for name in ("war3map.wpm", "(attributes)")}
        for i, (before, after) in enumerate(zip(self.original.blocks, self.source.blocks)):
            if i not in indices:
                self.assertEqual(before, after)

    def test_dry_land_polarity_and_all_quad_corners(self):
        self.assertTrue(self.at(self.mask, -2048, 2048))
        for y, row in enumerate(self.base):
            for x, accepted in enumerate(row):
                if accepted:
                    flags = self.wpm[16 + y * 256 + x]
                    self.assertEqual(flags & 0x0A, 0)
                    self.assertTrue(flags & 0x40)  # NO_WATER must be SET.
                    plateau, low, high = self.quads[y // 4][x // 4]
                    self.assertTrue(plateau)
                    self.assertLessEqual(high - low, g.HEIGHT_DELTA)

    def test_road_perimeter_steep_slope_and_exit_rejected(self):
        for x, y in [(-2320, 2672), (-2368, -3136), (-3600, 3600),
                     (-4032, -4032), (0, -192), (0, 0)]:
            with self.subTest(x=x, y=y):
                self.assertFalse(self.at(self.mask, x, y))
                self.assertFalse(g.footprint_allowed(self.mask, x, y))
        self.assertTrue(self.at(self.mask, -960, -1216))  # Gentle 6.5-unit slope remains allowed.

    def test_exactly_one_cell_margin_everywhere(self):
        removed_edge, retained_edge = 0, 0
        for y in range(256):
            for x in range(256):
                in_bounds = 0 < x < 255 and 0 < y < 255
                neighbors = (in_bounds and all(self.base[yy][xx]
                    for yy in range(y - 1, y + 2) for xx in range(x - 1, x + 2)))
                left, bottom = -4096 + x * 32, -4096 + y * 32
                outside_exit = left >= 384 or left + 32 <= -416 or bottom >= 96 or bottom + 32 <= -480
                self.assertEqual(self.mask[y][x], bool(neighbors and outside_exit))
                removed_edge += self.base[y][x] and not neighbors
                if self.mask[y][x] and 1 < x < 254 and 1 < y < 254:
                    retained_edge += any(not self.base[yy][xx]
                        for yy in range(y - 2, y + 3) for xx in range(x - 2, x + 3))
        self.assertGreater(removed_edge, 0)
        self.assertGreater(retained_edge, 0)  # A second erosion would reject these.

    def test_ten_approved_full_192_footprints_and_free_placement(self):
        self.assertEqual(len(g.P1_POINTS), 10)
        for x, y in g.P1_POINTS:
            self.assertTrue(g.footprint_allowed(self.mask, x, y), (x, y))
            cells = [self.quads[cy // 4][cx // 4]
                     for cy in range((y - 96 + 4096) // 32, (y + 96 + 4096) // 32)
                     for cx in range((x - 96 + 4096) // 32, (x + 96 + 4096) // 32)]
            self.assertEqual(len(cells), 36)
            self.assertLessEqual(max(q[2] for q in cells) - min(q[1] for q in cells), 8)
        self.assertTrue(g.footprint_allowed(self.mask, -2017, 2047))
        self.assertFalse(g.footprint_allowed(self.mask, -4096, 2048))

    def test_half_open_exact_edge_footprint(self):
        synthetic = [[False] * 256 for _ in range(256)]
        for y in range(100, 106):
            for x in range(100, 106):
                synthetic[y][x] = True
        center = -4096 + 103 * 32
        self.assertTrue(g.footprint_allowed(synthetic, center, center))
        self.assertFalse(g.footprint_allowed(synthetic, center + 0.01, center))
        self.assertFalse(g.footprint_allowed(synthetic, center - 0.01, center))

    def test_solid_six_by_six_magenta_tga(self):
        data = (g.ROOT / g.TGA_PATH).read_bytes()
        self.assertEqual(struct.unpack("<BBBHHBHHHHBB", data[:18]),
                         (0, 0, 2, 0, 0, 0, 0, 0, 6, 6, 24, 0))
        self.assertEqual(len(data), 18 + 36 * 3)
        self.assertEqual(data[18:], bytes((255, 0, 255)) * 36)

    def test_static_binary_lookup_and_height_values_match_every_cell(self):
        source = (g.ROOT / g.WURST_PATH).read_text()
        self.assertNotRegex(source, r"(?m)^(init|.*\barray\b|\s+while|\s+for )$")
        def interpret_generated_function(name, args):
            # The generated bodies contain only binary if/else and literals.
            body = re.search(rf"(?:public )?function {name}\([^\n]+\n((?:\t[^\n]*\n)+)", source).group(1)
            body = "\n".join(line + ":" if line.lstrip().startswith("if ") or line.strip() == "else" else line
                             for line in body.splitlines())
            namespace = {}
            exec(f"def lookup({args}):\n" + body.expandtabs(4), namespace)
            return namespace["lookup"]
        row = interpret_generated_function("tdTerrainMaskRow", "cellY")
        low = interpret_generated_function("tdTerrainCellMinHeight", "cellX, cellY")
        high = interpret_generated_function("tdTerrainCellMaxHeight", "cellX, cellY")
        for y in range(256):
            self.assertEqual(row(y), "".join("1" if b else "0" for b in self.mask[y]))
            for x in range(256):
                if self.mask[y][x]:
                    self.assertEqual((low(x, y), high(x, y)), self.quads[y // 4][x // 4][1:])

    def test_natural_relief_uses_same_limit_for_full_footprint(self):
        def permitted(limit, x=-2048, y=896):
            mask, _, quads = g.make_mask(self.w3e, self.wpm, limit)
            cx, cy = (x + 4096) // 32, (y + 4096) // 32
            cells = [quads[yy // 4][xx // 4]
                     for yy in range(cy - 3, cy + 3) for xx in range(cx - 3, cx + 3)]
            delta = max(q[2] for q in cells) - min(q[1] for q in cells)
            self.assertEqual(delta, 54.75)
            return g.footprint_allowed(mask, x, y) and delta <= limit
        for limit in (8, 16, 32, 48):
            self.assertFalse(permitted(limit))
        self.assertTrue(permitted(64))
        source = (g.ROOT / g.WURST_PATH).read_text()
        self.assertIn(f"TD_TERRAIN_MAX_HEIGHT_DELTA = {g.HEIGHT_DELTA}", source)
        runtime = (g.ROOT / "wurst/towers/TDTowerPlacementRules.wurst").read_text()
        self.assertIn("highest - lowest > TD_TERRAIN_MAX_HEIGHT_DELTA", runtime)

    def test_new_open_cells_clear_old_generated_bit_only(self):
        previous = g.Mpq(g.generate(8.0)[g.MAP_PATH]).extract("war3map.wpm")
        actual = self.source.extract("war3map.wpm")
        cleared = 0
        for i, (old, new, original) in enumerate(zip(previous[16:], actual[16:], self.wpm[16:])):
            self.assertEqual(old & ~8, new & ~8)
            if old != new:
                self.assertEqual(old, new | 8)
                self.assertEqual(new, original)
                self.assertFalse(original & (g.UNWALKABLE | g.UNBUILDABLE))
                self.assertTrue(original & g.NO_WATER)
                self.assertTrue(self.quads[(i // 256) // 4][(i % 256) // 4][0])
                cleared += 1
        self.assertEqual(cleared, 2340)
        g.assert_reviewed_source(g.generate(8.0)[g.MAP_PATH], self.outputs[g.MAP_PATH])

    def test_reproducible_and_idempotent_outputs(self):
        for name, expected in self.outputs.items():
            self.assertEqual((g.ROOT / name).read_bytes(), expected, name)
        g.assert_reviewed_source(self.original_bytes, self.outputs[g.MAP_PATH])
        g.assert_reviewed_source(self.source_bytes, self.outputs[g.MAP_PATH])

    def test_unrelated_build_bit_edit_is_rejected(self):
        extra = bytearray(self.source.extract("war3map.wpm"))
        for i, flags in enumerate(extra[16:], 16):
            if not flags & 8:
                extra[i] |= 8
                break
        unreviewed = self.source.replace_wpm(extra)
        with self.assertRaisesRegex(AssertionError, "Unreviewed WPM changes"):
            g.assert_reviewed_source(unreviewed, self.outputs[g.MAP_PATH])


if __name__ == "__main__":
    unittest.main(verbosity=2)
