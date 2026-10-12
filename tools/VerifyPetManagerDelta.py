#!/usr/bin/env python3
"""Actual manager delta and inherited-code evidence against immutable formal C.

This gate proves all unchanged functions individually, using unchanged source
line provenance, named type allocators and typed local-temp bijections. Feature
functions have separate executable Wurst/manager object gates; this file never
calls their entire bodies an inheritance proof. Historical feature-only closed
comparisons continue using their own frozen artifacts.
"""
import argparse
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import subprocess
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyDamageRankingJass import functions
from VerifyBuilderControlDelta import allocations, ASSIGN, TYPE_TEST
from VerifySemanticIconArtifact import parse_objects, load_objects, Reader
from VerifyGlobalRankingsArtifact import members, normalize_info, OBJECTS
from VerifyPetUIArtifact import verify_global_rawcode_uniqueness, verify_manager_objects
from VerifyGroundItemArtifact import verify_global_channel_orders

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = 'b7e3d051e98c2b18caafed4ab6e036700a6ee64c'
BASE_MAP_SHA256 = '55e8decccc5fada5b3dd21c854ad44a2203c73b64e1fcc1d10bd380bd48daadf'
SOURCE_CHANGES = {'wurst/TDHud.wurst'} | {f'wurst/pets/{p}.wurst' for p in
    ('TDPetData', 'TDPetRules', 'TDPetState', 'TDPetObjectGen', 'TDPetRuntime',
     'TDPetUIData', 'TDPetUIState', 'TDPetUI', 'TDPetUIView')}
FEATURE_FUNCTIONS = set('''tdRefreshStatusBoard tdPetDisplayUnitId tdPetSlotAbilityId
 tdPetRefreshDisplay call_doPeriodically_TDPetUI tdPetUICommandId tdPetSetupUI
 init_TDPetUI TDPet_summary dispatch_TDPet_TDPet_summary tdPetShowCollection
 navigate showCultivation onCommand bridge_onCommand onDeploy showReleaseConfirmation
 TDPet_rollSkill tdPetBeginReroll tdPetOpenSlot TDPet_init init_TDPetData
 init_TDPetUIState'''.split())
