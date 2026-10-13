# Provenance

Created 2026-10-13 for this project under the user's requested elemental combat effects and the approved three-resource B-batch scope.

All mesh vertices, UVs, closed primitives, winding, atlas pixels, animation keys and material choices are original program-authored project assets. No third-party model, source texture, commercial asset, sampled game texture, downloaded reference artwork or AI image-generation output is incorporated. The 64×64 atlas is generated deterministically by the included Python script with broad gradients, sparse bark grooves and mineral cracks.

The BLP1 encoding layout and MDX parser-loader workflow reuse the project's existing published asset tooling. The converter runtime uses the project's pinned public npm dependencies and their independent upstream software licenses; dependency code is not redistributed with these art assets. Runtime installation was `npm ci --ignore-scripts`, preserving locked versions and integrity hashes. First attempt using the old mirror lockfile failed before installation due to missing default cache; isolated lockfile origins were updated to official npm registry and a workspace-local cache was used successfully. No install scripts or unfamiliar executables were run.

These new artwork resources have no third-party artwork attribution or redistribution restriction introduced by this task; retain this provenance and the project's applicable licensing when publishing or modifying them. This statement does not relicense upstream converter software.

No production map was changed, compiled or tested by this asset task. The implementation owner receives the final resource SHA-256 values and owns actual map packaging and compatibility review. No in-game visual/performance test has been claimed.
