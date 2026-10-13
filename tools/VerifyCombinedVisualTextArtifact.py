"""Finite source-derived field contract for this visual/text/ground-sort batch.

No broad text-field exemption. All other object fields stay byte-identical to
the real published parent. Source strings are interpreted only as pure values;
this is separate from the actual Wurst checks/build and engine verification.
"""
import re
from pathlib import Path
from VerifyActiveCooldownContract import SourceScalarEvaluator, Expression, read_sources, rawstring
from VerifySemanticIconArtifact import parse_objects
from VerifyEquipmentAuraSpecialArtifact import field, named, verify as verify_aura
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTowerPlacementArtifact import unit_objects
from VerifyPlayerTooltipArtifact import validate as verify_player
from VerifyAuraTargetArtifact import verify_hidden_carriers


def require(value, message):
    if not value:
        raise AssertionError(message)


class SourceTextEvaluator(SourceScalarEvaluator):
    """Reuse the finite scalar parser/control flow, adding string concatenation."""
    def __init__(self, sources, root=None):
        super().__init__(sources)
        self.item_entries = {}
        if 'items/TDItemData.wurst' in sources:
            from ReadEquipmentCatalog import catalog, ROOT
            self.item_entries = {int.from_bytes(x.rawcode.encode(), 'big'): x for x in catalog(ROOT if root is None else root)}
            params, body = self.functions['tdItemTooltip', 1]
            # The unchanged catalog initializer has no text effect. Its fields
            # below come from the authoritative single catalog, not a fixture.
            self.functions['tdItemTooltip', 1] = params, body.replace('tdEnsureItemCatalog()\n', '')

    def call(self, name, values, fields=None):
        accessors = {'tdItemQuality': ('quality', None), 'tdItemAuraKind': ('aura', 'TD_ITEM_AURA_'),
                     'tdItemAuraValue': ('aura_value', None), 'tdItemAuraRadius': ('aura_radius', None),
                     'tdItemSpecialization': ('specialization', 'TD_ITEM_SPECIAL_'),
                     'tdItemPrimaryEffectKind': ('primary', 'TD_ITEM_EFFECT_'),
                     'tdItemPrimaryEffectValue': ('primary_value', None),
                     'tdItemSecondaryEffectKind': ('secondary', 'TD_ITEM_EFFECT_'),
                     'tdItemSecondaryEffectValue': ('secondary_value', None)}
        if name in accessors:
            require(len(values) == 1 and values[0] in self.item_entries, 'Unknown source catalog text identity')
            attr, prefix = accessors[name]; value = getattr(self.item_entries[values[0]], attr)
            return self.constant(prefix + value) if prefix else value
        if name == 'tdTooltipNumber':
            return format(values[0], '.6f').rstrip('0').rstrip('.')
        if name == 'tdPreciseBonusPercentString':
            scaled = int(values[0] * 100000 + .5)
            return str(scaled // 1000) + ('.' + str(scaled % 1000).zfill(3).rstrip('0') if scaled % 1000 else '') + '%'
        return super().call(name, values, fields)

    def expression(self, text, scope):
        parser = Expression(text); tree = parser.parse()
        require(not parser.peek(), 'Unclassified source text expression: ' + text)
        def read(node):
            kind = node[0]
            if kind == 'value': return node[1]
            if kind == 'name': return scope[node[1]] if node[1] in scope else self.constant(node[1])
            if kind == 'attribute':
                if node[1] == ('name', 'Orders'):
                    require(node[2] in self.orders, 'Unknown locked order'); return self.orders[node[2]]
                return getattr(read(node[1]), node[2])
            if kind == 'unary':
                v = read(node[2]); return not v if node[1] == 'not' else -v if node[1] == '-' else v
            if kind == 'ternary': return read(node[2] if read(node[1]) else node[3])
            if kind == 'binary':
                op, a = node[1], read(node[2])
                if op == 'and': return bool(a) and bool(read(node[3]))
                if op == 'or': return bool(a) or bool(read(node[3]))
                b = read(node[3])
                if op == '+' and (isinstance(a, str) or isinstance(b, str)): return str(a) + str(b)
                return {'+': lambda: a+b, '-': lambda: a-b, '*': lambda: a*b, '/': lambda: a/b,
                        'div': lambda: int(a/b), 'mod': lambda: a%b, '==': lambda: a==b,
                        '!=': lambda: a!=b, '<': lambda: a<b, '>': lambda: a>b,
                        '<=': lambda: a<=b, '>=': lambda: a>=b}[op]()
            if kind == 'call':
                target, args = node[1], [read(n) for n in node[2]]
                if target[0] == 'attribute':
                    v, method = read(target[1]), target[2]
                    require(not args and method in ('toInt', 'toString', 'toRawCode'), 'Unclassified source string method')
                    return int(v) if method == 'toInt' else rawstring(v) if method == 'toRawCode' else str(v)
                require(target[0] == 'name', 'Unclassified source call')
                name = target[1]
                if name in self.tuples: return self.tuples[name](*args)
                if name in ('RMinBJ', 'IMinBJ', 'min'): return min(args)
                if name in ('RMaxBJ', 'IMaxBJ', 'max'): return max(args)
                if name == 'R2I': return int(args[0])
                if name == 'I2R': return float(args[0])
                return self.call(name, args)
            raise AssertionError('Unclassified source text node')
        return read(tree)


def verify_tables(current, baseline, root):
    root = Path(root)
    source = read_sources(root); evaluator = SourceTextEvaluator(source, root)
    tables = {'war3map.w3u': False, 'war3map.w3a': True, 'war3map.w3t': False, 'war3map.w3h': False}
    now = {p: parse_objects(current.extract(p), extended) for p, extended in tables.items()}
    old = {p: parse_objects(baseline.extract(p), extended) for p, extended in tables.items()}
    allowed = {p: {} for p in tables}
    def allow(path, code, key, expected=None):
        require(code in now[path] and code in old[path], 'Missing approved object ' + code)
        allowed[path].setdefault(code, set()).add(key)
        if expected is not None:
            require(now[path][code].fields[key].value == expected, 'Source text/value mismatch: ' + code + str(key))
    tower_source = source['towers/TDTowerCatalogData.wurst']
    tower_ids = set(re.findall(r"public constant int TD_(?:ARCHER|ORC|FOOT|DRYAD|GHOUL)_LEVEL_[A-Z0-9_]+_ID = '(.{4})'", tower_source))
    require(len(tower_ids) == 35, 'Unexpected tower text object set')
    for family in range(1, 6):
        for level in range(1, 7):
            for branch in range(1, 3 if level == 6 else 2):
                code = rawstring(evaluator.call('tdTowerUnitIdForLevelBranch', [family, level, branch]))
                require(code in tower_ids, 'Source tower ID escaped finite set')
                allow('war3map.w3u', code, ('ides', 0, 0), evaluator.call('tdTowerTalentSummaryForBranch', [family, level, branch]))
                allow('war3map.w3u', code, ('utub', 0, 0), evaluator.call('tdTowerTooltipExtendedForBranch', [family, level, branch]))
    for key in ('umdl', 'usca'): allow('war3map.w3u', 'uB16', (key, 0, 0))
    from ReadEquipmentCatalog import catalog
    for entry in catalog(root):
        for key in ('utub', 'ides'): allow('war3map.w3t', entry.rawcode, (key, 0, 0), evaluator.call('tdItemTooltip', [int.from_bytes(entry.rawcode.encode(), 'big')]))
    for skill in range(16):
        for quality in range(1, 5):
            text = evaluator.call('tdPetSkillDescriptionById', [skill, quality])
            variant = skill * 4 + quality - 1
            for position in range(2): allow('war3map.w3a', f'Ps{position*16+skill:02X}', ('aub1', quality, 0), text)
            for slot in range(4):
                for locked in (0, 64):
                    code = f's{slot}{variant+locked:02X}'
                    # Locked copies carry the same description plus its existing warning.
                    actual = field(now['war3map.w3a'][code], 'aub1', 1)
                    expected = ('技能已获得；共鸣锁定，完成本路第' + ('4' if slot == 2 else '8') + '波解锁。|n' if locked else '') + text
                    allow('war3map.w3a', code, ('aub1', 1, 0), expected)
    for code in ('A104', 'A113'):
        for level in range(1, 62): allow('war3map.w3a', code, ('aub1', level, 0))
    for code in ('A119', 'Geqb', 'Gupg'): allow('war3map.w3a', code, ('aub1', 1, 0))
    for code in ('AM13', 'AM14', 'AM15', 'AM16'):
        allow('war3map.w3a', code, ('abpx', 0, 0), 0); allow('war3map.w3a', code, ('abpy', 0, 0), -11)
    buff_calls = re.findall(r'tdAuraName\((\d+)\) \+ " (\d+)"', source['auras/TDAuraObjectIds.wurst'])
    require(len(buff_calls) == 38, 'Unexpected aura Buff source set')
    expected_buffs = [(evaluator.call('tdAuraName', [int(i)]) + ' ' + rank,
                       evaluator.call('tdAuraStateTooltip', [int(i), int(rank)])) for i, rank in buff_calls]
    expected_buffs += [(evaluator.call('tdWarStageName', [n]), evaluator.call('tdWarStageTooltip', [n])) for n in range(1, 5)]
    expected_buffs += [(evaluator.call('tdPoisonStageName', [n]), evaluator.call('tdPoisonStageTooltip', [n])) for n in range(1, 3)]
    for name, text in expected_buffs:
        matches = [code for code, obj in now['war3map.w3h'].items() if field(obj, 'fnam') == name]
        require(len(matches) == 1, 'Missing source Buff ' + name); code = matches[0]
        allow('war3map.w3h', code, ('fube', 0, 0), text)
    differences = []
    for path in tables:
        require(list(now[path]) == list(old[path]), 'Object set/order changed: ' + path)
        for code, obj in now[path].items():
            before = old[path][code]
            require(obj.identity == before.identity and obj.table == before.table, 'Object parent/identity changed: ' + code)
            for key in set(obj.fields) | set(before.fields):
                if obj.fields.get(key) != before.fields.get(key):
                    require(key in allowed[path].get(code, set()), 'Unapproved object field: ' + path + ':' + code + str(key))
                    differences.append([path, code, list(key)])
    verify_player(ability_objects(current.extract('war3map.w3a')), unit_objects(current.extract('war3map.w3u')),
                  unit_objects(current.extract('war3map.w3t')), source_root=root, shared_active_cooldown=True, current_pet_ui=True)
    verify_aura(now['war3map.w3a'], now['war3map.w3h']); verify_hidden_carriers(now['war3map.w3a'])
    return differences


def verify_ground_runtime(script):
    from VerifyPetUIArtifact import jass_function
    from VerifyEquipmentCombatReplay import EquipmentTrialRuntime
    def body(name):
        match = jass_function(script, name)
        require(match is not None, 'Missing compiled ground entry ' + name)
        return match.group(1)
    finish = body('tdFinishCraftSession')
    sequence = ['= TDCraftingRuntime_tdCraftCaptureLane', 'set TDCraftingRuntime_tdCraftSession = 0', 'set TDCraftingRuntime_tdCraftCaptureLane = -1',
                'call dispatch_TDCraftSession_destroyTDCraftSession', 'call tdItemOperationRelease', 'call tdSortGroundEquipmentAfterUpgrade']
    positions = [finish.find(part) for part in sequence]
    require(all(p >= 0 for p in positions) and positions == sorted(positions), 'Compiled ground finish lost lane/cleanup/release/sort order')
    require(finish.count('call tdSortGroundEquipmentAfterUpgrade') == 1 and not re.search(r'doAfter|doPeriodically|TriggerSleepAction', finish), 'Compiled sort handoff deferred/duplicated')
    require('call tdGroundStart(' in body('tdSortGroundEquipmentAfterUpgrade'), 'Compiled lane sorter not connected')
    for name in ('tdGroundCaptureItem', 'tdGroundProcessOne'):
        require('tdGroundItemAvailable(' in body(name), name + ': captured/dequeued item lacks shared admission guard')
    require('tdGroundSortItemEligible(' in body('tdGroundItemAvailable'), 'Compiled shared admission lacks lane/quality guard')
    require('tdSetupCraftingRuntime' not in body('tdSetupGroundItemRuntime'), 'Compiled ground setup imports crafting backwards')
    r = EquipmentTrialRuntime(script); r.initialize_match()
    count = 0
    for requested in range(-2, 5):
        for lane in range(-1, 5):
            for group in range(7):
                expected = 0 <= lane < 4 and ((requested == -1 and 1 <= group <= 5) or (0 <= requested < 4 and requested == lane and 1 <= group <= 4))
                require(r.invoke('tdGroundSortItemEligible', requested, lane, group) == expected, 'Compiled ground lane/quality matrix mismatch')
                count += 1
    return count
