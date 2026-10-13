# Original elemental spirit assets

The 15 MDX800 models and their BLP1 atlases are original program-authored geometry,
UVs, rigs, animations and textures, authorized by the user for this repository.
See LICENSE-PROVENANCE.txt. No third-party model artwork is included here.

`import-manifest.json` fixes the species ID, exact model/texture import path and
SHA-256 of each approved final binary. Do not rename an atlas inside the MDX.
Each model includes Stand, Walk, Attack, Death and Portrait animation plus an
embedded Portrait camera. The assets have offline format/topology/pose checks;
Warcraft III 1.27a runtime acceptance is still required.

Minimal editable/reproducible sources are in `models/<model>/`: run its Python
build script (Python 3, numpy, Pillow), then export_validate.cjs. The exporter
requires mdx-m3-viewer 5.7.9, typescript 4.9.5 and gl-matrix 3.4.4. Install those
from npm in an ancestor or set MDX_PARSER_MODULES to their node_modules directory.
Generate into a scratch copy: exporters also emit validation/preview caches,
which are deliberately excluded from this repository.

`portraits/species-01.png` through `species-15.png` are transparent 256px renders
of these final MDX models' actual Portrait camera/pose and decoded BLP textures.
`tools/BuildElementalPetUiAssets.py` embeds those in the existing v5 semantic SVG
frame, then produces palette BLP1 BTN and DIS icons and `ui-manifest.json`.
There are 315 required combinations in each state: 15 plain species icons,
60 species/quality icons and 240 species/quality/owned-skill-count list icons.
All have seven mip levels; no concept artwork or render animation cache ships.
