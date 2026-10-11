#!/usr/bin/env python3
"""Read-only P1 icon gate for the actual packed map, against its exact predecessor.

python tools/VerifySemanticIconArtifact.py map.w3x --baseline-map baseline.w3x

No compiler, asset generator, MPQ writer or gameplay launch is invoked. The
optional offline contact sheet is decoded from this map, labelled non-gameplay,
and written outside the repository. Pillow is the only additional dependency.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageOps
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'assets/source/semantic-icons/manifest.json'
NORMAL = 'war3mapImported\\BTN'
DISABLED = 'ReplaceableTextures\\CommandButtonsDisabled\\DISBTN'
NATIVE = 'ReplaceableTextures\\CommandButtons\\'
EQUIPMENT = {
    'iW01': 'ShortBow', 'iG01': 'SteelLongbow', 'iB01': 'WindrunnerBow',
    'iW02': 'EagleScope', 'iG02': 'HunterScope', 'iP01': 'WhiteTigerBanner',
    'iW04': 'CoolingRune', 'iW09': 'StableTotem', 'iG04': 'RhythmTotem',
    'iG08': 'FocusStone', 'iB04': 'FrostTome', 'iP03': 'CommandSeal',
    'iW06': 'ArmorSpike', 'iG03': 'WarAxe', 'iG07': 'LaceratingSpike',
    'iB02': 'BerserkerBadge', 'iB03': 'ArmorDrum', 'iP02': 'BlademasterSigil',
    'iW05': 'GoldRing', 'iW10': 'ScavengerBag', 'iG06': 'MercenaryPurse',
    'iB05': 'BountyContract', 'iB06': 'ExecutionMark', 'iP04': 'CorruptedHeart',
    'iW08': 'PoisonSac', 'iG05': 'ToxicVine',
}
ACTIONS = {'A119': 'InventoryCraft', 'Gupg': 'GroundUpgrade',
           'Pcap': 'CaptureOrb', 'Pmas': 'MasterCapture', 'Pfor': 'CaptureForge'}
TOWER_ABILITIES = {
    'A100': 'SplitShot', 'A101': 'TrueshotAura',
    'A102': 'CriticalStrike', 'A103': 'SwordDance', 'A104': 'ShieldBash',
    'A105': 'CommandAura', 'A106': 'PoisonDart', 'A107': 'Frenzy',
    'A110': 'VinesAura', 'A111': 'TrueshotAura', 'A112': 'CriticalStrike',
    'A113': 'ShieldBash', 'A114': 'PoisonDart', 'A115': 'Frenzy',
    'A116': 'CorpseExplosion', 'A131': 'Bloodlust', 'A132': 'Bladestorm',
    'A135': 'VinesAura', 'A136': 'VinesAura', 'A137': 'Frenzy',
    'A138': 'Frenzy', 'A139': 'SwordDance', 'A140': 'VinesAura',
    'A141': 'VinesAura', 'AeCM': 'CommandAura', 'AeSL': 'VinesAura',
}
TOWER_UNITS = dict(zip(
    ('uA6A', 'uA6B', 'uO6A', 'uO6B', 'uH6A', 'uH6B',
     'uD6A', 'uD6B', 'uG6A', 'uG6B'),
    ('SplitShot', 'TrueshotAura', 'Bloodlust', 'Bladestorm', 'ShieldBash',
     'CommandAura', 'PoisonDart', 'VinesAura', 'Frenzy', 'CorpseExplosion')))
TOWER_STEMS = tuple(sorted(set(TOWER_UNITS.values()) | {'SwordDance'}))
PET_STEMS = ('TDPetMenuTools', 'TDPetCollection', 'TDPetPrevious', 'TDPetNext',
             'TDPetReturnBuilder', 'TDPetDeploy', 'TDPetRecall', 'TDPetCultivate',
             'TDPetInfo', 'TDPetEmptySlot', 'TDPetFlamePhoenix',
             'TDPetStormFaerieDragon', 'TDPetGhostWisp')
SPECIES_STEMS = PET_STEMS[-3:]
OBJECT_FILES = {'units': ('war3map.w3u', False),
                'abilities': ('war3map.w3a', True),
                'items': ('war3map.w3t', False)}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def icon_path(stem, disabled=False):
    return (DISABLED if disabled else NORMAL) + stem + '.blp'


def normalized_path(path):
    require(isinstance(path, str) and bool(path), 'Empty resource path')
    require('/' not in path and '\\\\' not in path and
            all(part not in ('', '.', '..') for part in path.split('\\')),
            f'Non-canonical resource path {path!r}')
    return path.casefold()


@dataclass(frozen=True)
class Field:
    key: tuple
    kind: int
    value: object
    raw: bytes


@dataclass
class Object:
    table: int
    identity: bytes
    fields: dict

    def encoded(self):
        return self.identity + struct.pack('<I', len(self.fields)) + b''.join(
            field.raw for field in self.fields.values())


class Reader:
    def __init__(self, data):
        self.data, self.offset = data, 0

    def take(self, count):
        require(count >= 0 and self.offset + count <= len(self.data),
                'Truncated object/import record')
        value = self.data[self.offset:self.offset + count]
        self.offset += count
        return value

    def integer(self):
        return struct.unpack('<I', self.take(4))[0]

    def string(self):
        end = self.data.find(b'\0', self.offset)
        require(end >= self.offset, 'Unterminated object/import string')
        return self.take(end - self.offset + 1)[:-1].decode('utf-8')


def parse_objects(data, extended):
    """Keep every field's encoding, float bits, end marker, order and identity."""
    reader = Reader(data)
    require(reader.integer() == 2, 'Only object version 2 is supported')
    objects = {}
    for table in range(2):
        for _ in range(reader.integer()):
            identity = reader.take(8)
            rawcode = (identity[4:] if identity[4:] != b'\0' * 4 else identity[:4]).decode('ascii')
            require(rawcode not in objects, f'Duplicate object {rawcode}')
            fields = {}
            for _ in range(reader.integer()):
                start = reader.offset
                name, kind = reader.take(4).decode('ascii'), reader.integer()
                level, column = (reader.integer(), reader.integer()) if extended else (0, 0)
                require(kind in (0, 1, 2, 3), f'{rawcode}.{name}: invalid kind {kind}')
                value = (reader.string() if kind == 3 else
                         struct.unpack('<i' if kind == 0 else '<f', reader.take(4))[0])
                reader.take(4)  # Preserve and compare object modification end marker.
                key = (name, level, column)
                require(key not in fields, f'{rawcode}: duplicate field {key}')
                fields[key] = Field(key, kind, value, data[start:reader.offset])
            objects[rawcode] = Object(table, identity, fields)
    require(reader.offset == len(data), 'Trailing object bytes')
    return objects


