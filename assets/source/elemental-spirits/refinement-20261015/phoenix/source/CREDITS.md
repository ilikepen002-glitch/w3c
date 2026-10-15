# Phoenix (Re-Classic) source asset

Author: johnwar
Source: https://www.hiveworkshop.com/threads/phoenix-re-classic.353829/
Resource metadata: https://www.hiveworkshop.com/resources/phoenix-re-classic.129747/more-info
Retrieved: 2026-10-14 through the public HIVE Download link in cloud browser, without login.

Author statement on source page: “Anyone can edit my models as long as you give proper credits.”
Retain proper johnwar credit in any derived map/model. This statement is not represented as a general commercial license or a license for Blizzard assets. Original package readme is preserved as original-readme.html.

Original ZIP and PhoenixV2.mdx are unmodified. inspection.json is a static binary analysis, not an in-game test. Verified MDLX magic, VERS=800, SEQS and TEXS. Game rendering/behavior on Warcraft III 1.27a remains untested.

Visual reference: https://www.hiveworkshop.com/data/ratory-images/281/281368-2da51892f0e6aa6169f25083dbe323a2.png
The inspected author image shows orange-yellow wings with pink-purple edges, a slim bird body and one narrow tail stem ending in a feather fan. It does not match the requested white/red/purple multi-ribbon long-tail concept without further art work.

## Static rendering-cost inspection
35 BONE records, 23 HELP nodes (58 combined); 9 geosets; 8 PRE2 particle emitters; 4 RIBB ribbon emitters; 8 materials / 9 layers. Layer filter modes: 3 opaque (0), 1 alpha-test/transparent (1), 1 blend (2), 3 additive (3), 1 add-alpha (4). Thus 5 blended/additive layers plus 1 alpha-test layer. Counts do not equal concurrently visible effects or draw calls.

Low geometry cost does not imply negligible total cost: evaluate overdraw from enlarged additive wings, 8 particle emitters and 4 ribbons in the actual map camera. Some nodes/effects belong to egg/birth/death sequences. A tower-only derivative could eventually remove unused states after visual verification, while preserving the unmodified original.

Web beta viewer failed with navigator.gpu.requestAdapter returned null; old viewer showed an empty canvas. The saved screenshot is an author-published model preview, not an in-game test or a successfully running live 3D viewer. No 1.27a runtime test was performed.
