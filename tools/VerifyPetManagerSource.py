#!/usr/bin/env python3
"""Bounded source-only manager checks. Never runs Wurst, staging, map build or game.

Executes selected real scalar/navigation source bodies in a small Python subset,
then checks runtime wiring and the exact source asset manifest. This cannot prove
Wurst syntax/types, compiletime objects, packaged MPQ, or native selection events.
"""
from __future__ import annotations
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'c9d59e6482d13c97bd205b7b55276f06e416cf46'
ASSET_BASELINE = '0330fd12de4d66c4a1ca4980e10b771f0903fbfc'
FILES = ('TDPetData', 'TDPetRules', 'TDPetState', 'TDPetUIState', 'TDPetUIView', 'TDPetUI', 'TDPetObjectGen')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source(name):
    return (ROOT / f'wurst/pets/{name}.wurst').read_text(encoding='utf-8')


def function_body(text, name, arity=None):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.fullmatch(r'(\t*)(?:public )?function ' + re.escape(name) + r'\((.*?)\)(?: returns \w+)?', line)
        if not match:
            continue
        parameters = [p.strip().split()[-1] for p in match[2].split(',') if p.strip()]
        if arity is not None and len(parameters) != arity:
            continue
        indent = len(match[1])
        body = []
        for following in lines[index + 1:]:
            if following.strip() and len(following) - len(following.lstrip('\t')) <= indent:
                break
            body.append(following[indent + 1:])
        return parameters, '\n'.join(body).rstrip()
    raise ValueError(f'Missing real source function {name}/{arity}')


def _expression(text):
    """Only the controlled subset in selected helper bodies, fail on leftovers."""
    # Recursively normalize parenthesized ternaries and comma-separated arguments.
    def nested(value):
        result, i = '', 0
        while i < len(value):
            ch = value[i]
            if ch in ('"', "'"):
                quote, end = ch, i + 1
                while end < len(value):
                    if value[end] == '\\':
                        end += 2
                    elif value[end] == quote:
                        break
                    else:
                        end += 1
                require(end < len(value), 'Unterminated source string')
                result += value[i:end + 1]
                i = end + 1
            elif ch == '(':
                end, depth, quote = i + 1, 1, None
                while end < len(value) and depth:
                    c = value[end]
                    if quote:
                        if c == '\\':
                            end += 1
                        elif c == quote:
                            quote = None
                    elif c in ('"', "'"):
                        quote = c
                    elif c == '(':
                        depth += 1
                    elif c == ')':
                        depth -= 1
                    end += 1
                require(depth == 0, 'Unbalanced source parentheses')
                result += '(' + nested(value[i + 1:end - 1]) + ')'
                i = end
            else:
                result += ch
                i += 1
        # Find top-level separators, ignoring quoted literals and nested groups.
        depth, quote, comma, question, colon = 0, None, [], None, None
        i = 0
        while i < len(result):
            ch = result[i]
            if quote:
                if ch == '\\':
                    i += 1
                elif ch == quote:
                    quote = None
            elif ch in ('"', "'"):
                quote = ch
            elif ch in '([':
                depth += 1
            elif ch in ')]':
                depth -= 1
            elif depth == 0:
                if ch == ',':
                    comma.append(i)
                elif ch == '?' and question is None:
                    question = i
                elif ch == ':' and question is not None:
                    colon = i
                    break
            i += 1
        if comma:
            indices = [-1] + comma + [len(result)]
            return ','.join(nested(result[a + 1:b]) for a, b in zip(indices, indices[1:]))
        if question is not None:
            require(colon is not None, 'Malformed source ternary')
            return '(' + nested(result[question + 1:colon]) + ' if ' + nested(result[:question]) + ' else ' + nested(result[colon + 1:]) + ')'
        return result
    text = nested(text)
    # Wurst implicitly converts an integer in string concatenation. This
    # controlled source helper retains the independent false-branch conversion.
    text = re.sub(r'("0"\s*\+\s*)(\(slot\s*\+\s*1\))', r'\1str(\2)', text)
    text = re.sub(r'\bdiv\b', '//', text)
    text = re.sub(r'\bmod\b', '%', text)
    text = re.sub(r'\btrue\b', 'True', text)
    text = re.sub(r'\bfalse\b', 'False', text)
    text = re.sub(r'\bnull\b', 'None', text)
    text = re.sub(r"'([^']{4})'", lambda m: str(int.from_bytes(m[1].encode('ascii'), 'big')), text)
    text = re.sub(r'(\([^()]+\)|\w+)\.toString\(\)', r'str(\1)', text)
    if text.endswith('.fromRawCode()'):
        text = 'rawcode(' + text[:-len('.fromRawCode()')] + ')'
    require('?' not in text and ' castTo ' not in text and '.fromRawCode' not in text and '.toString' not in text,
            f'Unsupported source-only expression: {text}')
    return text