# Fixed compiler-visible function additions/retirements for this approved UI
# implementation; body semantics remain separate from the inheritance proof.
NEW_FUNCTIONS = set("""TDPetUISession_abilities_get TDPetUISession_abilities_set TDPetUISession_actions_get TDPetUISession_actions_set TDPetUISession_admitCommand TDPetUISession_close TDPetUISession_commandAction TDPetUISession_consumeCommand TDPetUISession_init TDPetUISession_levels_get TDPetUISession_levels_set TDPetUISession_listGenerations_get TDPetUISession_listGenerations_set TDPetUISession_listPets_get TDPetUISession_listPets_set TDPetUISession_listResonances_get TDPetUISession_listResonances_set TDPetUISession_listRevisions_get TDPetUISession_listRevisions_set TDPetUISession_matchesListCell TDPetUISession_matchesPet TDPetUISession_mount TDPetUISession_onDestroy TDPetUISession_open TDPetUISession_selectionCloses TDPetUISession_snapshotCurrent TDPet_quality alloc_CallbackSingle_doAfter_TDPetUIView alloc_TDPetUISession bridge_init_TDPetUIView bridge_onCommand_1 bridge_onCommand_2 bridge_onDeselected bridge_onSelected call_doAfter_TDPetUIView construct_TDPetUISession dealloc_TDPetUISession destroyTDPetUISession dispatch_TDPetUISession_TDPetUISession_admitCommand dispatch_TDPetUISession_TDPetUISession_close dispatch_TDPetUISession_TDPetUISession_commandAction dispatch_TDPetUISession_TDPetUISession_consumeCommand dispatch_TDPetUISession_TDPetUISession_matchesListCell dispatch_TDPetUISession_TDPetUISession_matchesPet dispatch_TDPetUISession_TDPetUISession_mount dispatch_TDPetUISession_TDPetUISession_open dispatch_TDPetUISession_TDPetUISession_selectionCloses dispatch_TDPetUISession_TDPetUISession_snapshotCurrent dispatch_TDPetUISession_destroyTDPetUISession dispatch_TDPet_TDPet_quality init_TDPetUIView new_TDPetUISession onDeselected onSelected refreshStale retire showPage tdPetActionCell tdPetCloseManager tdPetCollectionNumber tdPetHandleSelectionIdentity tdPetHexRawcode tdPetIsDisplayType tdPetListAbilityId tdPetListUnitId tdPetManagerCommandId tdPetNextOccupied tdPetOwnedQuality tdPetPageSlot tdPetPageSummary tdPetPreviewAbilityId tdPetReleaseNonce tdPetRenderPage tdPetResolveRerollVersion tdPetSelectFarmer tdPetShowPageSummary tdPetSkillRestriction tdPetStepSlot""".split())
REMOVED_FUNCTIONS = set("""TDPetDialogSession_close TDPetDialogSession_consumeButton TDPetDialogSession_init TDPetDialogSession_matchesPet TDPetDialogSession_open addButton alloc_TDPetDialogSession bridge_init_TDPetUI bridge_onDialog clearButtons clearDialog construct_TDPetDialogSession details dialog_addButton dialog_clear dispatch_TDPetDialogSession_TDPetDialogSession_close dispatch_TDPetDialogSession_TDPetDialogSession_consumeButton dispatch_TDPetDialogSession_TDPetDialogSession_matchesPet dispatch_TDPetDialogSession_TDPetDialogSession_open new_TDPetDialogSession onDialog selectDisplay showList tdPetDeployedCount tdPetDialogActionAllowed tdPetDialogHotkey tdPetResolveReroll""".split())
DIAGNOSTIC = re.compile(r'"((?:when calling [^"\n]+ in |via function reference |when (?:reading|writing) array [^"\n]+ in )([A-Za-z_]\w*), line )(\d+)"')
TEMP = re.compile(r'^\s*local (\w+) (temp\d+(?:_\w+)?)\b', re.M)
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*')


def git_blob(path):
    return subprocess.check_output(['git', 'show', BASE_COMMIT + ':' + path], cwd=ROOT)


def baseline_map():
    data = git_blob('ExampleMap.w3x')
    require(hashlib.sha256(data).hexdigest() == BASE_MAP_SHA256, 'Immutable formal C map differs')
    return Mpq(data)


def source_maps():
    current, before, mappings = {}, {}, {}
    old_paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE_COMMIT, '--', 'wurst'], cwd=ROOT).decode().splitlines()
    for path in old_paths:
        if not path.endswith('.wurst'):
            continue
        old = git_blob(path)
        now = (ROOT / path).read_bytes()
        if path not in SOURCE_CHANGES:
            require(now == old, 'Unrelated production source changed: ' + path)
        package = re.search(r'^package (\w+)', old.decode())[1]
        before[package] = old.decode(); current[package] = now.decode()
        lines, newer = old.decode().splitlines(), now.decode().splitlines()
        mapping = {}
        for block in SequenceMatcher(None, lines, newer, autojunk=False).get_matching_blocks():
            for offset in range(block.size):
                mapping[block.a + offset + 1] = block.b + offset + 1
        mappings[package] = mapping
    new_paths = {str(p.relative_to(ROOT)) for p in (ROOT / 'wurst').rglob('*.wurst') if '_tests' not in p.parts}
    require(new_paths - set(old_paths) == {'wurst/pets/TDPetUIView.wurst'}, 'Unexpected new production package')
    return mappings


