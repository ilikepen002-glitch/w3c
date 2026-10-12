"""Trial-only source/import tests. No map or Wurst toolchain required."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from BuildTrialAssets import MANIFEST, NORMAL, DISABLED, build, disabled_icon, render_source
from VerifyPetUIArtifact import decode_icon_blp


class TrialAssetTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_source_prompt_and_hash_are_preserved(self):
        self.assertIn("GOLD COIN GOLEM", self.manifest["prompt"])
        self.assertIn("not a 3D model", self.manifest["prompt"])
        self.assertEqual(self.manifest["library_file_id"], "libfile_3f732c23e1b48191a2bbd457fe5ca8e2")
        render_source(self.manifest)

    def test_imports_have_full_alpha8_mips_and_pinned_hashes(self):
        for path, key in [(NORMAL, "normal_sha256"), (DISABLED, "disabled_sha256")]:
            data = (ROOT / "imports" / path).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), self.manifest["conversion"][key])
            decode_icon_blp(data, path)

    def test_disabled_transform_is_gray_045_and_preserves_alpha(self):
        normal = render_source(self.manifest)
        disabled = disabled_icon(normal)
        self.assertEqual(normal.size, (64, 64))
        self.assertEqual(normal.getchannel("A").tobytes(), disabled.getchannel("A").tobytes())
        for red, green, blue, _ in zip(*[iter(disabled.tobytes())] * 4):
            self.assertEqual(red, green)
            self.assertEqual(green, blue)
        for original, transformed in zip(normal.convert("L").tobytes(), disabled.convert("L").tobytes()):
            self.assertLessEqual(abs(transformed - original * 0.45), 1.0)

    def test_rebuild_is_deterministic_and_trial_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / self.manifest["source"]
            source.parent.mkdir(parents=True)
            source.write_bytes((ROOT / self.manifest["source"]).read_bytes())
            manifest = source.parent / "manifest.json"
            manifest.write_text(json.dumps(self.manifest))
            with patch("BuildEvolutionAssets.main", side_effect=AssertionError("must not invoke evolution main")):
                first = build(manifest, root)
                second = build(manifest, root)
            self.assertEqual(first, second)
            self.assertEqual({str(p.relative_to(root / "imports")) for p in (root / "imports").rglob("*") if p.is_file()}, {NORMAL, DISABLED})
            for path, key in [(NORMAL, "normal_sha256"), (DISABLED, "disabled_sha256")]:
                self.assertEqual(hashlib.sha256((root / "imports" / path).read_bytes()).hexdigest(), self.manifest["conversion"][key])

    def test_bad_source_hash_fails_before_output_write(self):
        self.manifest["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / "manifest.json"
            manifest.write_text(json.dumps(self.manifest))
            with patch("BuildTrialAssets.blp") as encoder:
                with self.assertRaisesRegex(ValueError, "source hash mismatch"):
                    build(manifest)
                encoder.assert_not_called()

    def test_import_paths_are_casefold_unique(self):
        paths = [str(p.relative_to(ROOT / "imports")).replace("/", "\\") for p in (ROOT / "imports").rglob("*") if p.is_file()]
        self.assertEqual(len(paths), len({p.casefold() for p in paths}))
        self.assertEqual(self.manifest["conversion"]["normal"], NORMAL.replace("/", "\\"))
        self.assertEqual(self.manifest["conversion"]["disabled_path"], DISABLED.replace("/", "\\"))


if __name__ == "__main__":
    unittest.main()