def compile_source_helper(text, name, namespace, arity=None):
    parameters, body = function_body(text, name, arity)
    output = [f'def {name}(' + ','.join(parameters) + '):']
    for raw in body.splitlines():
        line = raw.lstrip('\t')
        if not line.strip() or line.startswith('//'):
            continue
        indent = 1 + len(raw) - len(line)
        if line.startswith('let ') or line.startswith('var '):
            line = line[4:]
        if line.startswith('else if '):
            line = 'elif ' + _expression(line[8:]) + ':'
        elif line.startswith('if '):
            line = 'if ' + _expression(line[3:]) + ':'
        elif line == 'else':
            line = 'else:'
        elif line.startswith('for '):
            match = re.fullmatch(r'for (\w+) = (.*?) to (.*)', line)
            require(match is not None, 'Unsupported source-only loop')
            line = f'for {match[1]} in range({_expression(match[2])}, ({_expression(match[3])}) + 1):'
        elif line.startswith('return '):
            line = 'return ' + _expression(line[7:])
        elif ' = ' in line:
            left, right = line.split(' = ', 1)
            line = left + ' = ' + _expression(right)
        elif ' += ' in line:
            left, right = line.split(' += ', 1)
            line = left + ' += ' + _expression(right)
        elif ' -= ' in line:
            left, right = line.split(' -= ', 1)
            line = left + ' -= ' + _expression(right)
        else:
            raise ValueError(f'Unsupported source-only statement: {line}')
        output.append('    ' * indent + line)
    exec('\n'.join(output), {'__builtins__': {}, **namespace}, namespace)
    # Functions need one shared global namespace for cross-helper calls.
    namespace[name] = type(namespace[name])(namespace[name].__code__, namespace, name)
    return namespace[name]