def normalize_diagnostics(now, old, mappings):
    grouped, previous = {}, {}
    for m in DIAGNOSTIC.finditer(now): grouped.setdefault(m[1], []).append(m)
    for m in DIAGNOSTIC.finditer(old): previous.setdefault(m[1], []).append(m)
    require(set(grouped) == set(previous), 'Diagnostic prefix/site set changed')
    replacements, evidence = [], []
    for prefix, sites in previous.items():
        actual = grouped[prefix]
        require(len(actual) == len(sites), 'Diagnostic site count changed')
        for site, before in zip(actual, sites):
            package, line = before[2], int(before[3])
            if package in mappings:
                require(line in mappings[package], 'Diagnostic source line is not unchanged: ' + package + '/' + str(line))
                expected = mappings[package][line]
            else:
                # Locked stdlib/native packages must retain the exact old line.
                expected = line
            require(int(site[3]) == expected, 'Diagnostic relocation lacks exact source-line provenance')
            replacements.append((site.start(3), site.end(3), str(line)))
            if expected != line: evidence.append((package, line, expected))
    for start, end, value in reversed(sorted(replacements)):
        now = now[:start] + value + now[end:]
    return now, evidence


def type_bijection(script, old_script):
    now, old = allocations(script), allocations(old_script)
    require(set(now) - set(old) == {'alloc_TDPetUISession', 'alloc_CallbackSingle_doAfter_TDPetUIView'}, 'Unexpected new named allocator')
    require(set(old) - set(now) == {'alloc_TDPetDialogSession'}, 'Unexpected retired named allocator')
    mapping = {}
    for name, (array, old_id) in old.items():
        if name not in now: continue
        new_array, new_id = now[name]
        require(new_array == array, 'Allocator type owner changed: ' + name)
        mapping[old_id] = new_id
    require(len(set(mapping.values())) == len(mapping), 'Named allocator mapping is not one-to-one')
    return mapping, now, old


def normalize_types(now, old, mapping):
    evidence = []
    for pattern, group in ((ASSIGN, 3), (TYPE_TEST, 2)):
        sites, previous = list(pattern.finditer(now)), list(pattern.finditer(old))
        require(len(sites) == len(previous), 'Type assignment/comparison count changed')
        replacements = []
        for site, before in zip(sites, previous):
            require(site[group - 1] == before[group - 1], 'Type array/operator/reference changed')
            old_id = int(before[group]); expected = mapping.get(old_id, old_id)
            require(int(site[group]) == expected, 'Type number is not its named allocator or unchanged boundary')
            replacements.append((site.start(group), site.end(group), before[group]))
            if expected != old_id: evidence.append((before[group - 1], old_id, expected))
        for start, end, value in reversed(replacements): now = now[:start] + value + now[end:]
    return now, evidence


def normalize_temps(now, old):
    actual, previous = list(TEMP.finditer(now)), list(TEMP.finditer(old))
    require(len(actual) == len(previous), 'Local compiler-temp declaration count changed')
    rename = {}
    for site, before in zip(actual, previous):
        require(site[1] == before[1], 'Local compiler-temp type changed')
        require(site[2] not in rename, 'Duplicate local compiler-temp')
        rename[site[2]] = before[2]
    require(len(set(rename.values())) == len(rename), 'Local compiler-temp mapping is not bijective')
    # All identifier uses are replaced through the same proved typed declaration;
    # quoted strings, user locals and numbers are never changed.
    return TOKEN.sub(lambda m: m[0] if m[0].startswith('"') else rename.get(m[0], m[0]), now), {k:v for k,v in rename.items() if k != v}


