# Retired collection count badges

`count-ui-imports.tar.xz` losslessly preserves the 480 former `TDPetSpeciesNNQxNy` BTN/DIS BLP files, with their historical import paths. `count-ui-manifest.json` retains the original per-file SHA-256 and portrait provenance for all 240 pairs.

These files are source history only and are intentionally outside `imports/`. Current collection buttons use the existing quality-only portraits. The 15 portrait PNGs and all original frame/count SVG templates under `assets/source/pet-ui/` remain unchanged. `BuildElementalPetUiAssets.py` now generates only 15 plain + 60 quality pairs and rejects obsolete count icons in `imports/`.

Use `python3 tools/VerifyPetCollectionArtifact.py` to check all archived hashes, exact live/retired path separation and the 610-object source contract. For historical inspection, extract the archive to a temporary directory, not into current `imports/`.
