# Evolution asset conversion

The PNGs and original imagegen prompts are retained in `assets/source/imagegen-manifest.json`.
The conversion does not redraw the images: Pillow resizes/quantizes them to BLP1 with an 8-bit alpha plane and full mip chain; `BuildEvolutionAssets.py` generates a two-geoset, two-bone MDL attachment for each tower family.

Rebuild from the repository root:

```powershell
python tools/BuildEvolutionAssets.py
Push-Location tools/asset-converter
npm ci --ignore-scripts --no-audit --no-fund
Pop-Location
node tools/asset-converter/convert.cjs
```

The pinned `mdx-m3-viewer` 5.7.9 package provides an independent MDL/MDX parser and BLP1 decoder ([upstream MIT-licensed source](https://github.com/flowtsohg/mdx-m3-viewer)). A TypeScript transpile hook loads its parser without building the browser viewer. `node_modules` is ignored; the exact dependency lockfile is retained.

The converter round-trips every MDX, checks version 800, Blend/TwoSided, Stand animation, and exact single-separator texture path; it decodes all texture mips and verifies wing alpha 0–255. Pillow's current BLP1 decoder reads palette alpha rather than the per-pixel plane, so its RGBA result is not used to validate Warcraft transparency.

The five attachment dimensions encode family-specific offsets at `origin`. Native placement, visibility/occlusion and animation in Warcraft III remain untested in this request.