def load_objects(artifact):
    return {kind: parse_objects(artifact.extract(path), extended)
            for kind, (path, extended) in OBJECT_FILES.items()}


def expected_bindings():
    """Closed rawcode/field allow-list; never inferred from final map/manifest."""
    bindings = {}
    def add(kind, rawcode, fields, stem):
        for field in fields:
            bindings[kind, rawcode, (field, 0, 0)] = icon_path(stem)
    for rawcode, name in EQUIPMENT.items():
        add('items', rawcode, ('iico',), 'TDItem' + name)
    add('items', 'Ibal', ('iico',), 'TDActionCaptureOrb')
    for rawcode, name in ACTIONS.items():
        add('abilities', rawcode, ('aart', 'arar'), 'TDAction' + name)
    for rawcode, name in TOWER_ABILITIES.items():
        add('abilities', rawcode, ('aart', 'arar'), 'TDTower' + name)
        if rawcode in ('A131', 'A132'):
            add('abilities', rawcode, ('auar',), 'TDTower' + name)
    for rawcode, name in TOWER_UNITS.items():
        add('units', rawcode, ('uico', 'ussi'), 'TDTower' + name)
    for wave in range(1, 33):
        for species, stem in enumerate(SPECIES_STEMS, 1):
            add('units', f'p{wave:02X}{species}', ('uico', 'ussi'), stem)
    return bindings


BINDINGS = expected_bindings()