def scalar_helpers():
    namespace = {'range': range, 'str': str, 'IMaxBJ': max, 'IMinBJ': min,
                 'SubString': lambda text, start, end: text[start:end],
                 'rawcode': lambda text: int.from_bytes(text.encode('ascii'), 'big'),
                 'tdIsLanePlayer': lambda lane: 0 <= lane < 4,
                 'tdPetAt': lambda _lane, _slot: None, '__builtins__': {}}
    for name in FILES:
        for constant, value in re.findall(r'public constant int (\w+) = (-?\d+)', source(name)):
            namespace[constant] = int(value)
    for name, value in re.findall(r'public constant int (TD_PET_HERO_\w+) = (\d+)', source('TDPetHeroRules')):
        namespace[name] = int(value)
    namespace['TD_PET_SLOT_EMPTY'] = namespace['TD_PET_SKILL_COUNT'] * 2
    targets = {
        'TDPetData': [('tdPetHexRawcode', 3), ('tdPetHex3Rawcode', 3), ('tdPetDisplayUnitId', 2), ('tdPetListAbilityId', 4), ('tdPetPreviewAbilityId', 2), ('tdPetPreviewArrowAbilityId', 1), ('tdPetUICommandId', 1), ('tdPetManagerCommandId', 1), ('tdPetSlotAbilityId', 2)],
        'TDPetHeroRules': [('tdPetHeroDefined', 1), ('tdPetHeroName', 1), ('tdPetHeroHostName', 1), ('tdPetHeroHostTypeId', 1), ('tdPetHeroFitsRawcode', 2)],
        'TDPetHeroData': [('tdPetHeroIconName', 1)],
        'TDPetElementData': [('tdPetSkillElement', 1), ('tdPetSkillFixedQuality', 1), ('tdPetElementSkillName', 1)],
        'TDPetRules': [('tdPetCollectionNumber', 1), ('tdPetPageSlot', 2), ('tdPetStepSlot', 2), ('tdPetOwnedQuality', 5), ('tdPetSkillDefined', 1), ('tdPetSkillIsNumeric', 1), ('tdPetSkillOwned', 5), ('tdPetSkillNameById', 1)],
        'TDPetUIState': [('tdPetActionCell', 2), ('tdPetActionHotkey', 1), ('tdPetListHotkey', 1)],
        'TDPetState': [('tdPetNextOccupied', 3)],
    }
    for package, helpers in targets.items():
        for name, arity in helpers:
            compile_source_helper(source(package), name, namespace, arity)
    return namespace


