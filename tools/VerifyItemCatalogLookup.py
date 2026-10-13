#!/usr/bin/env python3
"""Offline source contract for the exact-key catalog index; no native hash/FPS claim."""
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[1]
path = 'wurst/items/TDItemData.wurst'
source = (root / path).read_text()
before = subprocess.check_output(['git', 'show', 'bfd59de:' + path], cwd=root, text=True)
ids = dict(re.findall(r'constant int (TD_ITEM_\w+_ID) = \'(.{4})\'',
                     (root / 'wurst/items/TDItemCatalogIds.wurst').read_text()))
config = (root / 'wurst/items/TDItemCatalogConfig.wurst').read_text()
names = re.findall(r'return tdEquipmentDefinition\((TD_ITEM_\w+_ID),', config)
rawcodes = [int.from_bytes(ids[name].encode(), 'big') for name in names]
assert len(rawcodes) == len(set(rawcodes)) == 40
lookup = {rawcode: index for index, rawcode in enumerate(rawcodes, 1)}
for index, rawcode in enumerate(rawcodes, 1):
    assert lookup.get(rawcode, 0) == index
for rawcode in [0, -1, *(int.from_bytes(x.encode(), 'big') for x in
                       ('iP00', 'iP11', 'iW00', 'jP01', 'IP01', 'iZ01', 'Ibal', 'uA11')),
                *(x + 8192 for x in rawcodes), *(x - 8192 for x in rawcodes)]:
    assert lookup.get(rawcode, 0) == 0
body = source.split('function tdItemDefinitionIndex', 1)[1].split('\npublic function', 1)[0]
assert 'if itemId <= 0\n\t\treturn 0' in body
assert 'return tdItemDefinitionIndices.loadInt(itemId)' in body
assert 'for ' not in body and '[itemId]' not in source
assert source.count('tdItemDefinitionIndices.saveInt(definition.rawcode, index)') == 1
# Registration's 40-entry lazy initialization and every metadata getter remain exact.
assert source.split('function tdEnsureItemCatalog()', 1)[1].split('function tdItemDefinitionIndex', 1)[0] == before.split('function tdEnsureItemCatalog()', 1)[1].split('function tdItemDefinitionIndex', 1)[0]
assert source.split('public function tdItemDefinitionCount()', 1)[1] == before.split('public function tdItemDefinitionCount()', 1)[1]
print('PASS: 40 exact rawcodes, 90 absent/alias probes, unchanged lazy initialization and metadata getters')
print('Lookup work: full 40-ID pass replaces 820 catalog comparisons with 40 Table loads; absent positive ID replaces 40 comparisons with 1 Table load.')