def dispatch_calls(body, type_id, this=1):
    """Fail-closed execution of the generated conditional dispatch only."""
    stack, active, calls = [], True, []
    for raw in body.splitlines()[1:-1]:
        line = raw.strip()
        if line.startswith('if ') or line.startswith('elseif '):
            expr = line.split(' ', 1)[1][:-5]
            match = re.fullmatch(r'(CallbackSingle_typeId\[this_1\]|this_1) (==|<=) (\d+)', expr)
            require(match is not None, 'Unexpected dispatch predicate')
            value = type_id if match[1].startswith('CallbackSingle') else this
            condition = value == int(match[3]) if match[2] == '==' else value <= int(match[3])
            if line.startswith('if '):
                stack.append([active, condition]); active = active and condition
            else:
                require(bool(stack), 'Dispatch elseif without if')
                parent, taken = stack[-1]; active = parent and not taken and condition
                stack[-1][1] = taken or condition
        elif line == 'else':
            require(bool(stack), 'Dispatch else without if')
            parent, taken = stack[-1]; active = parent and not taken; stack[-1][1] = True
        elif line == 'endif':
            require(bool(stack), 'Dispatch endif without if'); active = stack.pop()[0]
        elif line.startswith('call '):
            require(re.fullmatch(r'call (?:call_\w+\(this_1(?:, "[^"\n]*")?\)|error\("[^"\n]*", "[^"\n]*"\))', line) is not None, 'Unexpected dispatch call/arguments')
            if active: calls.append(line)
        else:
            require(line in ('set wurst_stack[wurst_stack_depth] = w__wurst_stackPos',
                             'set wurst_stack_depth = wurst_stack_depth + 1',
                             'set wurst_stack_depth = wurst_stack_depth - 1'), 'Unexpected dispatch side effect')
    require(not stack, 'Unclosed dispatch branch')
    return calls


def prove_callback_dispatch(now, old, new_allocators, old_allocators):
    for name, (array, old_id) in old_allocators.items():
        if array != 'CallbackSingle_typeId': continue
        new_id = new_allocators[name][1]
        require(dispatch_calls(now, new_id) == dispatch_calls(old, old_id), 'Existing callback target/diagnostic changed: ' + name)
    require(dispatch_calls(now, new_allocators['alloc_CallbackSingle_doAfter_TDPetUIView'][1]) == ['call call_doAfter_TDPetUIView(this_1)'], 'Retirement callback dispatch is not exact')
    require(dispatch_calls(now, 0, 0)[:1] == dispatch_calls(old, 0, 0)[:1] and dispatch_calls(now, 0, 1)[:1] == dispatch_calls(old, 0, 1)[:1], 'Null/invalid dispatch diagnostics changed')


def expected_initialization(name, previous):
    def once(text, old, new):
        require(text.count(old) == 1, 'Initialization anchor must be unique')
        return text.replace(old, new, 1)
    if name == 'main':
        old = '\tcall TriggerAddCondition(initTrig, Condition(ref_function_bridge_init_TDPetUI))\n'
        new = ('\tcall TriggerAddCondition(initTrig, Condition(ref_function_bridge_init_TDPetUIView))\n'
               '\tif  not TriggerEvaluate(initTrig) then\n'
               '\t\tcall error("Could not initialize package TDPetUIView.", "when calling error in TDPetUIView, line 1")\n'
               '\tendif\n\tcall TriggerClearConditions(initTrig)\n'
               '\tcall TriggerAddCondition(initTrig, Condition(ref_function_init_TDPetUI))\n')
        return once(previous, old, new)
    if name == 'initGlobals':
        text = previous.replace('TDPetDialogSession_firstFree', 'TDPetUISession_firstFree').replace('TDPetDialogSession_maxIndex', 'TDPetUISession_maxIndex')
        text = once(text, '\tset ref_function_bridge_onDialog = function bridge_onDialog\n', '')
        anchor = '\tset ref_function_bridge_onCommand = function bridge_onCommand\n'
        added = ''.join('\tset ref_function_' + n + ' = function ' + n + '\n' for n in
                        ('bridge_onCommand_1','bridge_onCommand_2','bridge_onSelected','bridge_onDeselected'))
        text = once(text, anchor, anchor + added)
        return once(text, '\tset ref_function_bridge_init_TDPetUI = function bridge_init_TDPetUI\n',
                    '\tset ref_function_bridge_init_TDPetUIView = function bridge_init_TDPetUIView\n\tset ref_function_init_TDPetUI = function init_TDPetUI\n')
    return None


