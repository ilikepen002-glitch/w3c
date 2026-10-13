#!/usr/bin/env python3
"""Generate/check conservative ground-item eligibility without modifying the map.

Only the newly introduced Wurst mask and JSON manifest can be written. The
reviewed source W3X, W3E, WPM, W3R and existing tower artifacts are read-only.
Python standard library only; optional --reference-npz checks the review data.
"""
import argparse
import ast
from collections import deque
import io
import json
import math
from pathlib import Path
import struct
import zipfile

from GenerateTowerTerrainMask import Mpq, bands, binary_rows, sha

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = "maps/ExampleMap.source.w3x"
WURST_PATH = "wurst/items/TDGroundItemTerrainMask.wurst"
MANIFEST_PATH = "maps/ground-item-terrain-mask.json"
REVIEWED_HASHES = {
    "map": "3fd31a78aaa5d017565fca6c6f3758d40ed6131999c701bdf1f99557ba39e408",
    "war3map.w3e": "997468b2761ae013507a2696cdb1deb1644b8fd1c1e4cecb4d5da26ffee1f087",
    "war3map.wpm": "f03db9fe3a24936718f3e9e4de1b3dc878527ad7d598d78ced7239a431d98d49",
    "war3map.w3r": "6fb69963bcaa599f4932cc7ead21699bad8aa18a5be9cc866330144abb2107b5",
}
ORIGIN, CELL_SIZE, GRID_SIZE = -4096, 32, 256
CENTRAL_PROTECTION = (-1024, -768, 1024, 896)  # [left,right) x [bottom,top)
EXPECTED_LANE_COUNTS = (1824, 1552, 1600, 1664)
UNWALKABLE, DRY = 0x02, 0x40
MAX_SAFE_HEIGHT_DELTA = 8.0


def terrain_vertices(data):
    assert data[:4] == b"W3E!", "Invalid W3E signature"
    offset = 13
    for _ in range(2):
        count = struct.unpack_from("<I", data, offset)[0]
        offset += 4 + 4 * count
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
            layers = {layer for layer, _ in corners}
            heights = [height for _, height in corners]
            row.append((next(iter(layers)) if len(layers) == 1 else -1,
                        max(heights) - min(heights)))
        quads.append(row)
    return vertices, quads


def regions(data):
    version, count = struct.unpack_from("<II", data)
    assert version == 5, "Only reviewed W3R version 5 supported"
    offset, result = 8, {}
    for _ in range(count):
        bounds = struct.unpack_from("<ffff", data, offset)
        offset += 16
        end = data.index(b"\0", offset)
        name = data[offset:end].decode("utf-8")
        offset = end + 1 + 8  # Name terminator, region index and weather ID.
        end = data.index(b"\0", offset)  # Ambient sound filename.
        offset = end + 1 + 4  # Color.
        assert name not in result, "Duplicate source region"
        result[name] = bounds
    assert offset == len(data), "Unparsed W3R bytes"
    return result


def lane_at(x, y):
    return (0 if y >= 0 else 3) if x < 0 else (1 if y >= 0 else 2)


def protected(x, y):
    left, bottom, right, top = CENTRAL_PROTECTION
    return left <= x < right and bottom <= y < top


def cell_at(x, y):
    return math.floor((x - ORIGIN) / CELL_SIZE), math.floor((y - ORIGIN) / CELL_SIZE)


def source_lane(mask, x, y):
    cx, cy = cell_at(x, y)
    return mask[cy][cx] if 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE else -1


def safe_layer_at(safe, x, y):
    cx, cy = cell_at(x, y)
    return safe[cy][cx] if 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE else -1