def verify_bindings(objects):
    for (kind, rawcode, key), path in BINDINGS.items():
        require(rawcode in objects[kind], f'Missing {kind} object {rawcode}')
        field = objects[kind][rawcode].fields.get(key)
        require(field is not None and field.kind == 3 and field.value == path,
                f'{rawcode}.{key[0]}: exact global icon binding mismatch; expected {path}')
    for rawcode, name in (('iW03', 'BTNGlove'), ('iW07', 'BTNDaggerOfEscape')):
        field = objects['items'][rawcode].fields.get(('iico', 0, 0))
        require(field is not None and field.kind == 3 and field.value == NATIVE + name + '.blp',
                f'{rawcode}: retained native equipment icon changed')
    capture = objects['abilities']['Pcap']
    levels = capture.fields.get(('alev', 0, 0))
    require(levels is not None and levels.kind == 0 and levels.value == 61,
            'Pcap must retain sixty-one functional levels')
    require({key[1] for key in capture.fields if key[1] > 0} == set(range(1, 62)),
            'Pcap functional level coverage must remain exactly 1..61')
    require(not any(key[0] in ('aart', 'arar') and key[1:] != (0, 0)
                    for key in capture.fields), 'Pcap icon fields must be global, not level-specific')
    for slot in range(4):
        for variant in range(129):
            rawcode = f's{slot}{variant:02X}'
            require(rawcode in objects['abilities'], f'Missing pet slot object {rawcode}')
            if variant % 64 // 4 == 11 and variant != 128:
                path = (DISABLED if variant >= 64 else NATIVE + 'BTN') + 'BloodLust.blp'
                field = objects['abilities'][rawcode].fields.get(('aart', 0, 0))
                require(field is not None and field.kind == 3 and field.value == path,
                        f'{rawcode}: native BloodLust icon polluted')


def verify_object_delta(objects, baseline):
    verify_bindings(objects)
    slots = {f's{slot}{variant:02X}' for slot in range(4) for variant in range(129)}
    for kind in OBJECT_FILES:
        current, before = objects[kind], baseline[kind]
        require(set(current) == set(before), f'{kind}: object set changed')
        for rawcode, obj in current.items():
            old = before[rawcode]
            require((obj.table, obj.identity) == (old.table, old.identity),
                    f'{rawcode}: object identity/parent/table changed')
            if kind == 'abilities' and rawcode in slots:
                require(obj.encoded() == old.encoded(), f'{rawcode}: pet slot object must be wholly identical')
            for key in set(obj.fields) | set(old.fields):
                field, previous = obj.fields.get(key), old.fields.get(key)
                if (kind, rawcode, key) not in BINDINGS:
                    require(field == previous,
                            f'{rawcode}.{key}: forbidden non-icon or non-allowlisted field delta')
                else:
                    require(field is not None and field.kind == 3,
                            f'{rawcode}.{key}: removed or wrongly encoded permitted icon field')
                    if previous is not None:
                        # Only the icon string may change, never its field metadata/end marker.
                        header = 16 if kind == 'abilities' else 8
                        require(field.raw[:header] == previous.raw[:header] and
                                field.raw[-4:] == previous.raw[-4:],
                                f'{rawcode}.{key}: icon encoding metadata changed')
    pcap = objects['abilities']['Pcap'].fields
    old_pcap = baseline['abilities']['Pcap'].fields
    for level in range(1, 62):
        require({k: f for k, f in pcap.items() if k[1] == level} ==
                {k: f for k, f in old_pcap.items() if k[1] == level},
                f'Pcap functional level {level} changed')


def import_records(data):
    reader = Reader(data)
    require(reader.integer() == 1, 'Unsupported import manifest version')
    count, names = reader.integer(), []
    for _ in range(count):
        flag = reader.take(1)[0]
        require(flag in (5, 8, 10, 13), f'Unsupported import path flag {flag}')
        name = reader.string()
        names.append(name if flag in (10, 13) else 'war3mapImported\\' + name)
    require(reader.offset == len(data), 'Trailing import manifest bytes')
    return names


def unique_paths(names, label):
    seen = {}
    for name in names:
        folded = normalized_path(name)
        require(folded not in seen, f'{label}: casefold duplicate {name!r} / {seen.get(folded)!r}')
        seen[folded] = name
    return seen