def prove_global_declarations(script, old_script):
    def globals_of(text):
        hit = re.search(r'^globals\n(.*?)^endglobals', text, re.M|re.S)
        require(hit is not None, 'Missing globals')
        lines = [line for line in hit[1].splitlines() if line.strip() and not line.startswith('//')]
        names = [re.fullmatch(r'\w+ (?:array )?(\w+)(?:=[^\n]+)?', line) for line in lines]
        require(all(names) and len({m[1] for m in names}) == len(names), 'Duplicate/malformed global declaration')
        return {m[1]:line for m,line in zip(names,lines)}
    comments = lambda text: [line for line in re.search(r'^globals\n(.*?)^endglobals', text, re.M|re.S)[1].splitlines() if line.startswith('//')]
    new_comments = ['// playerunitevent EVENT_PLAYER_UNIT_DESELECTED=ConvertPlayerUnitEvent(25)',
                    '// playerunitevent EVENT_PLAYER_UNIT_SELECTED=ConvertPlayerUnitEvent(24)']
    require(comments(script) == comments(old_script), 'Inherited native declaration comments changed')
    require(all(comments(script).count(line)==1 for line in new_comments), 'Selection native declaration missing/duplicate')
    now, old = globals_of(script), globals_of(old_script)
    exact = {'TDHud_tdPetHudSummaries':'string array TDHud_tdPetHudSummaries',
             'TDPetData_TD_PET_SKILL_COUNT':'integer TDPetData_TD_PET_SKILL_COUNT=0',
             'TDPet_proposalOldQuality':'integer array TDPet_proposalOldQuality',
             'TDPet_proposalOldSkill':'integer array TDPet_proposalOldSkill',
             'TDPet_proposalRevision':'integer array TDPet_proposalRevision',
             'TDPet_proposalVersion':'integer array TDPet_proposalVersion', 'old':'unit array old'}
    refs = {'ref_function_bridge_onDialog','ref_function_bridge_init_TDPetUI','ref_function_bridge_init_TDPetUIView',
            'ref_function_init_TDPetUI','ref_function_bridge_onCommand_1','ref_function_bridge_onCommand_2',
            'ref_function_bridge_onSelected','ref_function_bridge_onDeselected'}
    def feature(name):
        return name.startswith(('TDPetUI_', 'TDPetUIState_', 'TDPetUIView_', 'TDPetUISession_', 'TDPetDialogSession_')) or name in refs
    for name, line in old.items():
        if not feature(name): require(now.get(name)==line, 'Unrelated global declaration changed: ' + name)
    for name in set(now)-set(old):
        require(feature(name) or now[name]==exact.get(name), 'Unexpected new global declaration: ' + name)
    for name,line in exact.items(): require(now.get(name)==line, 'Required manager global declaration missing/changed: ' + name)
    return len([name for name in old if not feature(name)])


