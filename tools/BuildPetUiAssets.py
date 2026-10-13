"""Render the 78 pet-menu SVGs, then encode opaque BTN/DISBTN BLP1.

Requires Inkscape 1.4 and Pillow 12.3.0 for the recorded deterministic output.
Reuse the project's existing BLP1 palette/alpha8/mipmap encoder without invoking
its main(), rebuilding evolution art, editing a map, or running Wurst.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps, __version__ as PILLOW_VERSION
from BuildEvolutionAssets import blp

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/source/pet-ui/manifest.json"
FILE_KEYS = ("source_svg", "normal_blp", "disabled_blp")
SIZE = 64
BASE_NAMES = {"TDPetMenuTools", "TDPetCollection", "TDPetPrevious", "TDPetNext", "TDPetReturnBuilder", "TDPetDeploy", "TDPetRecall", "TDPetCultivate", "TDPetInfo", "TDPetEmptySlot", "TDPetFlamePhoenix", "TDPetStormFaerieDragon", "TDPetGhostWisp"}
EXPECTED_NAMES = BASE_NAMES | {stem + "Q" + str(q) for stem in ("TDPetFlamePhoenix", "TDPetStormFaerieDragon", "TDPetGhostWisp") for q in range(1, 5)} | {"TDPetRelease", "TDPetKeep", "TDPetAdopt"}
EXPECTED_NAMES |= {stem + f"Q{q}N{n}" for stem in ("TDPetFlamePhoenix", "TDPetStormFaerieDragon", "TDPetGhostWisp") for q in range(1, 5) for n in range(1, 5)} | {"TDPetKeepOld", "TDPetUseNew"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"Manifest path is outside the repository: {relative}")
    return path


def check_svg(path: Path) -> None:
    root = ET.parse(path).getroot()
    if root.attrib.get("viewBox") != "0 0 64 64":
        raise ValueError(f"Expected a 64px SVG viewBox: {path}")
    for node in root.iter():
        if node.tag.split("}")[-1] in ("image", "text", "script", "foreignObject"):
            raise ValueError(f"SVG must contain native vectors without font/raster dependencies: {path}")
        for key, value in node.attrib.items():
            if key.split("}")[-1] == "href" and not value.startswith("#"):
                raise ValueError(f"SVG must be self-contained: {path}")


def decode_blp(path: Path) -> Image.Image:
    """Check each BLP1 alpha8 mip and decode the top level independently.

    Palette BGRA and alpha planes are inspected explicitly; Pillow's BLP1
    reader does not reliably validate alpha in this project's format.
    """
    data = path.read_bytes()
    if len(data) < 1180 or data[:4] != b"BLP1":
        raise ValueError(f"Not a palette BLP1: {path}")
    compression, flags, width, height, picture_type, subtype = struct.unpack_from("<6I", data, 4)
    if (compression, flags, width, height, picture_type, subtype) != (1, 8, SIZE, SIZE, 5, 1):
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
            raise ValueError(f"Invalid BLP mip size/offset at {level}: {path}")
        alpha = data[cursor + pixels:cursor + 2 * pixels]
        if len(alpha) != pixels or any(v != 255 for v in alpha):
            raise ValueError(f"Button must be fully opaque at every mip: {path}")
        cursor += lengths[level]
    if cursor != len(data):
        raise ValueError(f"Unexpected trailing or missing BLP bytes: {path}")
    palette = data[156:1180]
    indices = data[offsets[0]:offsets[0] + SIZE * SIZE]
    pixels = bytes(channel for i in indices for channel in
                   (palette[i * 4 + 2], palette[i * 4 + 1], palette[i * 4], 255))
    return Image.frombytes("RGBA", (SIZE, SIZE), pixels)


def label_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Pillow's bundled font keeps the preview independent of host font installs.
    # The actual icons contain no text or fonts.
    return ImageFont.load_default(size=size)


def contact_sheet(manifest: dict) -> None:
    cols, cell_w, cell_h, top = 4, 284, 238, 66
    rows = (len(manifest["assets"]) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w + 24, rows * cell_h + top + 12), "#10151d")
    draw = ImageDraw.Draw(sheet)
    title, font, small = label_font(21), label_font(14), label_font(12)
    draw.text((16, 10), "Pet UI | BLP1-decoded texture preview", font=title, fill="#e4e9e9")
    draw.text((16, 38), "Offline only. Each pair: BTN / DISBTN. Top 2x, bottom actual 64px. Not a game screenshot.",
              font=small, fill="#b1bbc4")
    for i, asset in enumerate(manifest["assets"]):
        x, y = 12 + (i % cols) * cell_w, top + (i // cols) * cell_h
        draw.rounded_rectangle((x, y, x + cell_w - 10, y + cell_h - 10), radius=5,
                               fill="#1b232d", outline="#3b4654")
        label = asset["name"].removeprefix("TDPet")
        draw.text((x + 9, y + 8), f"{i + 1:02d}  {label}", font=font, fill="#e9e0ca")
        normal = decode_blp(local_path(asset["normal_blp"])).convert("RGB")
        disabled = decode_blp(local_path(asset["disabled_blp"])).convert("RGB")
        sheet.paste(normal.resize((128, 128), Image.Resampling.NEAREST), (x + 8, y + 34))
        sheet.paste(disabled.resize((128, 128), Image.Resampling.NEAREST), (x + 140, y + 34))
        sheet.paste(normal, (x + 39, y + 165))
        sheet.paste(disabled, (x + 172, y + 165))
    sheet.save(local_path(manifest["preview"]), compress_level=9)


def verify_manifest(manifest: dict, require_hashes: bool) -> None:
    if len(manifest["assets"]) != 78 or {asset["name"] for asset in manifest["assets"]} != EXPECTED_NAMES:
        raise ValueError("Expected exact 78 icon names: 28 preserved + 48 owned-count portraits + 2 readable choice buttons")
    names, normal_pixels_seen, disabled_pixels_seen = set(), set(), set()
    for asset in manifest["assets"]:
        name = asset["name"]
        if name in names:
            raise ValueError(f"Duplicate asset name: {name}")
        names.add(name)
        check_svg(local_path(asset["source_svg"]))
        expected_normal = f"war3mapImported\\BTN{name}.blp"
        expected_disabled = f"ReplaceableTextures\\CommandButtonsDisabled\\DISBTN{name}.blp"
        if asset["warcraft_normal_path"] != expected_normal or asset["warcraft_disabled_path"] != expected_disabled:
            raise ValueError(f"Unexpected Warcraft icon path: {name}")
        if asset["normal_blp"] != "imports/" + expected_normal.replace("\\", "/"):
            raise ValueError(f"Normal import path mismatch: {name}")
        if asset["disabled_blp"] != "imports/" + expected_disabled.replace("\\", "/"):
            raise ValueError(f"Disabled import path mismatch: {name}")
        normal = decode_blp(local_path(asset["normal_blp"]))
        disabled = decode_blp(local_path(asset["disabled_blp"]))
        digest = hashlib.sha256(normal.tobytes()).hexdigest()
        if digest in normal_pixels_seen:
            raise ValueError(f"Repeated normal icon pixels: {name}")
        normal_pixels_seen.add(digest)
        disabled_digest = hashlib.sha256(disabled.tobytes()).hexdigest()
        if disabled_digest in disabled_pixels_seen:
            raise ValueError(f"Repeated disabled icon pixels: {name}")
        disabled_pixels_seen.add(disabled_digest)
        gray_pixels = disabled.tobytes()
        if any(gray_pixels[i] != gray_pixels[i + 1] or gray_pixels[i + 1] != gray_pixels[i + 2]
               for i in range(0, len(gray_pixels), 4)):
            raise ValueError(f"Disabled image must be grayscale: {name}")
        if sum(gray_pixels[::4]) >= 0.6 * sum(ImageOps.grayscale(normal).tobytes()):
            raise ValueError(f"Disabled image must be darker: {name}")
        if require_hashes:
            for key in FILE_KEYS:
                if asset["sha256"][key] != sha256(local_path(asset[key])):
                    raise ValueError(f"Recorded hash mismatch: {asset[key]}")
        print(f"PASS {name}: normal + disabled, 64x64, opaque alpha8, 7 valid mips")
    if require_hashes and manifest["preview_sha256"] != sha256(local_path(manifest["preview"])):
        raise ValueError("Recorded contact-sheet hash mismatch")


def build(manifest: dict, executable: str, only_new: bool = False) -> None:
    version = subprocess.run([executable, "--version"], check=True, capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="td-pet-ui-") as temporary:
        temp = Path(temporary)
        env = os.environ.copy()
        env["INKSCAPE_PROFILE_DIR"] = str(temp / "profile")
        env["XDG_CACHE_HOME"] = str(temp / "cache")
        for asset in manifest["assets"]:
            if only_new and all(local_path(asset[key]).is_file() and asset.get("sha256", {}).get(key) == sha256(local_path(asset[key])) for key in FILE_KEYS):
                continue
            source = local_path(asset["source_svg"])
            check_svg(source)
            rendered = temp / f"{asset['name']}.png"
            subprocess.run([executable, str(source), "--export-type=png",
                            f"--export-filename={rendered}", "--export-width=256", "--export-height=256"],
                           check=True, capture_output=True, env=env)
            with Image.open(rendered) as rendered_image:
                normal = rendered_image.convert("RGBA").resize((SIZE, SIZE), Image.Resampling.LANCZOS)
            if normal.getchannel("A").getextrema() != (255, 255):
                raise ValueError(f"SVG rendered with unexpected transparency: {source}")
            blp(normal, local_path(asset["normal_blp"]))
            disabled = ImageOps.grayscale(normal).convert("RGBA")
            disabled.putalpha(normal.getchannel("A"))
            disabled = ImageEnhance.Brightness(disabled).enhance(0.45)
            blp(disabled, local_path(asset["disabled_blp"]))
            asset["sha256"] = {key: sha256(local_path(asset[key])) for key in FILE_KEYS}
    manifest["tool_versions"] = {"inkscape": version, "pillow": PILLOW_VERSION,
                                 "blp_encoder": "tools/BuildEvolutionAssets.py:blp (import only)"}
    manifest["rendering"] = {"svg_export_size": [256, 256], "button_size": [SIZE, SIZE],
                             "resampler": "Pillow LANCZOS", "disabled_brightness": 0.45,
                             "blp": "BLP1 paletted, alpha8, 7 mip levels"}
    verify_manifest(manifest, require_hashes=False)
    contact_sheet(manifest)
    manifest["preview_sha256"] = sha256(local_path(manifest["preview"]))
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verify_manifest(manifest, require_hashes=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inkscape", default=shutil.which("inkscape"), help="Path to the Inkscape CLI")
    parser.add_argument("--only-new", action="store_true", help="Keep unchanged verified SVG/BLP assets; build only new or changed inputs")
    parser.add_argument("--verify-only", action="store_true", help="Check all hashes/paths/BLP mips without rebuilding")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if args.verify_only:
        verify_manifest(manifest, require_hashes=True)
    elif not args.inkscape:
        parser.error("Inkscape CLI is required for SVG rendering; supply --inkscape PATH")
    else:
        build(manifest, args.inkscape, only_new=args.only_new)


if __name__ == "__main__":
    main()
