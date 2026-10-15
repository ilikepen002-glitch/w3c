"""Prepared actual-JASS craft executor; no candidate exists yet.

Production catalog/planner/class allocators/backend/watch/recovery/placement and
the real periodic callback execute from the supplied JASS. Only the explicitly
listed Warcraft natives and standard-library collection boundaries are models.
This cannot prove engine relocation, UI, timers, multiplayer or client gameplay.
Unknown functions/scalars/natives remain fail-closed. The public constructor
rejects maps without the new delivery/recovery contract; no legacy substitution.
"""
from collections import defaultdict
import re

from VerifyGroundUpgradeArtifact import GroundJassRuntime
from VerifyTowerUpgradeArtifact import JassScalarEvaluator, rawcode
from VerifyEquipmentAbilityArtifact import require


class InventoryCraftJassRuntime(GroundJassRuntime):
    REQUIRED = ('tdCraftWatchAcquire', 'tdCraftStagedMaterialValid',
                'tdCraftTryRecover', 'tdCraftRememberCustody',
                'tdCraftCatalogReady', 'tdStartInventoryCraft',
                'tdStartGroundCraft', 'tdFinishCraftSession')
    INIT_PACKAGES = ('TDConfig', 'TDItemCatalogIds', 'TDItemCatalogSchema',
                     'TDItemData', 'TDGroundItemRules',
                     'TDGroundItemTerrainMask', 'TDItemOperationState',
                     'TDCraftingCatalog', 'TDCraftingTransaction',
                     'TDCraftingItemWatch', 'TDCraftingRecovery',
                     'TDCraftingNativeBackend', 'TDCraftingRuntime')

    def __init__(self, script):
        JassScalarEvaluator.__init__(self, script)
        require(all(name in self.functions for name in self.REQUIRED),
                'PENDING new candidate: required delivery/recovery functions absent')
        self.initialize_models(script)
        require('TDCraftNativeBackend_phase' in self.globals and
                'TDCraftNativeBackend_staging' in self.globals,
                'PENDING new candidate: native delivery state absent')
        for package in self.INIT_PACKAGES:
            name = 'init_' + package
            # Pure packages without globals need no generated initializer.
            if name in self.functions:
                self.invoke(name)
        require('TDCraftingItemWatch_tdCraftPickupRecords' in self.globals,
                'Candidate pickup-watch namespace changed; review required')
        self.invoke('tdSetupCraftPickupWatch')
        self.callback = self.invoke('alloc_CallbackPeriodic_doPeriodically_TDCraftingRuntime')
        self.invoke('construct_CallbackPeriodic', self.callback)

    def initialize_models(self, script):
        self.globals = {}
        declarations = script.split('globals\n', 1)[1].split('endglobals', 1)[0]
        for kind, array, name in re.findall(r'^(\w+) (array )?(\w+)', declarations, re.M):
            default = False if kind == 'boolean' else 0.0 if kind == 'real' else 0 if kind == 'integer' else None
            self.globals[name] = defaultdict(lambda value=default: value) if array else default
        # common.j constants are opaque types, not arbitrary success booleans.
        self.walkability = object()
        self.pickup_event = object()
        self.globals.update(JASS_MAX_ARRAY_SIZE=8192,
                            PATHING_TYPE_WALKABILITY=self.walkability,
                            EVENT_PLAYER_UNIT_PICKUP_ITEM=self.pickup_event)
        for name in self.globals:
            if name.startswith('ref_function_'):
                function = name.removeprefix('ref_function_')
                require(function in self.functions, 'Missing exact function reference ' + function)
                self.globals[name] = function
        self.items, self.units = {}, {}
        self.collections, self.iterators, self.tables, self.triggers = {}, {}, {}, {}
        self.next_model_id = 1000000
        self.products, self.removed, self.messages = [], [], []
        self.adds, self.detaches, self.moves, self.pathing_calls = [], [], [], []
        self.current_item = self.current_unit = self.enum_item = None
        self.output_mode = self.return_mode = (True, True)
        self.create_mode = 'normal'
        self.alias_item = None
        self.wrong_rawcode = rawcode('iP01')
        self.drop_mode = 'after'
        self.on_create = self.on_add = self.on_drop = self.on_move = None
        self.block_terrain = True
        self.position_transform = None
        self.roll = 1
        self.random_calls = []

    def model_id(self):
        self.next_model_id += 1
        return self.next_model_id

    def collection(self, handle):
        require(handle in self.collections, 'Invalid modeled LinkedList handle')
        return self.collections[handle]

    def table(self, handle):
        require(handle in self.tables, 'Invalid modeled Table/HashMap handle')
        return self.tables[handle]

    def native(self, name, args):
        # Compiler foreach emits these non-dispatch standard-library bridges.
        if name in ('LinkedList_iterator', 'LLIterator_hasNext', 'LLIterator_next', 'LLIterator_close'):
            if name == 'LinkedList_iterator':
                return self.native('dispatch_LinkedList_LinkedList_iterator', args)
            if name == 'LLIterator_close':
                return self.native('dispatch_LLIterator_destroyLLIterator', args)
            return self.native('dispatch_LLIterator_LLIterator_' + name.removeprefix('LLIterator_'), args)
        if name == 'new_LinkedList':
            handle = self.model_id();self.collections[handle] = []
            return True, handle
        if name in ('new_Table', 'new_HashMap'):
            handle = self.model_id();self.tables[handle] = {}
            return True, handle
        if name.startswith('dispatch_LinkedList_'):
            operation = name.removeprefix('dispatch_LinkedList_')
            values = self.collection(args[0])
            if operation == 'destroyLinkedList':
                del self.collections[args[0]];return True, None
            operation = operation.removeprefix('LinkedList_')
            if operation == 'add_1':
                require(len(args) == 3, 'LinkedList.add signature changed')
                values.append(args[2]);return True, None
            if operation == 'size':return True, len(values)
            if operation == 'isEmpty':return True, not values
            if operation == 'get':return True, values[args[1]]
            if operation == 'dequeue':
                require(bool(values), 'Modeled LinkedList dequeued empty list')
                return True, values.pop(0)
            if operation == 'iterator':
                handle = self.model_id();self.iterators[handle] = [args[0], 0]
                return True, handle
            raise ValueError('Unsupported modeled LinkedList operation ' + operation)
        if name.startswith('dispatch_LLIterator_'):
            operation = name.removeprefix('dispatch_LLIterator_').removeprefix('LLIterator_')
            require(args[0] in self.iterators, 'Invalid modeled iterator handle')
            iterator = self.iterators[args[0]];values = self.collection(iterator[0])
            if operation == 'destroyLLIterator':
                del self.iterators[args[0]];return True, None
            if operation == 'hasNext':return True, iterator[1] < len(values)
            if operation == 'next':
                require(iterator[1] < len(values), 'Modeled iterator advanced past end')
                value = values[iterator[1]];iterator[1] += 1;return True, value
            raise ValueError('Unsupported modeled iterator operation ' + operation)
        if name.startswith(('dispatch_Table_', 'dispatch_HashMap_')):
            operation = name.split('_', 3)[-1]
            table = self.table(args[0])
            if operation in ('destroyTable', 'destroyHashMap'):
                del self.tables[args[0]];return True, None
            if operation in ('put', 'saveInt', 'saveString', 'saveBoolean'):
                table[args[1]] = args[2];return True, None
            if operation in ('has', 'hasInt', 'hasString', 'hasBoolean'):
                return True, args[1] in table
            if operation in ('get', 'loadInt', 'loadString', 'loadBoolean'):
                default = False if operation == 'loadBoolean' else None if operation == 'loadString' else 0
                return True, table.get(args[1], default)
            if operation in ('remove', 'removeInt', 'removeString', 'removeBoolean'):
                table.pop(args[1], None);return True, None
            raise ValueError('Unsupported modeled Table/HashMap operation ' + operation)
        if name == 'error':raise ValueError('Actual packaged runtime error: ' + str(args[0]))
        if name == 'CreateTrigger':
            handle = self.model_id();self.triggers[handle] = [];return True, handle
        if name == 'trigger_registerAnyUnitEvent':
            require(args[0] in self.triggers and args[1] is self.pickup_event,
                    'Pickup watch registered unexpected native event')
            return True, None
        if name == 'trigger_addAction':
            require(args[0] in self.triggers and args[1] in self.functions,
                    'Pickup watch action is not a real packaged function')
            self.triggers[args[0]].append(args[1]);return True, None
        if name in ('PauseTimer', 'DestroyTimer'):
            # Periodic scheduling is driven explicitly by tick(), not an engine
            # clock. The real closure and session destructor still execute.
            return True, None
        if name == 'timer_release':return True, None
        if name == 'Rect':return True, tuple(args)
        if name == 'RemoveRect':return True, None
        if name == 'EnumItemsInRect':
            require(len(args) == 3 and args[1] is None and args[2] in self.functions,
                    'Unexpected ground enumeration filter/callback')
            left,bottom,right,top=args[0]
            for handle in list(self.items):
                item=self.items[handle]
                if item['id'] and left<=item['x']<=right and bottom<=item['y']<=top:
                    self.enum_item=handle;self.invoke(args[2])
            return True, None
        if name in ('GetTriggerUnit', 'GetManipulatedItem', 'GetEnumItem'):
            return True, {'GetTriggerUnit': self.current_unit, 'GetManipulatedItem': self.current_item,
                          'GetEnumItem': self.enum_item}[name]
        if name == 'GetHandleId':return True, args[0] or 0
        if name == 'GetPlayerId':return True, args[0]
        if name == 'Player':return True, args[0]
        if name in ('GetUnitTypeId', 'GetOwningPlayer', 'GetUnitX', 'GetUnitY', 'UnitAlive'):
            unit = self.units.get(args[0], {})
            key = {'GetUnitTypeId': 'id', 'GetOwningPlayer': 'owner', 'GetUnitX': 'x',
                   'GetUnitY': 'y', 'UnitAlive': 'alive'}[name]
            return True, unit.get(key, False if name == 'UnitAlive' else 0)
        if name == 'UnitItemInSlot':return True, self.units[args[0]]['slots'][args[1]]
        if name == 'UnitAddItem':
            self.adds.append(tuple(args));item = args[1]
            result, insert = self.output_mode if item in self.products else self.return_mode
            slot = next((n for n, value in enumerate(self.units[args[0]]['slots']) if value is None), None)
            if insert and slot is not None:self.pickup(args[0], item, slot)
            if self.on_add:self.on_add(*args)
            return True, result
        if name == 'UnitRemoveItem':
            self.detaches.append(args[1])
            if self.drop_mode == 'before':
                if self.on_drop:self.on_drop(*args)
                if self.items[args[1]]['holder'] == args[0]:self.unlink(args[1])
            elif self.drop_mode == 'none':
                if self.on_drop:self.on_drop(*args)
            else:
                self.unlink(args[1])
                if self.on_drop:self.on_drop(*args)
            return True, None
        if name in ('GetItemTypeId', 'GetItemX', 'GetItemY', 'IsItemOwned', 'IsItemVisible'):
            item = self.items.get(args[0], {})
            if name == 'IsItemOwned':return True, item.get('holder') is not None
            return True, item.get({'GetItemTypeId': 'id', 'GetItemX': 'x', 'GetItemY': 'y',
                                   'IsItemVisible': 'visible'}[name], 0)
        if name == 'SetItemVisible':
            self.items[args[0]]['visible'] = args[1];return True, None
        if name == 'CreateItem':
            if self.create_mode == 'null':return True, None
            if self.create_mode == 'alias':
                require(self.alias_item in self.items, 'Alias fixture requires exact original handle')
                return True, self.alias_item
            handle = self.add_item(self.wrong_rawcode if self.create_mode == 'wrong' else args[0], *args[1:])
            self.products.append(handle)
            if self.on_create:self.on_create(handle)
            return True, handle
        if name == 'RemoveItem':
            require(args[0] in self.items, 'Removed unknown modeled item')
            # The engine accepts cleanup of an externally deleted product.
            if self.items[args[0]]['id']:
                self.unlink(args[0]);self.items[args[0]]['id'] = 0;self.removed.append(args[0])
            return True, None
        if name == 'SetItemPosition':
            self.moves.append(tuple(args));point = tuple(args[1:])
            if self.position_transform:point = self.position_transform(args[0], *point)
            self.items[args[0]].update(x=point[0], y=point[1])
            if self.on_move:self.on_move(*args)
            return True, None
        if name == 'IsTerrainPathable':
            require(len(args) == 3 and args[2] is self.walkability,
                    'Unknown/incorrect native pathing type; expected walkability')
            self.pathing_calls.append(tuple(args[:2]));return True, self.block_terrain
        if name == 'GetRandomInt':
            require(args[0] <= self.roll <= args[1], 'Controlled roll outside real catalog range')
            self.random_calls.append(tuple(args));return True, self.roll
        if name == 'R2I':return True, int(args[0])
        if name == 'I2R':return True, float(args[0])
        if name == 'SubString':
            require(isinstance(args[0],str), 'SubString requires actual compiled string data')
            return True, args[0][max(0,args[1]):max(0,args[2])]
        if name == 'int_toString':return True, str(args[0])
        if name == 'DisplayTimedTextToPlayer':self.messages.append(tuple(args));return True, None
        # Only arithmetic boundary; do not inherit the retired ground queue,
        # catalog, item bridge or fake farmer assumptions from the old verifier.
        if name == '_jass_div':
            return True, int(args[0]/args[1]) if all(type(v) is int for v in args) else args[0]/args[1]
        if name == 'ModuloInteger':return True, args[0] % args[1]
        return False, None

    def add_unit(self, owner, x=-768., y=2560.):
        handle = self.model_id()
        self.units[handle] = dict(id=rawcode('uF01'), owner=owner, alive=True,
                                  x=x, y=y, slots=[None]*6)
        return handle

    def add_item(self, item_id, x, y):
        handle = self.model_id()
        self.items[handle] = dict(id=item_id, x=x, y=y, holder=None, visible=True)
        return handle

    def unlink(self, item):
        holder = self.items[item]['holder']
        if holder is not None:
            slots = self.units[holder]['slots']
            for slot, value in enumerate(slots):
                if value == item:slots[slot] = None
        self.items[item]['holder'] = None

    def place(self, unit, item, slot):
        self.unlink(item)
        require(self.units[unit]['slots'][slot] is None, 'Occupied modeled inventory slot')
        self.units[unit]['slots'][slot] = item;self.items[item]['holder'] = unit

    def pickup(self, unit, item, slot=None):
        if slot is None:
            slot = next((s for s, value in enumerate(self.units[unit]['slots']) if value is None), None)
        if slot is not None:self.place(unit, item, slot)
        self.current_unit, self.current_item = unit, item
        # Execute actual watch bridge, not a synthesized pickup-serial shortcut.
        self.invoke('tdCraftTrackPickup')

    def tick(self):
        signature=self.functions['call_doPeriodically_TDCraftingRuntime'][0]
        require(signature[:-1] == ['this_2','cb_1'], 'Periodic callback signature changed; review required')
        self.invoke('call_doPeriodically_TDCraftingRuntime', self.callback, self.callback)

    def drain(self):
        for _ in range(len(self.items)+100):
            if not self.globals['TDCraftingRuntime_tdCraftSession']:
                require(not self.globals['TDItemOperationState_tdItemOperationBusy'],
                        'Actual tdFinishCraftSession failed to release global operation lock')
                return
            self.tick()
        raise ValueError('Actual packaged craft session did not finish')