def prove_jass(script, old_script, mappings):
    now, old = functions(script), functions(old_script)
    require(set(now) == (set(old) - REMOVED_FUNCTIONS) | NEW_FUNCTIONS, 'Manager exact function addition/removal set changed')
    mapping, new_allocators, old_allocators = type_bijection(script, old_script)
    globals_proved = prove_global_declarations(script, old_script)
    diagnostics, types, temps, protected = [], [], {}, []
    for name, previous in old.items():
        if name not in now:
            require(name in REMOVED_FUNCTIONS, 'Unrelated legacy function removed: ' + name)
            continue
        if name in FEATURE_FUNCTIONS: continue
        initialization = expected_initialization(name, previous[0])
        if initialization is not None:
            require(now[name][0] == initialization, 'Initialization changed outside exact manager glue: ' + name)
            protected.append(name)
            continue
        if name == 'dispatch_CallbackSingle_CallbackSingle_call':
            prove_callback_dispatch(now[name][0], previous[0], new_allocators, old_allocators); continue
        if name == 'tdPetHandleCapture':
            replacements = {
                '收藏已满12只。按W选中收藏展示，再按C释放；上阵精灵须先召回。': '收藏已满20只。按W打开收藏，选择精灵后C养成、X释放；上阵精灵须先解绑。',
                '。按W选中收藏展示，E点塔上阵；选中展示后按C洗练/开栏/释放。': '。按W打开收藏，选择编号后E点塔绑定、C养成。'}
            expected = previous[0]
            for first,last in replacements.items():
                require(expected.count(first) == 1, 'Capture hint baseline changed'); expected = expected.replace(first,last)
            require(now[name][0] == expected, 'Capture behavior changed outside exact two hints')
            diag, type_sites, alpha = [], [], {}
        else:
            body, diag = normalize_diagnostics(now[name][0], previous[0], mappings)
            body, type_sites = normalize_types(body, previous[0], mapping)
            body, alpha = normalize_temps(body, previous[0])
            require(body == previous[0], 'Unrelated packaged function changed: ' + name)
        protected.append(name); diagnostics += diag; types += type_sites
        if alpha: temps[name] = alpha
    return {'protected_globals': globals_proved, 'protected_functions': len(protected), 'feature_functions_checked_separately': sorted(FEATURE_FUNCTIONS & set(now)), 'diagnostic_relocations': len(diagnostics), 'type_sites': len(types), 'named_allocator_changes': sum(new_allocators[n] != old_allocators[n] for n in old_allocators if n in new_allocators), 'temp_bijections': temps}


def verify_objects(current, before):
    require(set(current) == set(before), 'Object table set changed')
    added = {'units': {f'pd{i:02X}' for i in (0,4,5,6,7,8,9,10,11,12)},
             'abilities': {f'Pl{i:02X}' for i in range(130)} | {f'Pm{i:02X}' for i in range(13)} | {f'Ps{i:02X}' for i in range(32)}, 'items': set()}
    special = {('abilities','Pcol',('aub1',1,0)): '浏览已捕获精灵，查看技能并上阵、召回或培养。收藏上限20只，编号01–20固定，释放留空。|n已有第3/4技能栏在本路完成第4/8波后解锁。',
               ('abilities','Pdep',('anam',0,0)): '精灵绑定详情', ('abilities','Pdep',('atp1',1,0)): '精灵绑定详情 (E)',
               ('abilities','Pdep',('aub1',1,0)): '打开精灵详情，在详情中E选择本路已完工空塔绑定或换绑。|n每座塔可上阵1只精灵；换塔保留主动技能冷却。',
               ('abilities','Pdep',('Ncl2',1,2)): 0}
    for code,label,key in [('Pc00','精灵收藏','I'),('Pc05','解绑','Q'),('Pc07','刷新详情','W')]:
        special['abilities',code,('anam',0,0)] = label
        special['abilities',code,('atp1',1,0)] = label + ' (' + key + ')'
    changed, unchanged = [], 0
    for kind, previous in before.items():
        entries = current[kind]
        require(set(entries) == set(previous) | added[kind], 'Unexpected added/deleted objects: ' + kind)
        for code, old in previous.items():
            obj = entries[code]
            require((obj.table,obj.identity,list(obj.fields)) == (old.table,old.identity,list(old.fields)), 'Existing object identity/field set/order changed: ' + code)
            for key, item in obj.fields.items():
                prior = old.fields[key]
                if item == prior: unchanged += 1; continue
                allowed = kind == 'units' and code in ('pd01','pd02','pd03') and key[0] in ('unam','umdl','uico','ussi','uabi')
                if allowed:
                    # New shape separately proves exact species/quality/model,
                    # Avul-only mounting and zero native actions.
                    require(item.kind == prior.kind and item.raw[:8] == prior.raw[:8] and item.raw[-4:] == prior.raw[-4:], 'Display field encoding metadata drift')
                    changed.append((kind,code,key)); continue
                expected = special.get((kind,code,key))
                if kind == 'abilities' and re.fullmatch(r's[0-3][4-7][0-9A-F]',code) and key == ('aub1',1,0):
                    prefix = '技能已获得，尚未生效。'
                    require(prior.kind == 3 and prior.value.startswith(prefix), 'Locked tooltip predecessor changed')
                    expected = '技能已获得；共鸣锁定，' + prior.value[len(prefix):]
                require(expected is not None and item.value == expected, 'Unrelated or wrongly changed object field: ' + repr((kind,code,key)))
                header = 16 if kind == 'abilities' else 8
                require(item.kind == prior.kind and item.raw[:header] == prior.raw[:header] and item.raw[-4:] == prior.raw[-4:], 'Changed field encoding metadata drift')
                changed.append((kind,code,key))
    return {'added_abilities': len(added['abilities']), 'added_units': len(added['units']), 'changed_fields':len(changed),'unchanged_fields':unchanged}