def verify_paths(artifact, root):
    imported = [str(path.relative_to(root / 'imports')).replace('/', '\\')
                for path in (root / 'imports').rglob('*') if path.is_file()]
    source_paths = unique_paths(imported, 'imports')
    list_names = artifact.extract('(listfile)').decode('utf-8-sig').splitlines()
    listed_paths = unique_paths([name for name in list_names if name], 'MPQ listfile')
    mpq_imports = import_records(artifact.extract('war3map.imp'))
    packed_paths = unique_paths(mpq_imports, 'war3map.imp')
    # Also reject duplicate active MPQ hash entries, including members hidden
    # from the listfile. A locale/platform alias cannot rescue a path collision.
    hashes = set()
    for a, b, _locale, _platform, block in artifact.hashes:
        if block >= len(artifact.blocks) or not artifact.blocks[block][3] & 0x80000000:
            continue
        require((a, b) not in hashes, 'MPQ hash table: duplicate casefold resource entry')
        hashes.add((a, b))
    forbidden = [icon_path(stem, disabled) for stem in TOWER_STEMS
                 for disabled in (False, True)]
    # Slots still reference native BloodLust. Neither native normal nor disabled
    # resource may be shadowed by an import; disabled is also an old tower name.
    forbidden.append(NATIVE + 'BTNBloodLust.blp')
    for old in forbidden:
        require(old.casefold() not in source_paths and old.casefold() not in packed_paths and
                old.casefold() not in listed_paths and not artifact.has(old),
                f'Obsolete tower/native collision path remains: {old}')
    return source_paths, packed_paths


def decode_blp(data, path):
    """Strict BLP1 alpha8 decoder for every mip, independent of the converter."""
    require(len(data) >= 1180 and data[:4] == b'BLP1', f'{path}: invalid/truncated BLP1')
    require(struct.unpack_from('<6I', data, 4) == (1, 8, 64, 64, 5, 1),
            f'{path}: expected 64x64 palette BLP1 alpha8/mips')
    offsets, sizes = (struct.unpack_from('<16I', data, offset) for offset in (28, 92))
    palette = [(data[i + 2], data[i + 1], data[i]) for i in range(156, 1180, 4)]
    result, cursor = [], 1180
    for level in range(16):
        if level >= 7:
            require(offsets[level] == sizes[level] == 0, f'{path}: unexpected mip {level}')
            continue
        width = 64 >> level
        count = width * width
        require(sizes[level] == count * 2, f'{path}: mip {level} alpha8 size mismatch')
        require(offsets[level] == cursor and cursor + sizes[level] <= len(data),
                f'{path}: mip {level} missing/overlapping/out of bounds')
        indices, alpha = data[cursor:cursor + count], data[cursor + count:cursor + count * 2]
        rgba = bytes(component for index, opacity in zip(indices, alpha)
                     for component in (*palette[index], opacity))
        result.append(Image.frombytes('RGBA', (width, width), rgba))
        cursor += sizes[level]
    require(cursor == len(data), f'{path}: trailing BLP bytes')
    require(result[0].getchannel('A').getextrema()[1] > 0, f'{path}: fully transparent icon')
    require(result[0].getcolors(4) is None, f'{path}: no usable artwork')
    return result


def expected_pixels(image):
    """Rebuild the approved median-cut palette and seven decoded source mips."""
    image = image.convert('RGBA')
    palette = image.convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    result = []
    for level in range(7):
        width = 64 >> level
        mip = image.resize((width, width), Image.Resampling.LANCZOS)
        rgb = mip.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE).convert('RGBA')
        rgb.putalpha(mip.getchannel('A'))
        result.append(rgb)
    return result


def source_icon(entry, root):
    path = root / entry['source']
    require(not Path(entry['source']).is_absolute() and path.resolve().is_relative_to(root.resolve()),
            f'{entry["name"]}: source must be repository-relative')
    data = path.read_bytes()
    require(sha(data) == entry['source_sha256'], f'{entry["name"]}: source hash mismatch')
    with Image.open(path) as source:
        box = entry['crop']
        require(len(box) == 4 and all(type(value) is int for value in box) and
                0 <= box[0] < box[2] <= source.width and 0 <= box[1] < box[3] <= source.height,
                f'{entry["name"]}: invalid crop')
        return source.convert('RGBA').crop(box).resize((64, 64), Image.Resampling.LANCZOS)


