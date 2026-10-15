# Approved Phoenix texture source

These two custom textures were painted with the built-in image_gen tool. They are new artwork, not recovered copies of Blizzard Phoenix2.blp or PhoenixPortrait.blp. The original native texture download attempt was unavailable and was not bypassed.

## Locked input and rebuild

- Body: art/phoenix-body-imagegen-v4.png, RGBA 1254×1254, approved final source after four image_gen iterations.
- Head: art/phoenix-head-imagegen-v1.png, RGB 1254×1254.
- All body intermediate source images and exact saved prompts are retained in art/ and prompts/. The v4 edit adds the upper-right red-to-pearl ramp used by the refined model's localized UV remapping. Head v1 paints the separate eye/beak/mouth regions.
- art/PhoenixBody.png and art/PhoenixHead.png are the exact approved 512×512 RGBA and 256×256 RGB downsampled inputs. Downsampling from the full source images is pixel-identical.

Run `python3 scripts/rebuild_textures.py` from any directory. Dependencies: Python, Pillow 12.3.0 and numpy. Only rebuilt/ and technical/ are written. It downsamples via Lanczos, performs 256-color median-cut palette quantization, and writes BLP1 with full mip chains. Body retains an independent 8-bit alpha plane at every mip; head is opaque. It asserts both final approved SHA256 hashes. This is format conversion, with no procedural raster repainting.

Image generation itself is not deterministic. The accepted, versioned source PNGs are the deterministic rebuild inputs; rerunning the prompt is not required or claimed to reproduce them.

Outputs are byte-identical to ../source/{PhoenixBody,PhoenixHead}.blp. See technical/texture-rebuild-audit.json, which also checks all mip offsets/sizes, exact alpha and palette quantization error. BLP filenames/import paths are unchanged by this source packaging.

## Model credit and limits

Original model: johnwar, Phoenix (Re-Classic), https://www.hiveworkshop.com/threads/phoenix-re-classic.353829/ . Author permits model editing with proper credit. Preserve johnwar credit. Native Warcraft texture dependencies are not redistributed here. The new textures do not grant ownership of the original model or native game artwork.

This pack supports the already-approved low-poly prototype. No further art iteration was made while packaging. All previews and checks are offline; Warcraft III 1.27a native effects and actual loading remain to be tested in-game.
