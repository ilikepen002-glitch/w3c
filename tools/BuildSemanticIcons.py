#!/usr/bin/env python3
"""Rebuild only the 32 approved semantic icon pairs from selected imagegen art.

No drawing or image generation occurs here: crop, LANCZOS resize, alpha retention,
grayscale/0.45 disabled transform, and the existing BLP1 encoder are deterministic.
Run from any directory. Existing tower/pet art and wings are never regenerated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from PIL import Image, ImageEnhance, ImageOps

from BuildEvolutionAssets import blp

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/source/semantic-icons/manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_icon(entry: dict, root: Path = ROOT) -> Image.Image:
    source = root / entry["source"]
    if sha256(source) != entry["source_sha256"]:
        raise ValueError(f"Selected source hash mismatch: {entry['source']}")
    with Image.open(source) as opened:
        image = opened.convert("RGBA")
    x0, y0, x1, y1 = entry["crop"]
    if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
        raise ValueError(f"Invalid source crop: {entry['name']}")
    return image.crop((x0, y0, x1, y1)).resize((64, 64), Image.Resampling.LANCZOS)


def disabled_icon(image: Image.Image) -> Image.Image:
    disabled = ImageOps.grayscale(image).convert("RGBA")
    disabled.putalpha(image.getchannel("A"))
    return ImageEnhance.Brightness(disabled).enhance(0.45)


def build(manifest_path: Path = MANIFEST, root: Path = ROOT, check: bool = False) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(manifest["assets"]) != 32:
        raise ValueError("Expected exactly 32 approved new icon pairs")
    prepared = []
    with tempfile.TemporaryDirectory(prefix="semantic-icon-build-") as folder:
        rebuilt = Path(folder) / "icon.blp"
        for entry in manifest["assets"]:
            image = render_icon(entry, root)
            for key, rendered in [("normal", image), ("disabled", disabled_icon(image))]:
                path = root / "imports" / entry[key].replace("\\", "/")
                if not path.resolve().is_relative_to((root / "imports").resolve()):
                    raise ValueError(f"Import output escapes repository: {entry['name']}")
                blp(rendered, rebuilt)
                data = rebuilt.read_bytes()
                actual = hashlib.sha256(data).hexdigest()
                if actual != entry[key + "_sha256"]:
                    raise ValueError(f"Manifest {key} hash mismatch: {entry['name']}: {actual}")
                if check and (not path.is_file() or data != path.read_bytes()):
                    raise ValueError(f"Non-reproducible {key} icon: {entry['name']}")
                prepared.append((path, data))
    # Preflight every crop/source/output before writing any production import.
    if not check:
        for path, data in prepared:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print(f"PASS: 32 semantic pairs {'reproduced byte-for-byte' if check else 'built'} (64px BLP1, alpha8, seven mips)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare deterministic output without replacing imports")
    args = parser.parse_args()
    build(check=args.check)


if __name__ == "__main__":
    main()