def disabled_image(image):
    disabled = ImageOps.grayscale(image).convert('RGBA')
    disabled.putalpha(image.getchannel('A'))
    return ImageEnhance.Brightness(disabled).enhance(0.45)


def expected_asset_contract():
    assets = {name: ('TDItem' + name, {rawcode}) for rawcode, name in EQUIPMENT.items()}
    assets.update({name: ('TDAction' + name, {rawcode}) for rawcode, name in ACTIONS.items()})
    assets['CaptureOrb'][1].add('Ibal')
    assets['CriticalStrike'] = ('TDTowerCriticalStrike', {'A102', 'A112'})
    return assets


def manifest_contract(manifest):
    require(manifest.get('schemaVersion') == 1, 'Semantic manifest schemaVersion must be 1')
    contract = expected_asset_contract()
    entries = manifest.get('assets', [])
    require(len(entries) == 32 and {e['name'] for e in entries} == set(contract),
            'Semantic manifest must contain exactly thirty-two approved assets')
    for entry in entries:
        stem, rawcodes = contract[entry['name']]
        require(entry['normal'] == icon_path(stem) and entry['disabled'] == icon_path(stem, True),
                f'{entry["name"]}: manifest resource path mismatch')
        require(isinstance(entry['rawcodes'], list) and len(entry['rawcodes']) == len(rawcodes) and
                set(entry['rawcodes']) == rawcodes, f'{entry["name"]}: manifest rawcodes mismatch')
    for key, names, prefix in (('towerMigrations', TOWER_STEMS, 'TDTower'),
                               ('preservedPetUI', PET_STEMS, '')):
        records = manifest.get(key, [])
        require(len(records) == len(names) and {e['name'] for e in records} == set(names),
                f'{key}: exact preserved pair set mismatch')
        for entry in records:
            stem = prefix + entry['name']
            require(entry['normal'] == icon_path(stem) and entry['disabled'] == icon_path(stem, True),
                    f'{entry["name"]}: preserved resource path mismatch')
            if key == 'towerMigrations':
                require(entry['old_normal'] == icon_path(entry['name']) and
                        entry['old_disabled'] == icon_path(entry['name'], True),
                        f'{entry["name"]}: old migration path mismatch')
    unique_paths([e[field] for key in ('assets', 'towerMigrations', 'preservedPetUI')
                  for e in manifest[key] for field in ('normal', 'disabled')], 'manifest')


def verify_resources(artifact, baseline, root, manifest, paths):
    manifest_contract(manifest)
    source_paths, packed_paths = paths
    decoded, hashes = {}, set()
    for category in ('assets', 'towerMigrations', 'preservedPetUI'):
        for entry in manifest[category]:
            source = source_icon(entry, root) if category == 'assets' else None
            for disabled in (False, True):
                field = 'disabled' if disabled else 'normal'
                path = entry[field]
                folded = normalized_path(path)
                require(folded in source_paths and folded in packed_paths and artifact.has(path),
                        f'Missing exact imported/packed icon {path}')
                data = artifact.extract(path)
                local = root / 'imports' / Path(path.replace('\\', '/'))
                require(data == local.read_bytes(), f'{path}: packed bytes differ from imports')
                require(sha(data) == entry[field + '_sha256'], f'{path}: manifest icon hash mismatch')
                images = decode_blp(data, path)
                if category == 'assets':
                    expected = expected_pixels(disabled_image(source) if disabled else source)
                    for level, (actual, wanted) in enumerate(zip(images, expected)):
                        require(actual.tobytes() == wanted.tobytes(),
                                f'{path}: source-conversion pixels/alpha mismatch at mip {level}')
                else:
                    old_path = entry['old_' + field] if category == 'towerMigrations' else path
                    require(baseline.has(old_path) and data == baseline.extract(old_path),
                            f'{path}: preserved baseline artwork bytes changed')
                require(sha(data) not in hashes, f'{path}: duplicate semantic artwork bytes')
                hashes.add(sha(data))
                decoded[path] = images[0]
            normal, gray = decoded[entry['normal']], decoded[entry['disabled']]
            require(normal.getchannel('A').tobytes() == gray.getchannel('A').tobytes(),
                    f'{entry["name"]}: normal/disabled alpha differs')
            red, green, blue, _alpha = gray.split()
            require(red.tobytes() == green.tobytes() == blue.tobytes(),
                    f'{entry["name"]}: disabled icon must be grayscale')
            normal_sum = sum(sum(channel.tobytes()) for channel in normal.split()[:3])
            gray_sum = sum(red.tobytes()) * 3
            require(0 < gray_sum < normal_sum * 0.60,
                    f'{entry["name"]}: disabled icon is blank or not visibly dimmer')
    return decoded


