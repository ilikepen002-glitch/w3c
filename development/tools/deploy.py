"""Deploy authored sources into this checked-out, editor-created Y3 project.

Uses a pinned official unit template and the Git submodule already in the map.
Does not recreate terrain/GMP files, initialize projects or modify the editor.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import uuid
import zlib

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=4) + '\n', encoding='utf-8')

header = read(PROJECT / 'header.project')
MAP = PROJECT / 'maps' / header['entry_map']['name']
assert MAP.is_dir() and (MAP / 'header.map').is_file(), 'Missing editor-created map'
SCRIPT = MAP / 'script'
SCRIPT.mkdir(exist_ok=True)
(SCRIPT / '.log').mkdir(exist_ok=True)
assert (SCRIPT / 'y3' / 'init.lua').is_file(), 'Initialize official library first: git submodule update --init'
shutil.copytree(ROOT / 'src', SCRIPT, dirs_exist_ok=True)

# The scene/UI roots and tuple serialization come from the editor-created map.
hud_path = MAP / 'ui' / 'SpiritHUD.json'
if not hud_path.exists():
    hud = read(MAP / 'ui' / 'SceneUI.json')
    assert hud['children'] == [] and hud['type'] == 2
    hud.update(name='SpiritHUD', uid=str(uuid.uuid4()), zorder=600)
    write(hud_path, hud)

camp = read(PROJECT / 'campinfo.json')
roles = {item['items'][0]: item['items'][1] for item in camp['roles']}
colors = ['#FF5555', '#55AAFF', '#55DD99', '#CC88FF']
for rid in range(2, 5):
    if rid not in roles:
        role = copy.deepcopy(roles[1]);role.update(id=rid, name='$player '+str(rid), color=colors[rid-1])
        camp['roles'].append({'__tuple__': True, 'items': [rid, role]})
for item in camp['camps']:
    if item['items'][0] == roles[1]['camp_id']:
        item['items'][1]['role_ids'] = [1, 2, 3, 4]
write(PROJECT / 'campinfo.json', camp)

template = read(ROOT / 'vendor' / 'y3-helper' / 'unit.json')
lang_path = MAP / 'zhlanguage.json'
lang = read(lang_path)
# Model keys are taken from the official TD and CasualTD templates, not guessed.
objects = [
    ('游侠', 200780), ('剑卫', 200806), ('禁卫', 200797), ('森语者', 200799), ('幽魂', 200809),
    ('黑潮斥候', 200776), ('疾行先锋', 200792), ('重甲卫士', 200798), ('黑潮首领', 206850),
    ('行军道路', 201702), ('建造基座', 208145), ('契灵之门', 103895),
]
for index, (name, model) in enumerate(objects, 1):
    key = 134299000 + index
    data = copy.deepcopy(template)
    name_id = zlib.crc32(('spirit:' + name).encode('utf-8'))
    if name_id >= 2**31: name_id -= 2**32
    lang[str(name_id)] = name
    data.update(key=key, _ref_=key, uid=str(key), model=model, name=name_id,
                hp_max=1000.0, hp_rec=0.0, hp_rec_grow=0, hp_rec_percent=0,
                attack_phy=0.0, attack_mag=0.0, common_atk_type=0,
                agility=0.0, strength=0.0, intelligence=0.0,
                bar_show_name=0 if index>=10 else 2, blood_show_type=0 if index>=10 else 2)
    for field in list(data):
        if field.endswith('_grow'): data[field]=0
    for field in ['common_atk', 'common_ability_list', 'hero_ability_list']:
        data[field] = {'__tuple__': True, 'items': []}
    write(MAP / 'editor_table' / 'editorunit' / f'{key}.json', data)
write(lang_path, lang)

# Native imported icon packages and their IDs are committed alongside the map.
# Copying loose PNGs does not perform an editor import and is intentionally omitted.

manifest = {str(p.relative_to(ROOT / 'src')).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / 'src').rglob('*.lua'))}
write(PROJECT / 'spirit-build.json', {'source_root': str(ROOT), 'lua_library_commit':
      '000437857cd501d4a318a7355cf43af3b54cc3cc', 'source_hashes': manifest})
print(f'DEPLOYED {len(manifest)} authored Lua files, {len(objects)} unit definitions: {PROJECT}')
print('This is packaging evidence only; engine loading and gameplay must be checked separately.')
