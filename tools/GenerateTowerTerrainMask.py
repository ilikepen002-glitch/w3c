#!/usr/bin/env python3
"""Deterministically derive tower terrain/pathing from the reviewed source map.

    python3 tools/GenerateTowerTerrainMask.py --write
    python3 tools/GenerateTowerTerrainMask.py --check

The immutable Git object is the input, never the already-masked working copy.
Only the WPM build restriction and its four-byte MPQ attribute CRC may change.
W3E and every other game member are preserved byte-for-byte. The tiny MPQ writer
appends replacement WPM/attribute blocks, retargets those block-table records and
updates archive length; it does not rewrite terrain or depend on a World Editor
export. Python standard library only.
"""

import argparse
import bz2
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "4d69ea31a95d296138b0fd88c503c3ae701f2704"
MAP_PATH = "maps/ExampleMap.source.w3x"
WURST_PATH = "wurst/towers/TDTowerTerrainMask.wurst"
TGA_PATH = "imports/war3mapImported/TDTower192.tga"
MANIFEST_PATH = "maps/tower-terrain-mask.json"
CELL_SIZE = 32
ORIGIN = -4096
GRID_SIZE = 256
PLATEAU_LAYER = 1
HEIGHT_DELTA = 8.0
UNWALKABLE = 0x02
UNBUILDABLE = 0x08
NO_WATER = 0x40  # A SET bit means dry ground, not water.
EXIT = (-384, -448, 352, 64)
MARGIN = 32
P1_POINTS = tuple((x, y) for y in (1792, 2304)
                  for x in (-2432, -2240, -2048, -1856, -1664))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def baseline_bytes():
    return subprocess.check_output(
        ["git", "show", f"{BASELINE}:{MAP_PATH}"], cwd=ROOT)


def crypt_table():
    table, seed = [0] * 0x500, 0x100001
    for i in range(256):
        for j in range(5):
            seed = (seed * 125 + 3) % 0x2AAAAB
            high = (seed & 65535) << 16
            seed = (seed * 125 + 3) % 0x2AAAAB
            table[j * 256 + i] = high | (seed & 65535)
    return table


CRYPT = crypt_table()


def mpq_hash(value, kind):
    a, b = 0x7FED7FED, 0xEEEEEEEE
    for c in value.upper().encode("ascii"):
        a = (CRYPT[kind * 256 + c] ^ (a + b)) & 0xFFFFFFFF
        b = (c + a + b + (b << 5) + 3) & 0xFFFFFFFF
    return a


def crypt(data, key, encrypt=False):
    """MPQ encryption is word-based; any trailing bytes remain unchanged."""
    out, seed = bytearray(), 0xEEEEEEEE
    count = len(data) // 4 * 4
    for (word,) in struct.iter_unpack("<I", data[:count]):
        seed = (seed + CRYPT[0x400 + (key & 255)]) & 0xFFFFFFFF
        decoded = word if encrypt else word ^ ((key + seed) & 0xFFFFFFFF)
        encoded = word ^ ((key + seed) & 0xFFFFFFFF) if encrypt else decoded
        out.extend(struct.pack("<I", encoded))
        key = (((~key << 21) + 0x11111111) | (key >> 11)) & 0xFFFFFFFF
        seed = (decoded + seed + (seed << 5) + 3) & 0xFFFFFFFF
    return bytes(out) + data[count:]


