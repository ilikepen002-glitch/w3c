"""Build only the four boss PNG portraits into opaque 64px BTN/DISBTN BLP1.

Run from any directory with Pillow 12.3.0. Import the existing palette/alpha8
encoder without invoking BuildEvolutionAssets.main() or touching other assets.
Use --verify-only to independently check paths, hashes, mip chains and alpha.
This script does not build maps, produce 3D models, or launch Warcraft III.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps, __version__ as PILLOW_VERSION
from BuildEvolutionAssets import blp

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/source/bosses/manifest.json"
ENCODER = ROOT / "tools/BuildEvolutionAssets.py"
NAMES = ("TDBossRiftwind", "TDBossObsidian", "TDBossEclipse", "TDBossAbyss")
FILE_KEYS = ("source_png", "normal_blp", "disabled_blp")
SIZE = 64


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_path(relative: str) -> Path:
    """Require portable repository-relative paths, with no traversal/symlinks."""
    portable = PurePosixPath(relative)
    if portable.is_absolute() or ".." in portable.parts or "\\" in relative:
        raise ValueError(f"Not a portable repository-relative path: {relative}")
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"Manifest path is outside the repository: {relative}")
    return path


def validate_inputs(manifest: dict) -> None:
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported boss asset manifest schema")
    if manifest["required_pillow_version"] != PILLOW_VERSION:
        raise ValueError(f"Use Pillow {manifest['required_pillow_version']}; found {PILLOW_VERSION}")
    if tuple(asset["name"] for asset in manifest["assets"]) != NAMES:
        raise ValueError("Expected exactly the four ordered, isolated boss icon names")
    if manifest["preview"] != "assets/source/bosses/contact-sheet.png":
        raise ValueError("Unexpected contact-sheet destination")
    if manifest["provenance_file"] != "assets/source/bosses/prompts.json":
        raise ValueError("Unexpected source provenance path")
    provenance_path = local_path(manifest["provenance_file"])
    if sha256(provenance_path) != manifest["provenance_sha256"]:
        raise ValueError("Original prompt provenance hash mismatch")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if len(provenance["images"]) != 4:
        raise ValueError("Expected exactly four original prompt records")
    for asset, record in zip(manifest["assets"], provenance["images"]):
        name = asset["name"]
        expected_source = "assets/source/bosses/" + record["file"]
        normal = f"war3mapImported\\BTN{name}.blp"
        disabled = f"ReplaceableTextures\\CommandButtonsDisabled\\DISBTN{name}.blp"
        if asset["source_png"] != expected_source or asset["prompt"] != record["prompt"]:
            raise ValueError(f"Original source path or exact prompt mismatch: {name}")
        if asset["warcraft_normal_path"] != normal or asset["warcraft_disabled_path"] != disabled:
            raise ValueError(f"Unexpected Warcraft icon paths: {name}")
        if asset["normal_blp"] != "imports/" + normal.replace("\\", "/"):
            raise ValueError(f"Normal import path mismatch: {name}")
        if asset["disabled_blp"] != "imports/" + disabled.replace("\\", "/"):
            raise ValueError(f"Disabled import path mismatch: {name}")
        source = local_path(asset["source_png"])
        if sha256(source) != asset["sha256"]["source_png"]:
            raise ValueError(f"Original source hash mismatch: {name}")
        with Image.open(source) as image:
            if list(image.size) != asset["source_size"] or image.mode != asset["source_mode"]:
                raise ValueError(f"Original image size/mode mismatch: {name}")
            left, top, right, bottom = asset["crop"]
            if any(type(v) is not int for v in asset["crop"]):
                raise ValueError(f"Crop coordinates must be source-pixel integers: {name}")
            if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
                raise ValueError(f"Crop is outside source image: {name}")
            if right - left != bottom - top:
                raise ValueError(f"Portrait crop must be square: {name}")
        # Warcraft paths are case-insensitive. Refuse collisions with any other
        # imported resource instead of silently overwriting a differently named file.
        for key in ("normal_blp", "disabled_blp"):
            target = local_path(asset[key])
            if target.parent.exists():
                for existing in target.parent.iterdir():
                    if existing.name.casefold() == target.name.casefold() and existing != target:
                        raise ValueError(f"Case-insensitive import collision: {existing}")


def decode_blp(path: Path) -> Image.Image:
    """Parse palette BLP1 independently and validate every mip's alpha plane."""
    data = path.read_bytes()
    if len(data) < 1180 or data[:4] != b"BLP1":
        raise ValueError(f"Not a palette BLP1: {path}")
    encoding = struct.unpack_from("<6I", data, 4)
    if encoding != (1, 8, SIZE, SIZE, 5, 1):
        raise ValueError(f"Unexpected BLP1 encoding or size: {path}")
    offsets = struct.unpack_from("<16I", data, 28)
    lengths = struct.unpack_from("<16I", data, 92)
    cursor = 1180
    for level in range(16):
        if level >= 7:
            if offsets[level] or lengths[level]:
                raise ValueError(f"Extra BLP mip at {level}: {path}")
            continue
        pixels = max(1, SIZE >> level) ** 2
        if offsets[level] != cursor or lengths[level] != 2 * pixels:
            raise ValueError(f"Invalid BLP mip offset/length at {level}: {path}")
        alpha = data[cursor + pixels:cursor + 2 * pixels]
        if len(alpha) != pixels or any(value != 255 for value in alpha):
            raise ValueError(f"Expected opaque alpha8 at every mip: {path}")
        cursor += lengths[level]
    if cursor != len(data):
        raise ValueError(f"Unexpected missing/trailing BLP bytes: {path}")
    palette = data[156:1180]
    indices = data[offsets[0]:offsets[0] + SIZE * SIZE]
    pixels = bytes(channel for index in indices for channel in
                   (palette[index * 4 + 2], palette[index * 4 + 1], palette[index * 4], 255))
    return Image.frombytes("RGBA", (SIZE, SIZE), pixels)


