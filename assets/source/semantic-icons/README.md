# Semantic icon P1 source record

These seven selected PNG sources were generated using the built-in imagegen tool
on 2026-10-11 for this project, without third-party reference images. No Creative
Commons license, third-party license, exclusivity, or legal ownership claim is made.
The exact generation prompts are in `prompts.json`; the capture-forge edit is also
retained verbatim in `forge-edit-prompt.txt`.

The ranged, arcane, combat, and miscellaneous sheets preserve equipment-family
silhouettes. The quality plaques and their one-to-four notches came from imagegen;
the converter does not draw or add them. The fifth selected sheet is the revised
actions sheet, whose bottom-center cell depicts five ordinary capture balls feeding
one crowned master ball. The original crystal-fusion actions sheet and the rejected
standalone heart sketch are not part of this repository or map. Its superseded
`sheet_actions` prompt remains in the ledger to document how `forge_edit` produced
the selected `actions-sheet-v2-source.png`.

`manifest.json` records the exact source SHA256, per-icon pixel crop, rawcode
targets, output paths and BLP hashes. There are 30 active pairs: 26 equipment items,
three actions, and critical strike. The master-capture and five-to-one action
pairs are retired; their four dedicated BLP imports are absent. The shared
actions source and original prompts remain as provenance because its ordinary
capture and equipment crops are still active. The two semantically accurate native equipment
icons, glove and dagger, remain native. All eleven existing tower pairs were moved
to the `TDTower` namespace without changing bytes. All thirteen existing pet UI
pairs remain byte-identical. No 516-slot quality-variant expansion is included.

Rebuild only these new icons:

    python3 tools/BuildSemanticIcons.py

Read-only reproducibility check:

    python3 tools/BuildSemanticIcons.py --check

Conversion uses Pillow 12.3.0: explicit crop, 64×64 LANCZOS resample, alpha retained,
and grayscale brightness 0.45 for disabled art. The existing BLP1 writer produces
one 256-color MEDIANCUT palette, alpha8, and all seven mip levels through 1×1.
Only BLP files are imported. Source PNGs, prompts, and this manifest are not packed.

The semantic artifact verifier reads the actual built MPQ, decodes every icon/mip,
checks exact bindings and baseline object deltas, rejects old case-insensitive
paths, and emits a labeled packed-icon contact sheet. That contact sheet is an
offline inspection, not evidence of an in-game display or gameplay test.

Ordinary-only capture releases use VerifyCaptureRemovalArtifact.py against
their exact formal predecessor. Its closed removal delta remains separate
from the legacy icon-only VerifySemanticIconArtifact.py delta, which still
rejects object-set changes and arbitrary non-icon fields.