def pile_position(lane, group, index):
    x = -768 if lane == 0 else -1024 if lane == 3 else 1024
    y = 2560 - (group - 1) * 256 if lane <= 1 else -2816 + (group - 1) * 256
    cell = index % 15
    return x + (cell % 5 - 2) * 32, y + (cell // 5 - 1) * 32


def derive(w3e, wpm, w3r):
    vertices, quads = terrain_vertices(w3e)
    magic, version, width, height = struct.unpack_from("<4sIII", wpm)
    assert (magic, version, width, height) == (b"MP3W", 0, GRID_SIZE, GRID_SIZE)
    assert len(wpm) == 16 + width * height
    pathing = wpm[16:]
    low, safe = [], []
    for y in range(height):
        low_row, safe_row = [], []
        for x in range(width):
            flags = pathing[y * width + x]
            layer, delta = quads[y // 4][x // 4]
            walk_dry = flags & UNWALKABLE == 0 and flags & DRY != 0
            # Source eligibility is positive raw lowland membership. The build
            # bit is deliberately irrelevant: this is not a build-mask inverse.
            low_row.append(layer == 0 and walk_dry)
            safe_row.append(layer if layer in (0, 1) and walk_dry
                            and delta <= MAX_SAFE_HEIGHT_DELTA else -1)
        low.append(low_row)
        safe.append(safe_row)
    source = [[-1] * width for _ in range(height)]
    seeds, bounds = [], []
    source_regions = regions(w3r)
    for lane in range(4):
        left, bottom, right, top = source_regions[f"td_spawn_p{lane + 1}"]
        seed = cell_at((left + right) / 2, (bottom + top) / 2)
        seeds.append(seed)
        def eligible(x, y):
            if not (0 <= x < width and 0 <= y < height):
                return False
            px, py = ORIGIN + x * CELL_SIZE, ORIGIN + y * CELL_SIZE
            return low[y][x] and lane_at(px, py) == lane and not protected(px, py)
        assert eligible(*seed), f"Lane {lane} source seed rejected"
        queue = deque([seed])
        source[seed[1]][seed[0]] = lane
        cells = []
        while queue:
            x, y = queue.popleft()
            cells.append((x, y))
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if eligible(nx, ny) and source[ny][nx] == -1:
                    source[ny][nx] = lane
                    queue.append((nx, ny))
        assert len(cells) == EXPECTED_LANE_COUNTS[lane], f"Unreviewed lane {lane} mask count"
        bounds.append((ORIGIN + min(x for x, _ in cells) * CELL_SIZE,
                       ORIGIN + min(y for _, y in cells) * CELL_SIZE,
                       ORIGIN + (max(x for x, _ in cells) + 1) * CELL_SIZE,
                       ORIGIN + (max(y for _, y in cells) + 1) * CELL_SIZE))
    return source, safe, seeds, bounds, vertices, pathing


def wurst(source, safe, bounds):
    lines = ["package TDGroundItemTerrainMask", "",
             "// Generated by tools/GenerateGroundItemTerrainMask.py; do not hand edit.",
             "// Reads reviewed source terrain/pathing/regions; never modifies map assets."]
    lines += [f"// {name} SHA-256: {digest}" for name, digest in REVIEWED_HASHES.items()]
    lines += ["// Source: raw layer 0, four equal-layer corners, static walkable dry ground,",
              "// four-neighbor-connected to this lane's spawn, excluding the central merger.",
              "// Safe item point: raw layer 0/1, same corners, walkable dry, height delta <= 8.",
              "// Positive source/destination masks; buildability and item ownership are irrelevant.",
              "// Half-open 32-unit cells; mixed layers and unknown/out-of-map points are rejected.",
              "// Binary row dispatch needs no initialization loops, arrays or rect handles.",
              "public constant real TD_GROUND_TERRAIN_ORIGIN = -4096.0",
              "public constant real TD_GROUND_TERRAIN_CELL_SIZE = 32.0",
              "public constant int TD_GROUND_TERRAIN_CELLS = 256", ""]
    for name, mask in (("tdGroundSourceMaskRow", source), ("tdGroundSafeLayerRow", safe)):
        lines.append(f"function {name}(int cellY) returns string")
        rows = ["".join(str(value) if value >= 0 else "-" for value in row) for row in mask]
        lines.append(binary_rows(bands(rows), lambda value, ind: f'{ind}return "{value}"\n').rstrip())
        lines.append("")
    lines += ["function tdGroundTerrainCell(real coordinate) returns int",
              "\treturn ((coordinate - TD_GROUND_TERRAIN_ORIGIN) / TD_GROUND_TERRAIN_CELL_SIZE).floor()", "",
              "function tdGroundTerrainCellInMap(int cellX, int cellY) returns boolean",
              "\treturn cellX >= 0 and cellY >= 0 and cellX < TD_GROUND_TERRAIN_CELLS and cellY < TD_GROUND_TERRAIN_CELLS", "",
              "public function tdGroundSortSourceLane(real x, real y) returns int",
              "\tlet cellX = tdGroundTerrainCell(x)", "\tlet cellY = tdGroundTerrainCell(y)",
              "\tif not tdGroundTerrainCellInMap(cellX, cellY)", "\t\treturn -1",
              "\tlet value = SubString(tdGroundSourceMaskRow(cellY), cellX, cellX + 1)"]
    for lane in range(4):
        lines += [f'\tif value == "{lane}"', f"\t\treturn {lane}"]
    lines += ["\treturn -1", "",
              "public function tdGroundPointSafeForItem(real x, real y) returns boolean",
              "\tlet cellX = tdGroundTerrainCell(x)", "\tlet cellY = tdGroundTerrainCell(y)",
              "\tif not tdGroundTerrainCellInMap(cellX, cellY)", "\t\treturn false",
              '\treturn SubString(tdGroundSafeLayerRow(cellY), cellX, cellX + 1) != "-"', "",
              "public function tdGroundSortDestinationAllowed(int lane, real x, real y) returns boolean",
              "\tif lane < 0 or lane >= 4", "\t\treturn false",
              "\tlet pointLane = x < 0.0 ? (y >= 0.0 ? 0 : 3) : (y >= 0.0 ? 1 : 2)",
              "\tif pointLane != lane", "\t\treturn false",
              "\tlet cellX = tdGroundTerrainCell(x)", "\tlet cellY = tdGroundTerrainCell(y)",
              "\tif not tdGroundTerrainCellInMap(cellX, cellY)", "\t\treturn false",
              '\treturn SubString(tdGroundSafeLayerRow(cellY), cellX, cellX + 1) == "1"', ""]
    for name, indices in (("tdGroundSortSourceMin", (0, 1)), ("tdGroundSortSourceMax", (2, 3))):
        lines.append(f"public function {name}(int lane) returns vec2")
        for lane, bounds_for_lane in enumerate(bounds):
            x, y = (bounds_for_lane[i] for i in indices)
            lines += [f"\tif lane == {lane}", f"\t\treturn vec2({x}.0, {y}.0)"]
        lines += ["\treturn vec2(0.0, 0.0)", ""]
    return ("\n".join(lines)).encode()


def verify_generated_dispatch(generated, source, safe):
    """Independently interpret the emitted Wurst if/else trees for every row."""
    text = generated.decode()
    for name, mask in (("tdGroundSourceMaskRow", source), ("tdGroundSafeLayerRow", safe)):
        body = text.split(f"function {name}(int cellY) returns string\n", 1)[1].split("\n\n", 1)[0]
        lines = body.splitlines()
        def parse(index, depth):
            line = lines[index]
            assert line.startswith("\t" * depth) and not line.startswith("\t" * (depth + 1))
            statement = line[depth:]
            if statement.startswith("return "):
                return ("return", ast.literal_eval(statement[7:])), index + 1
            assert statement.startswith("if cellY < ")
            threshold = int(statement[len("if cellY < "):])
            yes, index = parse(index + 1, depth + 1)
            assert lines[index] == "\t" * depth + "else"
            no, index = parse(index + 1, depth + 1)
            return ("if", threshold, yes, no), index
        tree, consumed = parse(0, 1)
        assert consumed == len(lines), "Unparsed generated Wurst dispatch"
        for y, expected in enumerate(mask):
            node = tree
            while node[0] == "if":
                node = node[2] if y < node[1] else node[3]
            decoded = node[1]
            assert len(decoded) == GRID_SIZE
            assert decoded == "".join(str(value) if value >= 0 else "-" for value in expected), f"Wrong {name} row {y}"


def read_npy(data):
    """Read the review's simple numeric NPY arrays without requiring NumPy."""
    stream = io.BytesIO(data)
    assert stream.read(6) == b"\x93NUMPY"
    version = stream.read(2)
    assert version in (b"\x01\x00", b"\x02\x00")
    fmt = "<H" if version[0] == 1 else "<I"
    length = struct.unpack(fmt, stream.read(struct.calcsize(fmt)))[0]
    header = ast.literal_eval(stream.read(length).decode("latin1").strip())
    assert not header["fortran_order"]
    payload = stream.read()
    shape, dtype = header["shape"], header["descr"]
    size = math.prod(shape)
    if dtype in ("|b1", "|u1"):
        assert len(payload) == size
        values = tuple(payload)
    elif dtype == "<i8":
        assert len(payload) == size * 8
        values = tuple(value for (value,) in struct.iter_unpack("<q", payload))
    else:
        raise ValueError(f"Unsupported review NPY dtype {dtype}")
    return shape, values


def verify_reference(path, source, vertices, pathing):
    with zipfile.ZipFile(path) as archive:
        shape, masks = read_npy(archive.read("masks.npy"))
        assert shape == (4, GRID_SIZE, GRID_SIZE)
        assert read_npy(archive.read("walk.npy")) == ((GRID_SIZE, GRID_SIZE), tuple(pathing))
        assert read_npy(archive.read("layer.npy")) == ((65, 65), tuple(layer for layer, _ in vertices))
    differences = 0
    for lane in range(4):
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                reference = bool(masks[(lane * GRID_SIZE + y) * GRID_SIZE + x])
                generated = source[y][x] == lane
                if reference != generated:
                    assert reference and not generated, "Generated source extends beyond review"
                    assert protected(ORIGIN + x * CELL_SIZE, ORIGIN + y * CELL_SIZE), "Non-central review mismatch"
                    differences += 1
    assert differences == 1392, "Unexpected central review difference"
    return differences


def generate(reference_npz=None):
    map_bytes = (ROOT / MAP_PATH).read_bytes()
    assert sha(map_bytes) == REVIEWED_HASHES["map"], "Source map changed; recalibrate/review before regeneration"
    archive = Mpq(map_bytes)
    inputs = {name: archive.extract(name) for name in REVIEWED_HASHES if name != "map"}
    for name, data in inputs.items():
        assert sha(data) == REVIEWED_HASHES[name], f"Unreviewed map member: {name}"
    source, safe, seeds, bounds, vertices, pathing = derive(inputs["war3map.w3e"], inputs["war3map.wpm"], inputs["war3map.w3r"])
    # All 20 piles, every one of their 15 reusable positions, keep existing coordinates.
    piles = []
    for lane in range(4):
        for group in range(1, 6):
            for index in range(15):
                x, y = pile_position(lane, group, index)
                assert safe_layer_at(safe, x, y) == 1 and lane_at(x, y) == lane
                assert source_lane(source, x, y) == -1, "Pile overlaps source mask"
                piles.append([lane, group, index, x, y])
    for lane, (sx, sy) in enumerate(seeds):
        assert source_lane(source, ORIGIN + sx * 32 + 16, ORIGIN + sy * 32 + 16) == lane
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            value = source[y][x]
            px, py = ORIGIN + x * 32, ORIGIN + y * 32
            assert not protected(px, py) or value == -1
            if value >= 0:
                left, bottom, right, top = bounds[value]
                assert left <= px < right and bottom <= py < top
                assert source_lane(source, px, py) == value
                assert source_lane(source, px + 31.999, py + 31.999) == value
    for x, y in ((-4096.001, 0), (4096, 0), (0, -4096.001), (0, 4096)):
        assert source_lane(source, x, y) == -1 and safe_layer_at(safe, x, y) == -1
    reference_difference = verify_reference(reference_npz, source, vertices, pathing) if reference_npz else None
    manifest = {
        "generator": "tools/GenerateGroundItemTerrainMask.py",
        "read_only_source": MAP_PATH, "reviewed_sha256": REVIEWED_HASHES,
        "origin": [ORIGIN, ORIGIN], "cell_size": CELL_SIZE, "grid_size": [GRID_SIZE, GRID_SIZE],
        "source_raw_layer": 0, "source_connectivity": "4-neighbor within lane from W3R spawn center",
        "central_protection_half_open": list(CENTRAL_PROTECTION),
        "source_cells_per_lane": list(EXPECTED_LANE_COUNTS), "source_bounds_per_lane": bounds,
        "spawn_seed_cells": seeds, "safe_item_raw_layers": [0, 1],
        "safe_item_max_quad_height_delta": MAX_SAFE_HEIGHT_DELTA,
        "destination_raw_layer": 1, "destination_checked_pile_positions": len(piles),
        "static_walkability": "WPM flags & 0x02 == 0", "dry_ground": "WPM flags & 0x40 != 0",
        "buildability_used": False, "source_edge_policy": "Reject mixed-layer quads; half-open cells",
    }
    # The optional reference check is validation-only and never changes output.
    generated_wurst = wurst(source, safe, bounds)
    verify_generated_dispatch(generated_wurst, source, safe)
    outputs = {WURST_PATH: generated_wurst,
               MANIFEST_PATH: (json.dumps(manifest, indent=2) + "\n").encode()}
    assert (ROOT / MAP_PATH).read_bytes() == map_bytes, "Source map changed during generation"
    return outputs, reference_difference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="Write only new mask/manifest source files")
    group.add_argument("--check", action="store_true", help="Read-only exact regeneration and safety validation")
    parser.add_argument("--reference-npz", type=Path, help="Optional read-only Astra mask comparison")
    args = parser.parse_args()
    outputs, difference = generate(args.reference_npz)
    for name, expected in outputs.items():
        path = ROOT / name
        if args.write:
            path.write_bytes(expected)
        else:
            assert path.read_bytes() == expected, f"Stale ground-item mask artifact: {name}"
    print(("Wrote" if args.write else "PASS:") + " source-only ground-item mask/manifest; source cells 1824/1552/1600/1664; 300 existing pile positions valid; map unchanged")
    if difference is not None:
        print(f"PASS: review NPY terrain/pathing equal; {difference} removed source cells all in central protection")
    print("NOT TESTED: Wurst compilation, native enumeration/relocation, dynamic blockers, timers or gameplay")


if __name__ == "__main__":
    main()
