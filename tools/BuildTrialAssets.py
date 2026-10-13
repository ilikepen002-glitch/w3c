#!/usr/bin/env python3
"""Deterministic trial-only 64px BTN/DISBTN conversion. No map build.

Run from the repository root: python tools/BuildTrialAssets.py
Only BuildEvolutionAssets.blp is reused; its main is never invoked.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps
from BuildEvolutionAssets import blp

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/source/trial/manifest.json"
NORMAL = "war3mapImported/BTNTDTrialGoldGolem.blp"
DISABLED = "ReplaceableTextures/CommandButtonsDisabled/DISBTNTDTrialGoldGolem.blp"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_source(manifest: dict, root: Path = ROOT) -> Image.Image:
    source = root / manifest["source"]
    if digest(source.read_bytes()) != manifest["sha256"]:
        raise ValueError("Trial source hash mismatch; approve and update the manifest first")
    with Image.open(source) as image:
        return image.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)


def disabled_icon(normal: Image.Image) -> Image.Image:
    disabled = ImageOps.grayscale(normal).convert("RGBA")
    disabled.putalpha(normal.getchannel("A"))
    return ImageEnhance.Brightness(disabled).enhance(0.45)


def build(manifest_path: Path = MANIFEST, root: Path = ROOT) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    normal = render_source(manifest, root)
    disabled = disabled_icon(normal)
    # Preflight source before touching any output. Keep these two paths exclusive.
    blp(normal, root / "imports" / NORMAL)
    blp(disabled, root / "imports" / DISABLED)
    folder = root / "assets/source/trial"
    normal.save(folder / "gold-coin-golem-btn-64.png")
    disabled.save(folder / "gold-coin-golem-disbtn-64.png")
    preview = Image.new("RGBA", (144, 80), (25, 25, 25, 255))
    preview.alpha_composite(normal, (4, 8))
    preview.alpha_composite(disabled, (76, 8))
    preview.save(folder / "gold-coin-golem-icons-preview.png")
    manifest["conversion"] = {
        "script": "tools/BuildTrialAssets.py",
        "encoder": "BuildEvolutionAssets.blp",
        "size": [64, 64], "format": "BLP1 palette alpha8",
        "mips": [64, 32, 16, 8, 4, 2, 1],
        "disabled": "grayscale then brightness 0.45; preserve alpha",
        "normal": NORMAL.replace("/", "\\"),
        "disabled_path": DISABLED.replace("/", "\\"),
        "normal_sha256": digest((root / "imports" / NORMAL).read_bytes()),
        "disabled_sha256": digest((root / "imports" / DISABLED).read_bytes()),
    }
    manifest["use"] = ("Concept art and 64px BTN/DISBTN, not a 3D model. "
                       "Runtime uses native Units.golemStatue1 / UnitIds.battlegolem "
                       "as a gold-colored approximation, pending target 1.28 asset verification.")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest["conversion"]


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