def verify_manifest(manifest: dict, require_hashes: bool) -> None:
    validate_inputs(manifest)
    normal_seen, disabled_seen = set(), set()
    for asset in manifest["assets"]:
        normal = decode_blp(local_path(asset["normal_blp"]))
        disabled = decode_blp(local_path(asset["disabled_blp"]))
        for pixels, seen in ((normal.tobytes(), normal_seen), (disabled.tobytes(), disabled_seen)):
            digest = hashlib.sha256(pixels).hexdigest()
            if digest in seen:
                raise ValueError(f"Repeated icon pixels: {asset['name']}")
            seen.add(digest)
        gray_pixels = disabled.tobytes()
        if any(gray_pixels[i] != gray_pixels[i + 1] or gray_pixels[i + 1] != gray_pixels[i + 2]
               for i in range(0, len(gray_pixels), 4)):
            raise ValueError(f"Disabled icon must be grayscale: {asset['name']}")
        if sum(gray_pixels[::4]) >= 0.6 * sum(ImageOps.grayscale(normal).tobytes()):
            raise ValueError(f"Disabled icon must be substantially darker: {asset['name']}")
        if require_hashes:
            for key in FILE_KEYS:
                if asset["sha256"][key] != sha256(local_path(asset[key])):
                    raise ValueError(f"Recorded asset hash mismatch: {asset[key]}")
        print(f"PASS {asset['name']}: BTN/DISBTN, 64x64, opaque alpha8, 7 valid mips")
    if require_hashes:
        if manifest["tool_versions"]["blp_encoder_sha256"] != sha256(ENCODER):
            raise ValueError("BLP encoder hash differs from the recorded version")
        if manifest["tool_versions"]["boss_converter_sha256"] != sha256(Path(__file__)):
            raise ValueError("Boss converter hash differs from the recorded version")
        if manifest["preview_sha256"] != sha256(local_path(manifest["preview"])):
            raise ValueError("Recorded contact-sheet hash mismatch")


def contact_sheet(manifest: dict) -> None:
    cell_w, cell_h, top = 284, 238, 70
    sheet = Image.new("RGB", (4 * cell_w + 24, cell_h + top + 12), "#10151d")
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 10), "Four bosses | BLP1-decoded static texture preview",
              font=ImageFont.load_default(size=21), fill="#e4e9e9")
    draw.text((16, 40), "Offline only. Each pair: BTN / DISBTN. Top 2x; bottom actual 64px. No game screenshot or 3D portrait.",
              font=ImageFont.load_default(size=12), fill="#b1bbc4")
    for index, asset in enumerate(manifest["assets"]):
        x, y = 12 + index * cell_w, top
        draw.rounded_rectangle((x, y, x + cell_w - 10, y + cell_h - 10), radius=5,
                               fill="#1b232d", outline="#3b4654")
        draw.text((x + 9, y + 8), f"{index + 1:02d}  {asset['name'].removeprefix('TDBoss')}",
                  font=ImageFont.load_default(size=14), fill="#e9e0ca")
        normal = decode_blp(local_path(asset["normal_blp"])).convert("RGB")
        disabled = decode_blp(local_path(asset["disabled_blp"])).convert("RGB")
        sheet.paste(normal.resize((128, 128), Image.Resampling.NEAREST), (x + 8, y + 34))
        sheet.paste(disabled.resize((128, 128), Image.Resampling.NEAREST), (x + 140, y + 34))
        sheet.paste(normal, (x + 39, y + 165))
        sheet.paste(disabled, (x + 172, y + 165))
    sheet.save(local_path(manifest["preview"]), compress_level=9)


def build(manifest: dict) -> None:
    validate_inputs(manifest)
    for asset in manifest["assets"]:
        with Image.open(local_path(asset["source_png"])) as source:
            normal = source.convert("RGBA").crop(tuple(asset["crop"]))
            normal = normal.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        if normal.getchannel("A").getextrema() != (255, 255):
            raise ValueError(f"Unexpected portrait transparency: {asset['name']}")
        disabled = ImageOps.grayscale(normal).convert("RGBA")
        disabled = ImageEnhance.Brightness(disabled).enhance(0.45)
        blp(normal, local_path(asset["normal_blp"]))
        blp(disabled, local_path(asset["disabled_blp"]))
        asset["sha256"] = {key: sha256(local_path(asset[key])) for key in FILE_KEYS}
    manifest["tool_versions"] = {
        "pillow": PILLOW_VERSION,
        "blp_encoder": "tools/BuildEvolutionAssets.py:blp (import only)",
        "blp_encoder_sha256": sha256(ENCODER),
        "boss_converter_sha256": sha256(Path(__file__)),
    }
    verify_manifest(manifest, require_hashes=False)
    contact_sheet(manifest)
    manifest["preview_sha256"] = sha256(local_path(manifest["preview"]))
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verify_manifest(manifest, require_hashes=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Check all assets without rebuilding")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if args.verify_only:
        verify_manifest(manifest, require_hashes=True)
    else:
        build(manifest)


if __name__ == "__main__":
    main()
