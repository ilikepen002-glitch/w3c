#!/usr/bin/env python3
"""Read-only branding gate against the immediate formal predecessor.

python tools/VerifyMapBrandingArtifact.py map.w3x --baseline-map old.w3x
This validates offline pixels/packaged bytes, not engine rendering or gameplay.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import struct

from PIL import Image
import yaml

from BuildMapBrandingAssets import LOADING, MODEL_SHA256, TILES, loading_tiles, lobby_tga
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifyGlobalRankingsArtifact import members
from VerifySemanticIconArtifact import Reader

ROOT = Path(__file__).resolve().parents[1]
NAME = '契灵守卫战'
DESCRIPTION = '以塔为阵，与灵缔契！捕捉精灵、洗练绝技，让不同的契约与装备碰撞出意想不到的力量。打造属于你的王牌阵容，与契灵并肩，守到最后！'
MODEL = LOADING.replace('/', '\\') + '\\Load-Generic.mdx'
TEXTURES = {name: LOADING.replace('/', '\\') + f'\\Generic-Loading-{name}.blp'
            for name, _ in TILES}
PREVIEW = 'war3mapPreview.tga'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode_loading_blp(data, size):
    """Independent opaque BLP1 decoder, checking every complete mip boundary."""
    require(len(data) >= 1180 and data[:4] == b'BLP1', 'Invalid loading BLP1')
    width, height = size
    require(struct.unpack_from('<6I', data, 4) == (1, 0, width, height, 5, 1),
            'Loading dimensions/alpha/mip flags changed')
    offsets = struct.unpack_from('<16I', data, 28)
    sizes = struct.unpack_from('<16I', data, 92)
    palette = [(data[i + 2], data[i + 1], data[i]) for i in range(156, 1180, 4)]
    images, cursor = [], 1180
    for level in range(16):
        if level >= 10:
            require(offsets[level] == sizes[level] == 0, 'Unexpected loading mip')
            continue
        size = max(1, width >> level), max(1, height >> level)
        count = size[0] * size[1]
        require(offsets[level] == cursor and sizes[level] == count and cursor + count <= len(data),
                'Missing/overlapping/truncated loading mip')
        rgb = bytes(v for index in data[cursor:cursor + count] for v in palette[index])
        images.append(Image.frombytes('RGB', size, rgb)); cursor += count
    require(cursor == len(data), 'Trailing loading BLP bytes')
    return images


def decode_preview_tga(data):
    require(len(data) == 18 + 256 * 256 * 4, 'Unexpected preview TGA size')
    require(struct.unpack_from('<BBBHHBHHHHBB', data) ==
            (0, 0, 2, 0, 0, 0, 0, 0, 256, 256, 32, 0x28),
            'Expected uncompressed 256x256 32-bit top-left TGA')
    image = Image.frombytes('RGBA', (256, 256), data[18:], 'raw', 'BGRA')
    require(image.getchannel('A').getextrema() == (255, 255), 'Preview alpha is not opaque')
    return image


def model_textures(data):
    require(data[:4] == b'MDLX', 'Invalid MDX model')
    offset, textures, version = 4, None, None
    while offset < len(data):
        require(offset + 8 <= len(data), 'Truncated MDX chunk')
        tag, count = data[offset:offset + 4], struct.unpack_from('<I', data, offset + 4)[0]
        offset += 8
        require(offset + count <= len(data), 'Truncated MDX payload')
        payload = data[offset:offset + count]; offset += count
        if tag == b'VERS':
            require(version is None and count == 4, 'Duplicate/bad MDX version')
            version = struct.unpack('<I', payload)[0]
        if tag == b'TEXS':
            require(textures is None and count == 4 * 268, 'Duplicate/bad MDX texture block')
            textures = []
            for start in range(0, count, 268):
                require(struct.unpack_from('<I', payload, start)[0] == 0, 'Unexpected replaceable texture')
                path = payload[start + 4:start + 264].split(b'\0', 1)[0].decode('ascii')
                require('/' not in path and '\\\\' not in path, 'Noncanonical MDX texture path')
                textures.append(path)
    require(version == 800 and textures is not None and set(textures) == set(TEXTURES.values()),
            'Loading MDX800/exact four TEXS references changed')
    return textures


def parse_info(data):
    r, spans, fields = Reader(data), {}, {}
    require(r.integer() == 25, 'Only W3I25 supported')
    r.take(8)
    def string(key):
        start = r.offset; fields[key] = r.string(); spans[key] = start, r.offset
    for key in ('name', 'author', 'description', 'players'): string(key)
    r.take(56)
    start = r.offset; fields['flags'] = r.integer(); spans['flags'] = start, r.offset
    r.take(5)
    for key in ('model', 'loading_text', 'title', 'subtitle'): string(key)
    return fields, spans


def normalized_info(data):
    fields, spans = parse_info(data)
    edits = {key: b'BRANDING\0' for key in ('name', 'description', 'loading_text', 'title')}
    edits['flags'] = struct.pack('<I', fields['flags'] & ~0x0001)
    for key in sorted(edits, key=lambda k: spans[k][0], reverse=True):
        start, end = spans[key]; data = data[:start] + edits[key] + data[end:]
    return data


def import_records(data):
    r = Reader(data)
    require(r.integer() == 1, 'Unexpected import version')
    records = []
    for _ in range(r.integer()):
        start = r.offset; flag = r.take(1)[0]; path = r.string()
        require(flag in (10, 13), 'Expected full custom import path')
        records.append((flag, path, data[start:r.offset]))
    require(r.offset == len(data), 'Trailing import bytes')
    require(len({path.casefold() for _, path, _ in records}) == len(records), 'Import path alias')
    return records


def verify_source(root=ROOT):
    root = Path(root)
    config = yaml.safe_load((root / 'wurst.build').read_text(encoding='utf-8'))
    info = config['buildMapData']; scenario = info['scenarioData']; loading = scenario['loadingScreen']
    require(info['name'] == loading['title'] == NAME, 'Source map/loading name mismatch')
    require(info['author'] == '留白散人' and loading['subTitle'] == '作者：留白散人', 'Author changed')
    require(scenario['description'] == loading['text'] == DESCRIPTION, 'Approved description changed')
    require(loading['model'] == MODEL, 'Loading model configuration changed')
    flags = info['optionsFlags']
    require('hideMinimapPreview' not in flags or flags['hideMinimapPreview'] is False,
            'Lobby preview configuration must be omitted or strictly false')
    source = root / 'assets/source/branding'
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    require(manifest['map_name'] == NAME and manifest['approved_loading_text'] == DESCRIPTION,
            'Approved manifest metadata changed')
    for entry in manifest['images']:
        require(sha((root / entry['path']).read_bytes()) == entry['sha256'], 'Source image hash mismatch')
    model = (root / 'imports' / Path(MODEL.replace('\\', '/'))).read_bytes()
    require(sha(model) == MODEL_SHA256, 'Loading MDX must remain byte-for-byte unchanged')
    model_textures(model)
    expected = loading_tiles(Image.open(source / '契灵守卫战-加载背景.png'))
    palettes, decoded = set(), {}
    for name, (_, _, right, bottom) in TILES:
        path = TEXTURES[name]; data = (root / 'imports' / Path(path.replace('\\', '/'))).read_bytes()
        require(data == expected[name], 'Converted loading bytes differ from approved source: ' + name)
        size = (512, 512 if name.startswith('Top') else 256)
        decoded[name] = decode_loading_blp(data, size)[0]; palettes.add(data[156:1180])
    require(len(palettes) == 1, 'Loading quadrants do not share one palette')
    data = (root / 'imports' / PREVIEW).read_bytes()
    require(data == lobby_tga(Image.open(source / '契灵守卫战-地图缩略图.png')),
            'Preview bytes differ from approved source')
    decode_preview_tga(data)
    return decoded


def verify_archive(current, baseline, root=ROOT):
    root = Path(root); verify_source(root)
    after, before = members(current), members(baseline)
    require(set(after) == set(before) | {PREVIEW.casefold()}, 'Unexpected packaged resource set delta')
    current_info, _ = parse_info(current.extract('war3map.w3i'))
    previous_info, _ = parse_info(baseline.extract('war3map.w3i'))
    name = current_info['name']
    stamp = re.fullmatch(re.escape(NAME) + r' (\d{8}-[0-2]\d[0-5]\d)-UTC\+8', name)
    require(stamp and name == current_info['title'], 'New branding/title timestamp mismatch')
    datetime.datetime.strptime(stamp[1], '%Y%m%d-%H%M')
    require(current_info['author'] == '留白散人' and current_info['subtitle'] == '作者：留白散人', 'Packed author changed')
    require(current_info['model'] == MODEL and current_info['description'] == DESCRIPTION and
            current_info['loading_text'] == DESCRIPTION, 'Packed approved metadata changed')
    require(current_info['flags'] == previous_info['flags'] & ~0x0001, 'Flags changed beyond hidden-preview bit 0x0001')
    require(normalized_info(current.extract('war3map.w3i')) == normalized_info(baseline.extract('war3map.w3i')),
            'W3I structure or unrelated fields changed')
    script, old_script = current.extract('war3map.j'), baseline.extract('war3map.j')
    for native, new, old in [('SetMapName', NAME, previous_info['name'].split(' ')[0]),
                             ('SetMapDescription', DESCRIPTION, previous_info['description'])]:
        now, was = f'call {native}("{new}")'.encode(), f'call {native}("{old}")'.encode()
        require(script.count(now) == old_script.count(was) == 1, 'Expected exact JASS config metadata call')
        script = script.replace(now, was)
    require(script == old_script, 'Gameplay JASS changed beyond the two config metadata calls')
    imports, previous = import_records(current.extract('war3map.imp')), import_records(baseline.extract('war3map.imp'))
    preview_import = [row for row in imports if row[1] == PREVIEW]
    require(len(preview_import) == 1 and preview_import[0][0] == 13, 'Root preview requires exact custom import flag 13')
    require([row[2] for row in imports if row[1] != PREVIEW] == [row[2] for row in previous], 'Existing import records changed')
    for path in (*TEXTURES.values(), MODEL, PREVIEW):
        local = (root / 'imports' / Path(path.replace('\\', '/'))).read_bytes()
        require(current.extract(path) == local, 'Packaged resource differs from source: ' + path)
        require(sum(flag == 13 and name == path for flag, name, _ in imports) == 1, 'Exact custom resource import missing: ' + path)
    require(current.extract(MODEL) == baseline.extract(MODEL), 'Packaged MDX changed')
    model_textures(current.extract(MODEL))
    allowed = {p.casefold() for p in TEXTURES.values()} | {'war3map.w3i', 'war3map.j', 'war3map.imp', '(attributes)', '(listfile)'}
    for key, (path, old) in before.items():
        require(after[key][0] == path, 'Resource spelling changed: ' + path)
        if key not in allowed:
            require(after[key][1] == old, 'Unrelated gameplay/object/minimap/resource changed: ' + path)
    require(current.extract('war3mapMap.blp') == baseline.extract('war3mapMap.blp'), 'Real in-game minimap changed')
    return {'display_name': name, 'resource_count': len(after), 'loading_model_sha256': MODEL_SHA256,
            'gameplay_jass': 'unchanged except exact map name/description config strings',
            'real_minimap': 'byte-for-byte unchanged', 'preview': 'root TGA256 alpha255 flag13',
            'runtime_rendering': 'not observed'}


def main():
    p = argparse.ArgumentParser(); p.add_argument('map'); p.add_argument('--baseline-map', required=True)
    p.add_argument('--root', type=Path, default=ROOT); p.add_argument('--preview-dir', type=Path)
    args = p.parse_args()
    result = verify_archive(Mpq(Path(args.map).read_bytes()), Mpq(Path(args.baseline_map).read_bytes()), args.root)
    if args.preview_dir:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
        tiles = verify_source(args.root); canvas = Image.new('RGB', (1024, 768))
        for name, (x, y, _, _) in TILES: canvas.paste(tiles[name], (x, y))
        canvas.save(args.preview_dir / 'loading-decoded.png')
        image = decode_preview_tga((args.root / 'imports' / PREVIEW).read_bytes())
        image.save(args.preview_dir / 'lobby-256.png')
        image.resize((128, 128), Image.Resampling.LANCZOS).save(args.preview_dir / 'lobby-128.png')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
