"""Execute the packaged ground-upgrade JASS with bounded native stubs.

The compiler's real guards, snapshot capture, batch processing, item catalog,
and pile-position helpers execute here. Only Warcraft natives, standard-library
LinkedList operations and item/index bridges are stubbed. This proves called
coordinates and controlled interleavings, not native item relocation, terrain,
timers, UI, multiplayer synchronization or gameplay.
"""
import ast
from collections import defaultdict
import itertools
from pathlib import Path
import re
import sys

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyTowerUpgradeArtifact import JassScalarEvaluator, rawcode, function_body

PREFIX = 'TDGroundItemRuntime_'


def expected_pile_position(lane, quality, index=0):
    """Independent published four-lane coordinate oracle, not a JASS helper."""
    center_x, white_y, direction = {0: (-768.0, 2560.0, -1), 1: (1024.0, 2560.0, -1),
                                    2: (1024.0, -2816.0, 1), 3: (-1024.0, -2816.0, 1)}[lane]
    cell = index % 15
    return (center_x + (cell % 5 - 2) * 32.0,
            white_y + direction * (quality - 1) * 256.0 + (cell // 5 - 1) * 32.0)


class _Return(Exception):
    def __init__(self, value):
        self.value = value


def packaged_loop_bounds(name, lines):
    """Validate block structure without evaluating inactive expressions.

    Checking the complete body also keeps early returns and exitwhen jumps from
    concealing malformed or unclosed inactive blocks.
    """
    blocks, ends = [], {}
    for index, row in enumerate(lines):
        line = row.split('//', 1)[0].strip()
        if line.startswith('if ') and line.endswith(' then'):
            blocks.append(['if', index, False])
        elif (line.startswith('elseif ') and line.endswith(' then')) or line == 'else':
            require(blocks and blocks[-1][0] == 'if' and not blocks[-1][2],
                    f'{name}: illegal packaged control flow at {line}')
            if line == 'else':
                blocks[-1][2] = True
        elif line == 'endif':
            require(blocks and blocks[-1][0] == 'if',
                    f'{name}: illegal packaged control flow at endif')
            blocks.pop()
        elif line == 'loop':
            blocks.append(['loop', index, False])
        elif line == 'endloop':
            require(blocks and blocks[-1][0] == 'loop',
                    f'{name}: illegal packaged control flow at endloop')
            ends[blocks.pop()[1]] = index
        elif line.startswith('exitwhen '):
            require(any(block[0] == 'loop' for block in blocks),
                    f'{name}: illegal packaged control flow at exitwhen')
    require(not blocks, f'{name}: unclosed packaged control flow')
    return ends


class GroundJassRuntime(JassScalarEvaluator):
    """Minimal extension of the existing fail-closed scalar JASS evaluator."""
    def __init__(self, script):
        super().__init__(script)
        self.globals = {}
        declarations = script.split('globals\n', 1)[1].split('endglobals', 1)[0]
        for kind, array, name in re.findall(r'^(\w+) (array )?(\w+)', declarations, re.M):
            default = False if kind == 'boolean' else 0.0 if kind == 'real' else 0 if kind == 'integer' else None
            self.globals[name] = defaultdict(lambda value=default: value) if array else default
        self.globals.update({name: value for name, value in self.constants.items()
                             if re.fullmatch(r'\w+_[A-Z][A-Z0-9_]*', name)})
        self.items, self.queues = {}, {group: [] for group in range(1, 6)}
        self.globals[PREFIX + 'tdGroundQueues'] = defaultdict(int, {group: group for group in self.queues})
        self.globals[PREFIX + 'tdGroundCasterLane'] = -1
        self.globals['ref_function_bridge_tdGroundCaptureItem'] = 'tdGroundCaptureItem'
        self.enum_item, self.farmer, self.target = None, (-100, 0, rawcode('uF01')), (-768.0, 2560.0)
        self.products, self.removed, self.messages, self.random_calls, self.enqueued = [], [], [], [], []
        self.invoke('tdEnsureItemCatalog')

    def expression(self, text, scope):
        text = re.sub(r'\btrue\b', 'True', text)
        text = re.sub(r'\bfalse\b', 'False', text)
        text = re.sub(r'\bnull\b', 'None', text)
        variables = {**self.globals, **scope}
        runtime = self
        class Extensions(ast.NodeTransformer):
            def visit_Subscript(self, node):
                require(isinstance(node.value, ast.Name), 'Unsupported packaged array base')
                key = runtime.expression(ast.unparse(node.slice), scope)
                require(node.value.id in variables, 'Unknown packaged array')
                temporary = '_array_value_' + str(len(variables))
                variables[temporary] = variables[node.value.id][key]
                return ast.copy_location(ast.Name(id=temporary, ctx=ast.Load()), node)
            def visit_BinOp(self, node):
                node = self.generic_visit(node)
                if isinstance(node.op, ast.Div):
                    return ast.copy_location(ast.Call(func=ast.Name(id='_jass_div', ctx=ast.Load()),
                                                       args=[node.left, node.right], keywords=[]), node)
                return node
        node = Extensions().visit(ast.parse(text.strip(), mode='eval'))
        return super().expression(ast.unparse(node.body), variables)

    def assign(self, target, value, scope):
        if target.startswith('wurst_stack'):
            return  # Compiler diagnostics are outside the gameplay state.
        indexed = re.fullmatch(r'(\w+)\[(.*)\]', target)
        if indexed:
            name, index = indexed.groups()
            require(name in self.globals, 'Unknown packaged assignment array')
            self.globals[name][self.expression(index, scope)] = value
        elif target in scope:
            scope[target] = value
        else:
            require(target in self.globals, f'Unknown packaged assignment {target}')
            self.globals[target] = value

    def invoke(self, name, *arguments):
        signature = self.functions[name][0]
        if len(signature) == len(arguments) + 1 and signature[-1] == 'w__wurst_stackPos':
            arguments += ('offline ground validation',)
        return self.call(name, list(arguments))

    def call(self, name, args):
        native, result = self.native(name, args)
        if native:
            return result
        require(name in self.functions, f'Missing packaged ground function {name}')
        signature, lines = self.functions[name]
        require(len(args) == len(signature), f'{name}: packaged argument count changed')
        loop_ends = packaged_loop_bounds(name, lines)
        scope, branches, loops, active, index, steps = dict(zip(signature, args)), [], [], True, 0, 0
        try:
            while index < len(lines):
                steps += 1
                require(steps <= 10000, f'{name}: packaged loop did not terminate')
                line = lines[index].split('//', 1)[0].strip()
                if not line:
                    pass
                elif line.startswith('if ') and line.endswith(' then'):
                    selected = active and bool(self.expression(line[3:-5], scope))
                    branches.append([active, selected])
                    active = selected
                elif line.startswith('elseif ') and line.endswith(' then'):
                    parent, selected = branches[-1]
                    active = parent and not selected and bool(self.expression(line[7:-5], scope))
                    branches[-1][1] = selected or active
                elif line == 'else':
                    parent, selected = branches[-1]
                    active, branches[-1][1] = parent and not selected, True
                elif line == 'endif':
                    active = branches.pop()[0]
                elif line == 'loop':
                    loops.append((index, len(branches), active))
                elif line == 'endloop':
                    start, branch_depth, loop_active = loops.pop()
                    require(len(branches) == branch_depth,
                            f'{name}: illegal packaged control flow at endloop')
                    active = loop_active
                    if loop_active:
                        index = start
                        continue
                elif active and line.startswith('exitwhen '):
                    if self.expression(line[9:], scope):
                        start, branch_depth, loop_active = loops.pop()
                        del branches[branch_depth:]
                        active = loop_active
                        index = loop_ends[start]
                elif active and line.startswith('return'):
                    raise _Return(self.expression(line[7:], scope) if line != 'return' else None)
                elif active and line.startswith('local '):
                    declaration = re.fullmatch(r'local (\w+) (\w+)(?: = (.*))?', line)
                    require(declaration is not None, 'Unsupported packaged local')
                    kind, key, initializer = declaration.groups()
                    scope[key] = self.expression(initializer, scope) if initializer else (0 if kind in ('real', 'integer') else False if kind == 'boolean' else None)
                elif active and line.startswith('set '):
                    key, value = line[4:].split(' = ', 1)
                    if not key.startswith('wurst_stack'):
                        self.assign(key, self.expression(value, scope), scope)
                elif active and line.startswith('call '):
                    self.expression(line[5:], scope)
                elif active:
                    raise ValueError(f'{name}: unsupported packaged ground statement {line}')
                index += 1
        except _Return as returned:
            return returned.value
        require(not branches and not loops, f'{name}: unclosed packaged control flow')
        return None

    def native(self, name, args):
        if name == '_jass_div':
            return True, int(args[0] / args[1]) if all(type(value) is int for value in args) else args[0] / args[1]
        if name == 'ModuloInteger':
            return True, args[0] % args[1]
        if name in ('itemToIndex', 'itemFromIndex'):
            return True, args[0]
        if name.startswith('dispatch_LinkedList_LinkedList_'):
            operation = name.removeprefix('dispatch_LinkedList_LinkedList_')
            require(args[0] in self.queues, 'Packaged ground captured an uninitialized queue')
            queue = self.queues[args[0]]
            if operation == 'add_1':
                require(len(args) == 3, 'Queue add signature changed')
                queue.append(args[2])
                self.enqueued.append(args[2])
                return True, None
            if operation == 'isEmpty':
                return True, not queue
            if operation == 'dequeue':
                require(bool(queue), 'Packaged ground dequeued an empty queue')
                return True, queue.pop(0)
            raise ValueError('Unsupported packaged queue operation ' + operation)
        if name == 'GetEnumItem':
            return True, self.enum_item
        if name in ('GetItemTypeId', 'GetItemX', 'GetItemY', 'IsItemOwned', 'IsItemVisible'):
            item = self.items.get(args[0], {})
            return True, item.get({'GetItemTypeId': 'id', 'GetItemX': 'x', 'GetItemY': 'y',
                                   'IsItemOwned': 'owned', 'IsItemVisible': 'visible'}[name], 0)
        if name == 'RemoveItem':
            require(args[0] in self.items and self.items[args[0]]['id'] != 0,
                    'Packaged ground removed a missing/duplicate item')
            self.items[args[0]]['id'] = 0
            self.removed.append(args[0])
            return True, None
        if name == 'CreateItem':
            handle = self.add_item(*args)
            self.products.append(handle)
            return True, handle
        if name == 'SetItemPosition':
            self.items[args[0]].update(x=args[1], y=args[2])
            return True, None
        if name == 'GetRandomInt':
            self.random_calls.append(tuple(args))
            return True, args[1]
        if name == 'GetWorldBounds':
            return True, 1
        if name == 'RemoveRect':
            return True, None
        if name == 'EnumItemsInRect':
            require(args[2] == 'tdGroundCaptureItem', 'Ground snapshot callback changed')
            for handle in list(self.items):
                self.enum_item = handle
                self.invoke(args[2])
            return True, None
        if name == 'GetTriggerUnit':
            return True, self.farmer[0]
        if name == 'GetUnitTypeId':
            return True, self.farmer[2] if args[0] is not None else 0
        if name == 'GetOwningPlayer':
            return True, self.farmer[1]
        if name == 'GetPlayerId':
            return True, args[0]
        if name in ('GetSpellTargetX', 'GetSpellTargetY'):
            return True, self.target[name == 'GetSpellTargetY']
        if name == 'DisplayTimedTextToPlayer':
            self.messages.append(tuple(args))
            return True, None
        if name == 'int_toString':
            return True, str(args[0])
        return False, None

    def add_item(self, item_id, x, y, **flags):
        handle = len(self.items) + 1
        self.items[handle] = dict(id=item_id, x=x, y=y, owned=False, visible=True)
        self.items[handle].update(flags)
        return handle

    def cast(self, lane, point):
        self.farmer, self.target = (-100, lane, rawcode('uF01')), point
        self.invoke('tdGroundHandleUpgrade')

    def drain(self):
        for _ in range(len(self.items) + 30):
            if not self.globals[PREFIX + 'tdGroundBusy']:
                require(all(not queue for queue in self.queues.values()), 'Ground batch left a stale queue')
                return
            self.invoke('tdGroundProcessOne')
        raise ValueError('Packaged ground batch did not finish')

    def position(self, lane, quality, index=0):
        x = self.invoke('tdGroundItemPilePosition', lane, quality, index)
        return x, self.globals['tdGroundItemPilePosition_return_y']


def verify_rule_matrix(script):
    runtime = GroundJassRuntime(script)
    for quality, count in itertools.product(range(-1, 6), range(10)):
        require(runtime.invoke('tdGroundCraftBatchSize', quality, count) ==
                (3 if 1 <= quality <= 3 and count >= 3 else 0), 'Ground rule permits a pair/invalid quality')
    for roll in range(1, 101):
        require(runtime.invoke('tdCraftSucceeds', 2, roll) == (roll <= 65), 'Backpack pair probability changed')
        require(runtime.invoke('tdCraftSucceeds', 3, roll) is True, 'Backpack guaranteed triple changed')


def verify_geometry(script):
    runtime = GroundJassRuntime(script)
    for lane, quality, index in itertools.product(range(4), range(1, 6), range(30)):
        expected = expected_pile_position(lane, quality, index)
        require(runtime.position(lane, quality, index) == expected, 'Ground fixed four-lane coordinate oracle mismatch')
        require(runtime.invoke('tdGroundItemLane', *expected) == lane, 'Ground pile lane mapping mismatch')
    for lane, quality in itertools.product(range(4), range(1, 6)):
        center_x, center_y = expected_pile_position(lane, quality, 7)
        require(runtime.invoke('tdGroundPointInUpgradeCircle', center_x + 144.0, center_y, center_x, center_y) is True,
                'Ground 144 boundary must be included')
        require(runtime.invoke('tdGroundPointInUpgradeCircle', center_x + 145.0, center_y, center_x, center_y) is False,
                'Ground 145 boundary must be excluded')
    for x, y, expected in [(-1, 1, 0), (1, 1, 1), (1, -1, 2), (-1, -1, 3),
                           (0, 1, 1), (1, 0, 1), (0, 0, 1), (-1, 0, 0), (0, -1, 2)]:
        require(runtime.invoke('tdGroundItemLane', x, y) == expected, 'Ground half-open lane boundary mismatch')


def verify_capture_guards(script):
    runtime = GroundJassRuntime(script)
    runtime.globals[PREFIX + 'tdGroundCastPoint_x'] = -1.0
    runtime.globals[PREFIX + 'tdGroundCastPoint_y'] = 100.0
    runtime.globals[PREFIX + 'tdGroundCasterLane'] = 0
    handle = runtime.add_item(rawcode('iW01'), -1.0, 100.0)
    for crafting, nonnull, deleted, owned, visible, same_quality, same_lane, in_circle in itertools.product((False, True), repeat=8):
        runtime.globals[PREFIX + 'tdGroundCrafting'] = crafting
        item = runtime.items[handle]
        item.update(id=0 if deleted else rawcode('iW01' if same_quality else 'iG01'),
                    owned=owned, visible=visible, x=(-1.0 if same_lane else 1.0) * (1 if in_circle else 300))
        expected = nonnull and not deleted and not owned and visible and same_quality
        if crafting:
            expected = expected and same_lane and in_circle
        actual = runtime.invoke('tdGroundItemAvailable', handle if nonnull else None, 1)
        require(actual is bool(expected), 'Ground availability guard mismatch')
    for crafting, code, owned, visible in itertools.product((False, True), ('iW01', 'iG01', 'iB01', 'iP01', 'Ibal', 'ratf'), (False, True), (False, True)):
        runtime.globals[PREFIX + 'tdGroundCrafting'] = crafting
        runtime.items[handle].update(id=rawcode(code), x=-1.0, owned=owned, visible=visible)
        runtime.enum_item = handle
        before = len(runtime.enqueued)
        runtime.invoke('tdGroundCaptureItem')
        group = runtime.invoke('tdGroundItemGroup', rawcode(code))
        expected = group > 0 and not owned and visible and (not crafting or group < 4)
        require(len(runtime.enqueued) - before == int(expected), 'Ground capture guard mismatch')


def verify_upgrade_batches(script):
    scenarios = 0
    for lane, count, quality in itertools.product(range(4), range(10), range(1, 4)):
        runtime = GroundJassRuntime(script)
        point = expected_pile_position(lane, quality)
        originals = [runtime.add_item(rawcode(f'i{"WGB"[quality - 1]}0{index % 3 + 1}'), point[0] + index, point[1]) for index in range(count)]
        positions = {handle: (runtime.items[handle]['x'], runtime.items[handle]['y']) for handle in originals}
        runtime.cast(lane, point)
        runtime.drain()
        require(len(runtime.removed) == count // 3 * 3 and len(runtime.products) == count // 3,
                f'Ground batch lane={lane} quality={quality} count={count}: triple/leftover mismatch')
        require(not set(runtime.products) & set(runtime.enqueued), 'Ground products reentered the cast snapshot')
        require((1, 100) not in runtime.random_calls, 'Ground triples used a success roll')
        for handle in set(originals) - set(runtime.removed):
            require((runtime.items[handle]['x'], runtime.items[handle]['y']) == positions[handle], 'Ground leftover moved')
        for index, handle in enumerate(runtime.products):
            product = runtime.items[handle]
            require(runtime.invoke('tdItemQuality', product['id']) == quality + 1, 'Ground product quality mismatch')
            require((product['x'], product['y']) == expected_pile_position(lane, quality + 1, index), 'Ground output pile coordinate mismatch')
        scenarios += 1
    for whites, greens, blues, expected in [(6, 1, 2, (0, 3, 2, 0)), (3, 3, 3, (0, 1, 1, 1)), (9, 2, 0, (0, 5, 0, 0))]:
        runtime = GroundJassRuntime(script)
        point = expected_pile_position(0, 2)
        for quality, count in [(1, whites), (2, greens), (3, blues)]:
            for _ in range(count):
                runtime.add_item(rawcode('i' + 'WGB'[quality - 1] + '01'), *point)
        runtime.cast(0, point)
        runtime.drain()
        actual = tuple(sum(runtime.invoke('tdItemQuality', item['id']) == quality for item in runtime.items.values()) for quality in range(1, 5))
        require(actual == expected, 'Ground snapshot mixed-quality/no-cascade mismatch')
        if whites == 9:
            runtime.cast(0, point)
            runtime.drain()
            require(sum(runtime.invoke('tdItemQuality', item['id']) == 3 for item in runtime.items.values()) == 1, 'Ground products unavailable on the next cast')
        scenarios += 1
    return scenarios


def verify_lifecycle_guards(script):
    for slot, invalid in itertools.product(range(3), ('deleted', 'owned', 'hidden', 'outside', 'other_lane', 'quality', 'null')):
        runtime = GroundJassRuntime(script)
        originals = [runtime.add_item(rawcode('iW01'), -1.0, 100.0) for _ in range(3)]
        runtime.cast(0, (-1.0, 100.0))
        runtime.invoke('tdGroundProcessOne')
        runtime.invoke('tdGroundProcessOne')
        handle = originals[slot]
        if invalid == 'null':
            if slot < 2:
                runtime.globals[PREFIX + ('tdGroundFirst' if slot == 0 else 'tdGroundSecond')] = None
            else:
                runtime.queues[1][-1] = None
        else:
            updates = {'deleted': {'id': 0}, 'owned': {'owned': True}, 'hidden': {'visible': False},
                       'outside': {'x': -300.0}, 'other_lane': {'x': 1.0}, 'quality': {'id': rawcode('iG01')}}
            runtime.items[handle].update(updates[invalid])
        runtime.invoke('tdGroundConsumeBatch', None if invalid == 'null' and slot == 2 else originals[2])
        require(not runtime.removed and not runtime.products, f'Ground direct stale ingredient {slot}/{invalid} consumed')
        runtime.drain()
        require(not runtime.removed and not runtime.products, f'Ground stale ingredient {slot}/{invalid} consumed')
    runtime = GroundJassRuntime(script)
    point = expected_pile_position(0, 1)
    for _ in range(3):
        runtime.add_item(rawcode('iW01'), *point)
    runtime.cast(0, point)
    saved = (runtime.globals[PREFIX + 'tdGroundCasterLane'], runtime.globals[PREFIX + 'tdGroundCastPoint_x'], runtime.globals[PREFIX + 'tdGroundCastPoint_y'], tuple(runtime.enqueued))
    runtime.cast(1, expected_pile_position(1, 1))
    require(saved == (runtime.globals[PREFIX + 'tdGroundCasterLane'], runtime.globals[PREFIX + 'tdGroundCastPoint_x'], runtime.globals[PREFIX + 'tdGroundCastPoint_y'], tuple(runtime.enqueued)), 'Busy cast replaced the active snapshot')
    fresh = runtime.add_item(rawcode('iW01'), *point)
    runtime.drain()
    require(fresh not in runtime.removed and fresh not in runtime.enqueued, 'New drop entered the cast snapshot')
    require(all((runtime.items[handle]['x'], runtime.items[handle]['y']) == expected_pile_position(0, 2, index)
                for index, handle in enumerate(runtime.products)), 'Busy cast redirected product to another lane')
    for lane, target_lane in [(0, 1), (0, 3), (4, 0), (-1, 0)]:
        runtime = GroundJassRuntime(script)
        runtime.cast(lane, expected_pile_position(target_lane, 1))
        require(not runtime.globals[PREFIX + 'tdGroundBusy'] and not runtime.enqueued, 'Ground accepted an invalid/other-lane cast')
    runtime = GroundJassRuntime(script)
    for _ in range(3):
        runtime.add_item(rawcode('iW01'), *point)
    runtime.cast(0, point)
    runtime.invoke('tdGroundProcessOne')
    runtime.invoke('tdGroundProcessOne')
    runtime.globals['TDState_tdGameOver'] = True
    runtime.drain()
    require(not runtime.removed and not runtime.products and not runtime.messages, 'Ground mutated/notified after game over')
    require(runtime.globals[PREFIX + 'tdGroundCasterLane'] == -1 and runtime.globals[PREFIX + 'tdGroundFirst'] is None and runtime.globals[PREFIX + 'tdGroundSecond'] is None, 'Ground finish retained caster/ingredients')
    for stopped, third_null, duplicate in [(True, False, False), (False, True, False), (False, False, True)]:
        runtime = GroundJassRuntime(script)
        handles = [runtime.add_item(rawcode('iW01'), *point) for _ in range(3)]
        runtime.cast(0, point)
        runtime.globals[PREFIX + 'tdGroundFirst'] = handles[0]
        runtime.globals[PREFIX + 'tdGroundSecond'] = handles[0] if duplicate else handles[1]
        runtime.globals['TDState_tdGameOver'] = stopped
        runtime.invoke('tdGroundConsumeBatch', None if third_null else handles[2])
        require(not runtime.removed and not runtime.products, 'Ground directly consumed stopped/pair/duplicate batch')
    runtime = GroundJassRuntime(script)
    own = [runtime.add_item(rawcode('iW01'), -1.0, 100.0) for _ in range(3)]
    foreign = [runtime.add_item(rawcode('iW01'), 1.0, 100.0) for _ in range(3)]
    runtime.cast(0, (-1.0, 100.0))
    runtime.drain()
    require(set(runtime.removed) == set(own) and not set(foreign) & set(runtime.enqueued), 'Ground circle captured foreign-lane ingredients')


def verify_sort_preserved(script):
    runtime = GroundJassRuntime(script)
    original = {}
    for lane, group in itertools.product(range(4), range(1, 6)):
        point = expected_pile_position(lane, group)
        code = 'i' + 'WGBP'[group - 1] + '01' if group < 5 else 'Ibal'
        handle = runtime.add_item(rawcode(code), point[0] + 100, point[1] + 50)
        original[handle] = (lane, group, rawcode(code))
    runtime.invoke('tdGroundStart', False)
    runtime.drain()
    require(not runtime.products and not runtime.removed, 'Ground sort created/deleted items')
    for handle, (lane, group, code) in original.items():
        item = runtime.items[handle]
        require(item['id'] == code and (item['x'], item['y']) == expected_pile_position(lane, group), 'Ground sort changed lane/group/handle')


def verify_tooltip(abilities):
    tooltip = abilities['Gupg'][1][('aub1', 1, 0)][1]
    for text in ('本路', '每3件必得1件', '高一品质', '可不同名', '每次只升一级', '余1至2件原地保留', '本次不再参与升级', '对应品质堆'):
        require(text in tooltip, 'Ground tooltip lacks ' + text)
    for obsolete in ('65%', '失败', '继续合成至紫'):
        require(obsolete not in tooltip, 'Ground tooltip retains obsolete ' + obsolete)


def verify_ground_upgrade(script):
    for name in ('tdGroundCaptureItem', 'tdGroundItemAvailable', 'tdGroundConsumeBatch', 'tdGroundProcessOne', 'tdGroundHandleUpgrade'):
        for line in function_body(script, name).splitlines():
            require(not (re.search(r'\band\b', line) and re.search(r'\bor\b', line)), 'Ground contains ambiguous mixed JASS boolean precedence')
    require('tdGroundConsumeBatch(null' not in function_body(script, 'tdGroundProcessOne'), 'Ground retained pair-consumption path')
    verify_rule_matrix(script)
    verify_geometry(script)
    verify_capture_guards(script)
    scenarios = verify_upgrade_batches(script)
    verify_lifecycle_guards(script)
    verify_sort_preserved(script)
    return scenarios


def main():
    require(len(sys.argv) == 2, __doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    script = artifact.extract('war3map.j').decode('utf-8')
    scenarios = verify_ground_upgrade(script)
    verify_tooltip(ability_objects(artifact.extract('war3map.w3a')))
    print(f'PASS actual JASS ground upgrade: {scenarios} batch scenarios; 256 availability states; 600 independently fixed pile coordinates and 144/145 boundaries; capture, stale ingredients, snapshot, no-cascade, frozen lane; backpack probabilities unchanged')
    print('NOT TESTED: native handle reuse, relocation/pathing, timer registration/UI, multiplayer synchronization or gameplay.')


if __name__ == '__main__':
    main()