def verify_scalar_contracts(namespace=None):
    from VerifyPetUIArtifact import MANAGER_COMMANDS, PAGE_ACTIONS, expected_action_cell, manager_rawcode
    n = namespace or scalar_helpers()
    for mode, action in itertools.product(range(-1, 6), range(-1, 122)):
        require(n['tdPetActionCell'](mode, action) == expected_action_cell(mode, action), f'Source page whitelist {mode}/{action}')
    for action in range(23):
        require(n['tdPetActionHotkey'](action) == MANAGER_COMMANDS[manager_rawcode(action)][2], f'Source hotkey {action}')
    channels = {n['tdPetManagerCommandId'](action) for action in range(23)}
    for cell, variant in itertools.product(range(10), range(n['TD_PET_LIST_VARIANTS'])):
        species, quality, count = (0, 0, 0) if variant == 0 else ((variant - 1) // 16 + 1, ((variant - 1) % 16) // 4 + 1, (variant - 1) % 4 + 1)
        identifier = n['tdPetListAbilityId'](cell, species, quality, count)
        require(identifier == int.from_bytes(f'L{cell * n['TD_PET_LIST_VARIANTS'] + variant:03X}'.encode(), 'big'), 'Source list rawcode mismatch')
        require(identifier not in channels, 'Source manager Channel collision')
        channels.add(identifier)
    passives = {n['tdPetSlotAbilityId'](slot, variant) for slot, variant in itertools.product(range(4), range(n['TD_PET_SLOT_EMPTY'] + 1))}
    passives.update(n['tdPetPreviewAbilityId'](position, skill) for position, skill in itertools.product(range(2), range(n['TD_PET_SKILL_COUNT'])))
    passives.update(n['tdPetPreviewArrowAbilityId'](position) for position in range(2))
    require(len(channels) == 23 + 10 * n['TD_PET_LIST_VARIANTS'] and len(passives) == 4 * (n['TD_PET_SLOT_EMPTY'] + 1) + 2 * n['TD_PET_SKILL_COUNT'] + 2 and not channels & passives, 'Source object/rawcode capacity/collision mismatch')
    for cell, species, quality, count in itertools.product(range(-1, 11), range(-1, n['TD_PET_SPECIES_COUNT'] + 2), range(-1, 6), range(-1, 6)):
        valid = 0 <= cell < 10 and ((species, quality, count) == (0, 0, 0) or (1 <= species <= n['TD_PET_SPECIES_COUNT'] and 1 <= quality <= 4 and 1 <= count <= 4))
        require((n['tdPetListAbilityId'](cell, species, quality, count) != 0) == valid, 'Invalid list portrait/count must fail closed')
    for cell in range(10):
        require(n['tdPetListHotkey'](cell) == 'QWETASDFZX'[cell], 'Source list hotkey mismatch')
        for page in range(2):
            slot = n['tdPetPageSlot'](page, cell)
            require(slot == page * 10 + cell and n['tdPetCollectionNumber'](slot) == f'{slot + 1:02d}', 'Source fixed-page number mismatch')
    for count in range(5):
        for qualities in itertools.product(range(1, 5), repeat=4):
            require(n['tdPetOwnedQuality'](count, *qualities) == max((1, *qualities[:count])), 'Owned quality must include every owned skill only')
    for occupied in (set(), {0}, {19}, {0, 3, 10, 19}, set(range(20))):
        n['tdPetAt'] = lambda lane, slot, occupied=occupied: object() if lane == 0 and slot in occupied else None
        for slot, direction in itertools.product(range(20), (-1, 1)):
            expected = next(((slot + step * direction) % 20 for step in range(1, 21) if (slot + step * direction) % 20 in occupied), -1)
            require(n['tdPetNextOccupied'](0, slot, direction) == expected, 'Source skip-hole navigation mismatch')
            require(n['tdPetNextOccupied'](1, slot, direction) == -1, 'Source lane isolation mismatch')
    for function, args in [('tdPetListAbilityId', (10, 1, 1, 1)), ('tdPetListAbilityId', (0, 16, 1, 1)), ('tdPetPreviewAbilityId', (2, 0)), ('tdPetPreviewArrowAbilityId', (2,)), ('tdPetManagerCommandId', (23,)), ('tdPetSlotAbilityId', (4, 0)), ('tdPetSlotAbilityId', (0, 129)), ('tdPetDisplayUnitId', (16, 1))]:
        require(n[function](*args) == 0, 'Source out-of-partition rawcode must fail closed')
    # Full source literal collision scan, not merely the new namespace itself.
    reserved = channels | passives | {n['tdPetDisplayUnitId'](species, quality) for species, quality in itertools.product(range(1, n['TD_PET_SPECIES_COUNT'] + 1), range(1, 5))} | {int.from_bytes(b'pd00', 'big')}
    allowed = {'TDPetData.wurst', 'TDPetObjectGen.wurst'}
    for path in (ROOT / 'wurst').rglob('*.wurst'):
        if path.name in allowed or '_tests' in path.parts:
            continue
        for literal in re.findall(r"'([A-Za-z0-9]{4})'", path.read_text(encoding='utf-8')):
            require(int.from_bytes(literal.encode(), 'big') not in reserved, f'Rawcode reservation collision in {path.relative_to(ROOT)}: {literal}')
    print('PASS SOURCE SCALARS: 861 page/action cases; definition-derived Channel identities; definition-sized passive rawcode capacity; exhaustive count inputs; 20 numbers; 1,280 quality cases; navigation and boundary guards')


def verify_wiring(*, verify_legacy_wild_scope=True):
    texts = {name: source(name) for name in FILES}
    ui, view, state, session, objects = (texts[n] for n in ('TDPetUI', 'TDPetUIView', 'TDPetState', 'TDPetUIState', 'TDPetObjectGen'))
    require('TD_PET_COLLECTION_LIMIT = 20' in texts['TDPetData'], 'Collection capacity must be twenty')
    require('tdPetOwnedQuality(skillCount, qualities[0], qualities[1], qualities[2], qualities[3])' in function_body(state, 'quality')[1], 'Record quality must include all four owned slots independently of resonance/proposal')
    for name in ('TDPetUI', 'TDPetUIView', 'TDPetUIState'):
        require(not re.search(r'\b(?:Dialog\w*|Blz\w*|Dz\w*)\b', texts[name]), f'{name}: forbidden dialog/modern native')
    for text in texts.values():
        for line in text.splitlines():
            code = line.split('//', 1)[0]
            # Explicit guards avoid the known mixed and/or JASS printer defect.
            require(not (' and ' in code and ' or ' in code), 'Mixed boolean precedence in new pet source: ' + line)
    command = function_body(ui, 'onCommand')[1]
    for phrase in ('caster != tdPetDisplays[lane]', 'tdPetDisplayOwners.hasInt', 'GetUnitAbilityLevel', 'session.admitCommand', 'tdPetResolveRerollVersion'):
        require(phrase in command, 'Missing synchronized command authority: ' + phrase)
    require(command.index('session.admitCommand') < command.index('tdPetDeploy('), 'Consume authority before transaction')
    admission = function_body(session, 'admitCommand')[1]
    for phrase in ('commandAction(', 'dirty or not snapshotCurrent()', 'releaseNonce != tdPetReleaseNonce(lane)', 'consumeCommand(', 'TD_PET_COMMAND_STALE', 'TD_PET_COMMAND_REFRESH', 'TD_PET_COMMAND_EMPTY'):
        require(phrase in admission, 'Missing production admission: ' + phrase)
    require('tdPetDeploy(' not in function_body(ui, 'onDeploy')[1], 'Farmer deployment bypass remains')
    poll = ui.split('doPeriodically(0.5)', 1)[1]
    require(not any(x in poll for x in ('showPage(', 'tdPetRenderPage(', 'SelectUnit(', 'createUnit(')), 'Poller churns display/selection')
    refresh = function_body(view, 'tdPetRefreshDisplay')[1]
    require('dirty = true' in refresh and 'tdPetCancelRelease' in refresh, 'Poll invalidation must dirty snapshot/cancel release')
    render = function_body(view, 'tdPetRenderPage')[1]
    require(render.index('fresh.addPermanentAbility') < render.index('tdPetDisplays[lane] = fresh') < render.index('retire(old)') < render.index('GetLocalPlayer'), 'Prepare/publish/retire/local selection order')
    retire = function_body(view, 'retire')[1]
    require('tdPetDisplayOwners.removeInt' in retire and 'doAfter(0.0)' in retire and 'old.remove()' in retire and 'pet.' not in retire and 'session.' not in retire, 'Retirement captures only the old unit')
    for function in ('tdPetSelectFarmer', 'tdPetRenderPage'):
        body = function_body(view, function)[1]
        local = body.split('if GetLocalPlayer()', 1)[1]
        require(not any(x in local for x in ('createUnit(', 'addPermanentAbility(', 'saveInt(', ' = ', 'tdPetCancelRelease(')), 'Local selection writes synchronized authority')
    for name, suffix in (('onSelected', 'false)'), ('onDeselected', 'true)')):
        require('tdPetHandleSelectionIdentity(' in function_body(ui, name)[1] and suffix in function_body(ui, name)[1], 'Native selection must use production identity bridge: ' + name)
    selection = function_body(session, 'selectionCloses')[1]
    for phrase in ('owner != lane', 'return eventKey == currentKey', 'typeId == 0', 'tdPetIsDisplayType(typeId)', 'unitOwner == lane'):
        require(phrase in selection, 'Selection identity protection missing: ' + phrase)
    require('selectionCloses(' in function_body(view, 'tdPetHandleSelectionIdentity')[1] and 'tdPetCloseManager(lane)' in function_body(view, 'tdPetHandleSelectionIdentity')[1], 'Selection bridge must call real close transaction')
    require('if pet.paused' in function_body(view, 'tdPetSkillRestriction')[1], 'Paused skills require an explicit reason')
    require('tdPetCancelRelease(lane)' in function_body(view, 'tdPetCloseManager')[1], 'Leaving must invalidate release')
    require('tdPetResolveReroll' not in function_body(view, 'tdPetCloseManager')[1], 'Leaving silently resolves proposal')
    begin, resolve, opened = (function_body(state, name)[1] for name in ('tdPetBeginReroll', 'tdPetResolveRerollVersion', 'tdPetOpenSlot'))
    require(begin.index('let candidate = pet.rollSkill') < begin.index('tdPetRerollStones[lane] -= 1'), 'Roll failure must not charge')
    require('pet.proposalVersion += 1' in begin and 'pet.proposalRevision = pet.revision' in begin, 'Proposal version/source revision missing')
    require('pet.proposalVersion != candidateVersion' in resolve and 'pet.revision != pet.proposalRevision' in resolve, 'Adoption version guard missing')
    require('readyAt =' not in begin + resolve + opened, 'Cultivation resets cooldown')
    require('proposalVersion' in session and 'listRevisions' in session and 'actualLevel' in session, 'Session snapshots/admission incomplete')
    require('setNormalAbilities("Avul")' in function_body(objects, 'displayUnit')[1], 'Displays must be runtime-mounted only')
    require('new ChannelAbilityPreset(tdPetListAbilityId(cell, 0, 0, 0), 2, true)' in objects and 'new AbilityDefinitionIllidanChannel(tdPetListAbilityId(cell, species, quality, ownedCount))' in objects and 'anchor.getOrderString()' in objects,
            'List must allocate only one shared order per physical cell')
    require('new AbilityDefinitionBladeMasterCriticalStrike(tdPetPreviewAbilityId' in objects and '..setLevels(4)' in objects, 'Preview must use four-quality passives')
    summary = function_body(view, 'tdPetPageSummary')[1]
    require('tdPetShowPageSummary' not in function_body(ui, 'showPage')[1],
            'Navigation must not emit automatic screen notes')
    require('session.mode != TD_PET_UI_DETAIL' in summary and '共鸣Lv' in summary,
            'Explicit status query must be limited to current pet details')
    require('tdPetSkillDescriptionById' not in summary and 'record ' not in summary,
            'Status query must not repeat skill tooltips or expose internal record IDs')
    require(not re.search(r'\[生效|生效技能\s*\d|生效数', ui + view + session), 'Unrequested effective-status label/count')
    hud = (ROOT / 'wurst/TDHud.wurst').read_text()
    before = subprocess.run(['git', 'show', BASELINE + ':wurst/TDHud.wurst'], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    require(hud.count('CreateMultiboard') == before.count('CreateMultiboard'), 'Manager replaces ranking board')
    require('setColumnCount(TD_DAMAGE_HUD_COLUMNS)' in hud and 'tdPetHudSummaries[playerId]' in hud and 'tdPetHudSummaries[lane]' in hud, 'Keep ranking columns and synchronous lane summaries')
    if verify_legacy_wild_scope:
        for path in ('wurst/pets/TDPetWild.wurst', 'wurst/pets/TDPetWildState.wurst'):
            before = subprocess.run(['git', 'show', BASELINE + ':' + path], cwd=ROOT, check=True, capture_output=True).stdout
            actual = (ROOT / path).read_bytes()
            if path.endswith('TDPetWild.wurst') and 'TD_PET_SPECIES_COUNT = 15' in source('TDPetData'):
                require(before.count(b'species > 3') == 1 and before.count(b'GetRandomInt(1, 3)') == 1, 'Wild species expansion baseline changed')
                before = before.replace(b'species > 3', b'species > TD_PET_SPECIES_COUNT').replace(b'GetRandomInt(1, 3)', b'GetRandomInt(1, TD_PET_SPECIES_COUNT)')
            require(actual == before, 'Wild encounter changes outside approved species-only scope: ' + path)
    verify_ui_workflow()
    print('PASS SOURCE WIRING: fresh caster authority, exact level/page whitelist, consume-before-transaction, dirty-only polling, synchronized mounts/local-only selection, proposal preservation, release cancellation, HUD board ownership; ' +
          ('exact historical wild bytes plus approved species-only expansion' if verify_legacy_wild_scope else 'wild scope must be proven by the separate exact Boss delta'))


def verify_assets():
    from BuildPetUiAssets import EXPECTED_NAMES, verify_manifest
    manifest = json.loads((ROOT / 'assets/source/pet-ui/manifest.json').read_text())
    verify_manifest(manifest, require_hashes=True)
    original = json.loads(subprocess.run(['git', 'show', ASSET_BASELINE + ':assets/source/pet-ui/manifest.json'], cwd=ROOT, check=True, capture_output=True, text=True).stdout)
    current = {asset['name']: asset for asset in manifest['assets']}
    require(set(current) == EXPECTED_NAMES, 'Exact seventy-eight source assets required')
    for asset in original['assets']:
        for key in ('source_svg', 'normal_blp', 'disabled_blp'):
            require(hashlib.sha256((ROOT / current[asset['name']][key]).read_bytes()).hexdigest() == asset['sha256'][key], 'Original pet artwork changed: ' + asset['name'])
    # Preserve all 28 predecessor artworks, not only the first 13 originals.
    before = json.loads(subprocess.check_output(['git', 'show', '28f16681bc07b58066f10d51e8aed7ba626fb768:assets/source/pet-ui/manifest.json'], cwd=ROOT))
    for asset in before['assets']:
        for key in ('source_svg', 'normal_blp', 'disabled_blp'):
            require(hashlib.sha256((ROOT / current[asset['name']][key]).read_bytes()).hexdigest() == asset['sha256'][key], 'Predecessor pet artwork changed: ' + asset['name'])
    print('PASS ASSET PRESERVATION: all 28 predecessor SVG/BTN/DIS inputs byte-locked; exact 48 count portraits + 2 readable choices')


def verify_ui_workflow():
    data, ui, session, objects, state = (source(n) for n in ('TDPetData', 'TDPetUI', 'TDPetUIState', 'TDPetObjectGen', 'TDPetState'))
    before = subprocess.check_output(['git', 'show', '28f16681bc07b58066f10d51e8aed7ba626fb768:wurst/pets/TDPetData.wurst'], cwd=ROOT).decode()
    require('limit > 256' in function_body(data, 'tdPetHexRawcode')[1] and 'limit > 4096' in function_body(data, 'tdPetHex3Rawcode')[1], 'Integer rawcodes must reject overflow')
    for helper in ('tdPetListAbilityId', 'tdPetManagerCommandId', 'tdPetPreviewArrowAbilityId'):
        body = function_body(data, helper)[1]
        require('SubString' not in body and '.fromRawCode' not in body, 'Startup helper performs runtime string work: ' + helper)
    setup = function_body(ui, 'tdPetSetupUI')[1]
    require(setup.index('if ready') < setup.index('ready = true') < setup.index('registerSpellEffectEvent'), 'Setup must guard repeated registration')
    require(setup.count('registerSpellEffectEvent(') == 2, 'Only farmer entrances may use per-ability registration')
    require('for action' not in setup and 'tdPetListAbilityId' not in setup and 'tdPetManagerCommandId' not in setup,
            'Startup traverses manager/portrait catalog')
    require(setup.count('managerCommandTrigger.registerAnyUnitEvent(EVENT_PLAYER_UNIT_SPELL_EFFECT)') == 1 and
            setup.count('managerCommandTrigger.addAction(function onManagerSpell)') == 1 and
            function_body(ui, 'onManagerSpell')[1].strip() == 'onCommand()',
            'One native command bridge must validate through onCommand')
    opened = function_body(session, 'open')[1]
    require('if abilityId == 0\n\t\t\tclose()\n\t\t\treturn false' in opened, 'Malformed occupied portrait must reject, never mount an empty fallback')
    require('current.skillCount == ownedCount' in function_body(session, 'matchesPet')[1] and 'current.skillCount == listOwnedCounts[cell]' in function_body(session, 'matchesListCell')[1], 'Count changes must stale both list and detail snapshots')
    for text in ('mount(0, tdPetPreviewAbilityId(0', 'mount(1, tdPetPreviewArrowAbilityId(0)', 'mount(2, tdPetPreviewArrowAbilityId(1)', 'mount(3, tdPetPreviewAbilityId(1'):
        require(text in opened, 'Preview old/arrow/arrow/new layout missing: ' + text)
    config = function_body(objects, 'listCommand')[1]
    for text in ('setLevels(2)', 'presetBaseOrderID(lvl -> order)', 'presetTargetType(lvl -> 0)', 'presetOptions(lvl -> 1)', 'presetDisableOtherAbilities(lvl -> false)', 'presetFollowThroughTime(lvl -> 0.0)', 'presetArtDuration(lvl -> 0.0)', 'setHeroAbility(false)', 'setItemAbility(false)', 'presetManaCost(lvl -> 0)', 'presetCooldown(lvl -> 0.0)', 'setArtCaster("")', 'setArtEffect("")', 'setArtSpecial("")', 'setArtTarget("")'):
        require(text in config, 'Incomplete shared list Channel configuration: ' + text)
    continued = function_body(state, 'tdPetContinueReroll')[1]
    for text in ('tdPetLaneCanManage(lane)', 'pet != expected', 'pet.released', 'pet.proposalSlot >= pet.skillCount', 'pet.proposalSlot >= 4', 'candidateVersion <= 0', 'pet.proposalVersion != candidateVersion', 'pet.proposalVersion >= 2147483647', 'pet.proposalRevision != sourceRevision', 'pet.revision != sourceRevision', 'tdPetRerollStones[lane] < 1', 'candidate < 0'):
        require(text in continued, 'Missing atomic continue guard: ' + text)
    require(continued.index('pet.rollSkill') < continued.index('pet.proposalVersion += 1') < continued.index('tdPetRerollStones[lane] -= 1'), 'Continue must validate/draw before one version and charge')
    require(continued.count('tdPetRerollStones[lane] -= 1') == 1 and continued.count('pet.proposalVersion += 1') == 1, 'Continue must charge/increment exactly once')
    require(not any(text in continued for text in ('setSkill(', 'tdPetBeginReroll(', 'proposalSlot = -1', 'readyAt =', 'skillCount =')), 'Continue clears candidate or mutates owned skills/cooldown')
    command = function_body(ui, 'onCommand')[1]
    require(command.index('session.admitCommand') < command.index('tdPetContinueReroll(lane, slot, session.pet, proposalVersion, proposalRevision)'), 'Continue must consume exact snapshot authority before mutation')
    fallback = function_body(ui, 'showDetailOrList')[1]
    require('current != null and current == expected' in fallback and 'TD_PET_UI_DETAIL' in fallback and 'TD_PET_UI_LIST' in fallback, 'Failure/cancel must revalidate record before detail')
    cancel = command.split('else if action == TD_PET_ACTION_CANCEL\n', 1)[1]
    require('tdPetCancelRelease(lane)\n\tshowDetailOrList(lane, page, slot, pet)' in cancel, 'Cancel must revoke ticket and return safely')
    release = function_body(ui, 'showReleaseConfirmation')[1]
    require('tdPetBeginRelease(lane, slot)' in release and 'showDetailOrList(lane, slot div 10, slot, expected)' in release, 'Release entrance must reuse the existing guarded ticket and safe return')
    require('TD_PET_UI_RELEASE' not in function_body(ui, 'refreshStale')[1], 'Stale release must not route back into cultivation')
    require('label = "保留原技能"' in objects and 'label = "换成新技能"' in objects, 'Choice tooltips must name the actual operation')
    print('PASS UI WORKFLOW: two farmer registrations + one constant manager bridge/guard; integer startup; count snapshots; complete shared Channels; eight-cell preview; atomic continue; safe release return')


def main():
    verify_scalar_contracts()
    verify_wiring()
    verify_ui_workflow()
    verify_assets()
    print('NOT RUN: Wurst syntax/typecheck/tests; full build; W3A/W3U/MPQ artifact gates; in-game selection/rendering/network timing/performance; final Astra implementation review')


if __name__ == '__main__':
    main()