def verify_archive(artifact, old):
    now, before = members(artifact), members(old)
    additions = {('war3mapImported\\BTN' + stem + '.blp').casefold() for stem in
                 [s + f'Q{q}' for s in ('TDPetFlamePhoenix','TDPetStormFaerieDragon','TDPetGhostWisp') for q in range(1,5)] + ['TDPetRelease','TDPetKeep','TDPetAdopt']}
    additions |= {p.replace('war3mapimported\\btn','replaceabletextures\\commandbuttonsdisabled\\disbtn') for p in additions}
    require(set(now) == set(before) | additions, 'Actual MPQ member additions/removals changed')
    for key,(path,data) in before.items():
        new_path,new_data = now[key]
        require(new_path == path, 'Existing MPQ path spelling changed')
        if path == 'war3map.w3i': require(normalize_info(data) == normalize_info(new_data),'Metadata changed outside two titles')
        elif path not in ('war3map.w3a','war3map.w3u','war3map.j','war3map.imp','(listfile)','(attributes)'):
            require(data == new_data, 'Unrelated MPQ resource changed: ' + path)
    # Strict IMP inventory retains old paths/flags and adds only 30 exact paths.
    def imports(data):
        r=Reader(data);require(r.integer()==1,'Unexpected import version'); result={}
        for _ in range(r.integer()):
            flag=r.take(1);path=r.string();require(path.casefold() not in result,'Duplicate import path');result[path.casefold()]=(path,flag)
        require(r.offset==len(data),'Import trailer');return result
    imp, prior = imports(artifact.extract('war3map.imp')), imports(old.extract('war3map.imp'))
    require(set(imp)==set(prior)|additions,'Import additions differ')
    for key,value in prior.items(): require(imp[key]==value,'Existing import path/flag changed')
    for key in additions: require(imp[key][1]==b'\r','New import flag differs')
    return {'old_members':len(before),'new_members':len(now),'new_assets':len(additions)}


def validate(artifact):
    old=baseline_map();mappings=source_maps()
    verify_global_rawcode_uniqueness(artifact)
    objects=load_objects(artifact);before=load_objects(old)
    verify_manager_objects(ability_objects(artifact.extract('war3map.w3a')), {n:{key[0]:f.value for key,f in o.fields.items()} for n,o in objects['units'].items()})
    report={'objects':verify_objects(objects,before),'archive':verify_archive(artifact,old),
            'jass':prove_jass(artifact.extract('war3map.j').decode(),old.extract('war3map.j').decode(),mappings),
            'global_channels':verify_global_channel_orders(ability_objects(artifact.extract('war3map.w3a')))}
    require(report['global_channels']<=335,'Order pool exhausted')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('map',type=Path);args=parser.parse_args()
    print('PASS MANAGER INHERITANCE:',json.dumps(validate(Mpq(args.map.read_bytes())),ensure_ascii=False,sort_keys=True))