class Mpq:
    """Minimal v0 reader; deliberately rejects unsupported compression/flags."""

    def __init__(self, data):
        self.data = data
        self.offset = data.index(b"MPQ\x1a")
        self.archive = data[self.offset:]
        (_, header, size, version, shift, ht, bt, hn, bn) = struct.unpack_from(
            "<4sIIHHIIII", self.archive)
        assert version == 0 and header == 32, "Only reviewed MPQ v0 supported"
        assert size <= len(self.archive)
        self.sector_size, self.bt = 512 << shift, bt
        self.hashes = list(struct.iter_unpack("<IIHHI", crypt(
            self.archive[ht:ht + hn * 16], mpq_hash("(hash table)", 3))))
        self.block_bytes = crypt(self.archive[bt:bt + bn * 16],
                                 mpq_hash("(block table)", 3))
        self.blocks = list(struct.iter_unpack("<IIII", self.block_bytes))

    def block_index(self, name):
        for a, b, _locale, _platform, index in self.hashes:
            if a == mpq_hash(name, 1) and b == mpq_hash(name, 2):
                if index < len(self.blocks):
                    return index
        raise KeyError(name)

    def has(self, name):
        try:
            self.block_index(name)
            return True
        except KeyError:
            return False

    @staticmethod
    def unpack(data, size):
        if len(data) == size:
            return data
        if data[0] == 2:
            result = zlib.decompress(data[1:])
        elif data[0] == 16:
            result = bz2.decompress(data[1:])
        else:
            raise ValueError(f"Unsupported MPQ compression {data[0]:#x}")
        assert len(result) == size
        return result

    def extract(self, name):
        pos, packed, size, flags = self.blocks[self.block_index(name)]
        data = self.archive[pos:pos + packed]
        assert flags & 0x80000000 and not flags & 0x100, "Invalid/imploded file"
        encrypted = bool(flags & 0x10000)
        key = mpq_hash(name.replace("/", "\\").split("\\")[-1], 3)
        if flags & 0x20000:
            key = ((key + pos) ^ size) & 0xFFFFFFFF
        if flags & 0x1000000:
            if encrypted:
                data = crypt(data, key)
            return self.unpack(data, size) if flags & 0x200 else data
        if flags & 0x200:
            count = (size + self.sector_size - 1) // self.sector_size
            offsets = data[:(count + 1) * 4]
            if encrypted:
                offsets = crypt(offsets, (key - 1) & 0xFFFFFFFF)
            offsets = struct.unpack("<" + "I" * (count + 1), offsets)
            parts = []
            for i in range(count):
                part = data[offsets[i]:offsets[i + 1]]
                if encrypted:
                    part = crypt(part, (key + i) & 0xFFFFFFFF)
                parts.append(self.unpack(part, min(self.sector_size,
                                                   size - i * self.sector_size)))
            return b"".join(parts)
        assert not encrypted, "Uncompressed encrypted sectors unsupported"
        return data

    def members(self):
        names = self.extract("(listfile)").decode("utf-8").splitlines()
        names += ["(listfile)", "(attributes)", "(signature)"]
        return {name: self.extract(name) for name in sorted(set(names))
                if name and self.has(name)}

    def replace_wpm(self, replacement):
        # Appending leaves the original terrain, imports, headers and member
        # payloads intact, including unknown members absent from the listfile.
        attributes = bytearray(self.extract("(attributes)"))
        assert struct.unpack_from("<II", attributes) == (100, 3)
        assert len(attributes) == 8 + len(self.blocks) * 12
        # The attribute record's own CRC is conventionally zero (otherwise it
        # would be self-referential). Keep every timestamp and other CRC intact.
        assert struct.unpack_from("<I", attributes, 8 + self.block_index("(attributes)") * 4)[0] == 0
        struct.pack_into("<I", attributes, 8 + self.block_index("war3map.wpm") * 4,
                         zlib.crc32(replacement))
        replacements = {"war3map.wpm": replacement, "(attributes)": attributes}
        out = bytearray(self.data)
        blocks = bytearray(self.block_bytes)
        for name, data in replacements.items():
            payload = b"\x02" + zlib.compress(data, 9)
            flags = 0x81000200  # Existing, single unit, zlib compression.
            if len(payload) >= len(data):
                payload, flags = data, 0x81000000
            struct.pack_into("<IIII", blocks, self.block_index(name) * 16,
                             len(out) - self.offset, len(payload), len(data), flags)
            out.extend(payload)
        start = self.offset + self.bt
        out[start:start + len(blocks)] = crypt(
            blocks, mpq_hash("(block table)", 3), encrypt=True)
        struct.pack_into("<I", out, self.offset + 8, len(out) - self.offset)
        return bytes(out)


def terrain(data):
    assert data[:4] == b"W3E!"
    offset = 13
    for _ in range(2):
        count = struct.unpack_from("<I", data, offset)[0]
        offset += 4 + count * 4
    width, height, ox, oy = struct.unpack_from("<IIff", data, offset)
    offset += 16
    assert (width, height, ox, oy) == (65, 65, ORIGIN, ORIGIN)
    assert len(data) == offset + width * height * 7
    vertices = []
    for pos in range(offset, len(data), 7):
        layer = data[pos + 6] & 15
        ground = struct.unpack_from("<H", data, pos)[0]
        vertices.append((layer, (ground - 8192) / 4 + (layer - 2) * 128))
    quads = []
    for y in range(height - 1):
        row = []
        for x in range(width - 1):
            corners = [vertices[(y + dy) * width + x + dx]
                       for dy in (0, 1) for dx in (0, 1)]
            heights = [v[1] for v in corners]
            row.append((all(v[0] == PLATEAU_LAYER for v in corners),
                        min(heights), max(heights)))
        quads.append(row)
    return quads