def contact_sheet(decoded, manifest, map_sha, target, root=ROOT):
    target = Path(target).resolve()
    require(not target.is_relative_to(root.resolve()), 'Keep offline contact sheet outside repository')
    records = [(category, entry) for category in ('assets', 'towerMigrations', 'preservedPetUI')
               for entry in manifest[category]]
    cell_width, cell_height, columns, top = 448, 190, 4, 70
    sheet = Image.new('RGB', (columns * cell_width, top + ((len(records) + columns - 1) // columns) * cell_height), '#15171b')
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 8), 'OFFLINE PACKED ICON CONTACT SHEET | NON-GAMEPLAY', fill='white')
    draw.text((12, 28), 'Actual map SHA256: ' + map_sha, fill='#cccccc')
    draw.text((12, 46), 'Actual 64px + nearest-neighbor 2x previews decoded from this MPQ; not a game screenshot.', fill='#cccccc')
    for index, (category, entry) in enumerate(records):
        x, y = (index % columns) * cell_width, top + (index // columns) * cell_height
        for offset, key in ((10, 'normal'), (226, 'disabled')):
            original = decoded[entry[key]]
            enlarged = original.resize((128, 128), Image.Resampling.NEAREST)
            sheet.paste(original, (x + offset, y + 34), original)
            sheet.paste(enlarged, (x + offset + 72, y + 2), enlarged)
            draw.text((x + offset, y + 102), key.upper() + ' 64px', fill='#aaaaaa')
            draw.text((x + offset + 72, y + 132), key.upper() + ' 2x 128px', fill='#aaaaaa')
        draw.text((x + 10, y + 150), entry['name'], fill='white')
        draw.text((x + 10, y + 166), category, fill='#888888')
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--baseline-map', type=Path, required=True,
                        help='Frozen actual compiled predecessor, before P1 icon changes')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--contact-sheet', type=Path,
                        help='Offline output outside repository; default /tmp includes map SHA')
    args = parser.parse_args(argv)
    data, before = args.map.read_bytes(), args.baseline_map.read_bytes()
    require(data != before, 'Final map and baseline map are identical; no P1 artifact to verify')
    artifact, baseline = Mpq(data), Mpq(before)
    manifest_path = args.manifest or args.root / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    verify_object_delta(load_objects(artifact), load_objects(baseline))
    paths = verify_paths(artifact, args.root)
    decoded = verify_resources(artifact, baseline, args.root, manifest, paths)
    digest = sha(data)
    target = args.contact_sheet or Path('/tmp') / f'semantic-icons-{digest[:12]}-offline.png'
    target = contact_sheet(decoded, manifest, digest, target, args.root)
    print('PASS: exact rawcode/global-field bindings; 28 equipment, 5 actions, critical strike, '
          'all tower icon uses and 96 wild identities; 516 whole pet slots and 61 Pcap levels unchanged.')
    print('PASS: 32 source-reproducible + 11 byte-preserved tower + 13 byte-preserved pet UI pairs; '
          'MPQ/import hashes, all seven decoded mips/alpha, casefold uniqueness and old-path absence.')
    print(f'FINAL MAP SHA256: {digest}')
    print(f'BASELINE MAP SHA256: {sha(before)}')
    print(f'OFFLINE NON-GAMEPLAY CONTACT SHEET: {target}; SHA256={sha(target.read_bytes())}')
    print('NOT TESTED: in-game command rendering, portraits, gameplay or performance.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, struct.error, OSError, UnicodeError, AssertionError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        sys.exit(1)