def make_mask(w3e, wpm):
    magic, version, width, height = struct.unpack_from("<4sIII", wpm)
    assert (magic, version, width, height) == (b"MP3W", 0, GRID_SIZE, GRID_SIZE)
    assert len(wpm) == 16 + width * height
    quads = terrain(w3e)
    base = []
    for y in range(height):
        row = []
        for x in range(width):
            flags = wpm[16 + y * width + x]
            plateau, low, high = quads[y // 4][x // 4]
            row.append(plateau and high - low <= HEIGHT_DELTA
                       and flags & (UNWALKABLE | UNBUILDABLE) == 0
                       and flags & NO_WATER != 0)
        base.append(row)
    result = [[False] * width for _ in range(height)]
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            # Exactly one erosion cell. Runtime checks the actual footprint;
            # it must not apply this terrain margin a second time.
            eligible = all(base[y + dy][x + dx]
                           for dy in (-1, 0, 1) for dx in (-1, 0, 1))
            left, bottom = ORIGIN + x * CELL_SIZE, ORIGIN + y * CELL_SIZE
            overlaps_exit = (left < EXIT[2] + MARGIN
                             and left + CELL_SIZE > EXIT[0] - MARGIN
                             and bottom < EXIT[3] + MARGIN
                             and bottom + CELL_SIZE > EXIT[1] - MARGIN)
            result[y][x] = eligible and not overlaps_exit
    return result, base, quads


def bands(values):
    result = []
    for y, value in enumerate(values):
        if result and result[-1][2] == value:
            result[-1] = (result[-1][0], y + 1, value)
        else:
            result.append((y, y + 1, value))
    return result


def binary_rows(rows, render, indent="\t"):
    if len(rows) == 1:
        return render(rows[0][2], indent)
    mid = len(rows) // 2
    return (f"{indent}if cellY < {rows[mid][0]}\n"
            + binary_rows(rows[:mid], render, indent + "\t")
            + f"{indent}else\n"
            + binary_rows(rows[mid:], render, indent + "\t"))


def wurst(mask, quads, w3e, wpm):
    lines = ["package TDTowerTerrainMask", "",
             "// Generated by tools/GenerateTowerTerrainMask.py; do not hand edit.",
             f"// Immutable source: {BASELINE}:{MAP_PATH}",
             f"// W3E SHA-256: {sha(w3e)}",
             f"// Original WPM SHA-256: {sha(wpm)}",
             "// Raw W3E plateau layer 1; no runtime cliff-level offset assumption.",
             "// One 32-unit terrain/exit margin is already baked into eligibility.",
             "// Binary row dispatch has no arrays, initialization loops or handles.",
             "public constant real TD_TERRAIN_ORIGIN_X = -4096.0",
             "public constant real TD_TERRAIN_ORIGIN_Y = -4096.0",
             "public constant real TD_TERRAIN_CELL_SIZE = 32.0",
             "public constant int TD_TERRAIN_CELLS_X = 256",
             "public constant int TD_TERRAIN_CELLS_Y = 256", "",
             "function tdTerrainMaskRow(int cellY) returns string"]
    rows = ["".join("1" if v else "0" for v in row) for row in mask]
    lines.append(binary_rows(bands(rows), lambda value, ind: f'{ind}return "{value}"\n').rstrip())
    lines += ["", "public function tdTerrainCellBuildable(int cellX, int cellY) returns boolean",
              "\tif cellX < 0 or cellY < 0 or cellX >= TD_TERRAIN_CELLS_X or cellY >= TD_TERRAIN_CELLS_Y",
              "\t\treturn false",
              '\treturn SubString(tdTerrainMaskRow(cellY), cellX, cellX + 1) == "1"', ""]
    for title, index in (("Min", 1), ("Max", 2)):
        # Height APIs are source-quad extrema, for cells whose eligibility has
        # already been checked. Ineligible cells deliberately carry no promise.
        heights = []
        for y in range(GRID_SIZE):
            exceptions = tuple((x, quads[y // 4][x // 4][index])
                               for x in range(GRID_SIZE)
                               if mask[y][x] and quads[y // 4][x // 4][index] != -128.0)
            heights.append(exceptions)
        def render_height(exceptions, ind):
            ranges = []
            for x, value in exceptions:
                if ranges and ranges[-1][1] == x and ranges[-1][2] == value:
                    ranges[-1] = (ranges[-1][0], x + 1, value)
                else:
                    ranges.append((x, x + 1, value))
            result = ""
            for start, end, value in ranges:
                test = f"cellX == {start}" if end == start + 1 else f"cellX >= {start} and cellX < {end}"
                result += f"{ind}if {test}\n{ind}\treturn {value}\n"
            return result + f"{ind}return -128.0\n"
        lines += ["// Call only after tdTerrainCellBuildable succeeds; source quad extrema.",
                  f"public function tdTerrainCell{title}Height(int cellX, int cellY) returns real",
                  binary_rows(bands(heights), render_height).rstrip(), ""]
    return ("\n".join(lines)).encode()


def tga():
    # Uncompressed 24-bit TGA, 6x6 texels, bottom-left origin; BGR pixels.
    # R=255 blocks walking, B=255 blocks building, G=0 preserves flying.
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, 6, 6, 24, 0)
    return header + bytes((255, 0, 255)) * 36


def footprint_allowed(mask, x, y):
    """Conservative exact [center-96, center+96) cell intersection reference."""
    import math
    x0, y0 = math.floor((x - 96 - ORIGIN) / 32), math.floor((y - 96 - ORIGIN) / 32)
    x1, y1 = math.ceil((x + 96 - ORIGIN) / 32), math.ceil((y + 96 - ORIGIN) / 32)
    return (0 <= x0 < x1 <= GRID_SIZE and 0 <= y0 < y1 <= GRID_SIZE
            and all(mask[yy][xx] for yy in range(y0, y1) for xx in range(x0, x1)))


def generate():
    original = baseline_bytes()
    archive = Mpq(original)
    w3e, wpm = archive.extract("war3map.w3e"), archive.extract("war3map.wpm")
    mask, base, quads = make_mask(w3e, wpm)
    updated = bytearray(wpm)
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            if not mask[y][x]:
                updated[16 + y * GRID_SIZE + x] |= UNBUILDABLE
    for x, y in P1_POINTS:
        assert footprint_allowed(mask, x, y), f"Approved P1 footprint rejected: {x},{y}"
    patched = archive.replace_wpm(updated)
    before, after = archive.members(), Mpq(patched).members()
    assert before.keys() == after.keys()
    assert all(after[name] == value for name, value in before.items()
               if name not in ("war3map.wpm", "(attributes)"))
    assert after["war3map.wpm"] == updated
    crc_offset = 8 + archive.block_index("war3map.wpm") * 4
    attributes = bytearray(before["(attributes)"])
    struct.pack_into("<I", attributes, crc_offset, zlib.crc32(updated))
    assert after["(attributes)"] == attributes
    manifest = {
        "generator": "tools/GenerateTowerTerrainMask.py", "baseline_commit": BASELINE,
        "baseline_map_sha256": sha(original), "terrain_sha256": sha(w3e),
        "original_pathing_sha256": sha(wpm), "generated_pathing_sha256": sha(updated),
        "generated_map_sha256": sha(patched),
        "attributes_metadata_exception": {
            "purpose": "Update only the changed WPM member's CRC32",
            "crc_offset": crc_offset, "changed_bytes_maximum": 4,
            "original_sha256": sha(before["(attributes)"]),
            "generated_sha256": sha(after["(attributes)"]),
        },
        "origin": [ORIGIN, ORIGIN], "cell_size": CELL_SIZE,
        "pathing_dimensions": [GRID_SIZE, GRID_SIZE], "raw_plateau_layer": PLATEAU_LAYER,
        "max_quad_height_delta": HEIGHT_DELTA, "edge_margin": MARGIN,
        "shared_exit_rect": list(EXIT), "eligible_cells": sum(map(sum, mask)),
        "added_unbuildable_cells": sum(a != b for a, b in zip(wpm, updated)),
        "unchanged_member_sha256": {name: sha(value) for name, value in before.items()
                                    if name not in ("war3map.wpm", "(attributes)")},
        "approved_p1_centers": [list(point) for point in P1_POINTS],
    }
    return {MAP_PATH: patched, WURST_PATH: wurst(mask, quads, w3e, wpm),
            TGA_PATH: tga(), MANIFEST_PATH: (json.dumps(manifest, indent=2) + "\n").encode()}


def assert_reviewed_source(current_bytes, generated_bytes):
    """Reject unrelated edits rather than silently resetting them to baseline."""
    current = Mpq(current_bytes).members()
    original = Mpq(baseline_bytes()).members()
    generated = Mpq(generated_bytes).members()
    assert current.keys() == original.keys(), "Source map member list changed"
    assert current["war3map.wpm"] in (original["war3map.wpm"], generated["war3map.wpm"]), "Unreviewed WPM changes"
    for name in original:
        if name == "war3map.wpm":
            continue
        elif name == "(attributes)":
            expected = original[name] if current["war3map.wpm"] == original["war3map.wpm"] else generated[name]
            assert current[name] == expected, "Unreviewed MPQ attribute changes"
        else:
            assert current[name] == original[name], f"Unreviewed source map change: {name}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = generate()
    if args.write:
        # Do not silently overwrite any unrelated terrain/map edits.
        assert_reviewed_source((ROOT / MAP_PATH).read_bytes(), outputs[MAP_PATH])
        for name, data in outputs.items():
            path = ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        print("Wrote deterministic terrain mask, WPM, manifest and native 6x6 texture")
    else:
        for name, expected in outputs.items():
            assert (ROOT / name).read_bytes() == expected, f"Stale generated artifact: {name}"
        print("PASS: terrain mask artifacts match immutable baseline regeneration")


if __name__ == "__main__":
    main()
