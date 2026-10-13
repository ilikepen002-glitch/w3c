"""Execute actual crafting source bodies with bounded native stubs.
Not Wurst typechecking, compiled JASS, or Warcraft-native placement proof.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from test_elemental_pet_runtime_source import compile_body

ROOT = Path(__file__).resolve().parents[2]


class Records(dict):
    def has(self, key):
        return key in self


class CraftFixture:
    def __init__(self, lane=0, quality=2, inventory=False, placement=0, reject_final=False):
        self.items = []
        self.moves = []
        self.removed = []
        self.origin = NS(x=10 + lane, y=20)
        self.records = Records()
        for key in range(1, 6):
            itm = self.create(quality - 1, key, 99)
            self.records[key] = NS(itemHandle=itm, rawcode=quality - 1)
        self.leftovers = [(it, it.x, it.y) for it in self.items[3:]]
        self.reject_final = reject_final
        self.placement = placement
        self.invalidated = False
        self.inventory_result = None
        self.n = dict(output=None, outputId=0, outputKey=0, pileCounts=[0] * 5,
                      inventory=inventory, origin=self.origin, lane=lane, records=self.records,
                      farmer=object(), caster=object(), deliveryExceptions=0,
                      tdItemIsEquipment=lambda raw: 1 <= raw <= 4,
                      tdItemQuality=lambda raw: raw, CreateItem=self.create,
                      SetItemVisible=lambda it, value: setattr(it, 'visible', value),
                      GetItemTypeId=lambda it: it.raw if it and not it.removed else 0,
                      RemoveItem=self.remove,
                      tdTryPlaceItemInPile=self.place_pile, tdTryPlaceItemNear=self.place_near,
                      tdGroundItemHandleValid=lambda it: it is not None and not it.removed,
                      tdItemActualPosition=lambda it: it,
                      tdItemGroundPointSafe=lambda lane, it: it.lane == lane,
                      tdItemActualInPile=lambda it, lane, quality: not self.reject_final and it.lane == lane and it.pile == quality,
                      available=self.available, UnitAddItem=self.add_inventory,
                      UnitItemInSlot=lambda farmer, slot: self.inventory_result if slot == 0 else None)
        body = (ROOT / 'wurst/items/TDCraftingNativeBackend.wurst').read_text().replace('override function ', 'function ')
        fields = ('output', 'outputId', 'outputKey', 'deliveryExceptions')
        for method in ('prepareResult', 'consumeThree', 'publishResult', 'discardResult'):
            compile_body(body, method, self.n, fields)
        self.backend = NS(**{name: self.n[name] for name in ('prepareResult', 'consumeThree', 'publishResult', 'discardResult')}, available=self.available)
        self.attempted = False
        ingredients = [NS(getKey=lambda key=key: key, getRawcode=lambda: quality - 1) for key in (1, 2, 3)]
        batch = NS(beginAttempt=self.begin_attempt, result=lambda catalog, roll: quality,
                   sourceQuality=lambda: quality - 1, ingredient=lambda slot: ingredients[slot])
        catalog = NS(quality=lambda raw: raw)
        plan = NS(isFrozen=lambda: True, usesCatalog=lambda other: other is catalog,
                  batch=lambda index: batch if index == 0 else None)
        transaction = (ROOT / 'wurst/items/TDCraftingTransaction.wurst').read_text()
        self.n.update(TD_CRAFT_COMMIT_CANCELLED=0, TD_CRAFT_COMMIT_SUCCESS=1,
                      TD_CRAFT_COMMIT_RESULT_FAILED=2, TD_CRAFT_COMMIT_ALREADY_ATTEMPTED=3)
        compile_body(transaction, 'tdCraftBatchAvailable', self.n)
        commit = compile_body(transaction, 'tdCommitCraftBatch', self.n)
        self.commit = lambda: commit(plan, 0, catalog, self.backend, 1)

    def begin_attempt(self):
        old = self.attempted
        self.attempted = True
        return not old

    def available(self, key, raw):
        return not self.invalidated and key in self.records and not self.records[key].itemHandle.removed and self.records[key].rawcode == raw

    def create(self, raw, x, y):
        it = NS(raw=raw, x=x, y=y, lane=-1, pile=0, removed=False, visible=True)
        self.items.append(it)
        return it

    def remove(self, it):
        assert not it.removed
        it.removed = True
        self.removed.append(it)

    def place_pile(self, it, lane, quality, index):
        self.moves.append(('pile', it, lane, quality, index))
        # Native stub represents the existing checked placement API; no origin filter.
        it.lane, it.pile = lane, quality
        it.x, it.y = lane * 1000, quality * 100
        return self.placement if self.placement < 0 else index

    def place_near(self, it, lane, origin, nearby):
        self.moves.append(('near', it, lane, origin.x, origin.y))
        it.lane, it.x, it.y = lane, origin.x, origin.y
        return True

    def add_inventory(self, farmer, it):
        self.inventory_result = it
        return True


class GroundUpgradeRuntimeSourceTests(unittest.TestCase):
    def test_four_lanes_three_result_qualities_direct_delivery_and_leftovers(self):
        for lane in range(4):
            for quality in (2, 3, 4):
                with self.subTest(lane=lane, quality=quality):
                    f = CraftFixture(lane, quality)
                    self.assertEqual(f.commit(), 1)
                    output = f.items[-1]
                    self.assertEqual((output.lane, output.pile), (lane, quality))
                    self.assertTrue(output.visible)
                    self.assertEqual(f.removed, f.items[:3])
                    self.assertEqual(len(f.moves), 1)
                    self.assertIs(f.moves[0][1], output)
                    for it, x, y in f.leftovers:
                        self.assertEqual((it.x, it.y, it.removed), (x, y, False))
                    self.assertEqual(f.commit(), 3)
                    self.assertEqual(len(f.items), 6)
                    self.assertEqual(len(f.removed), 3)

    def test_failed_preparation_or_final_projection_never_consumes_materials(self):
        for placement, rejected, expected in ((-1, False, 2), (-2, False, 2), (0, True, 0)):
            with self.subTest(placement=placement, rejected=rejected):
                f = CraftFixture(placement=placement, reject_final=rejected)
                self.assertEqual(f.commit(), expected)
                self.assertEqual(f.removed, [f.items[-1]])
                self.assertTrue(all(not it.removed for it in f.items[:5]))
                self.assertIsNone(f.n['output'])

    def test_failed_creation_and_foreign_lane_projection_keep_inputs(self):
        for create_fails in (True, False):
            f = CraftFixture(lane=2)
            if create_fails:
                f.n['CreateItem'] = lambda *args: None
            else:
                original = f.n['tdTryPlaceItemInPile']
                def wrong_lane(*args):
                    index = original(*args)
                    args[0].lane = 1
                    return index
                f.n['tdTryPlaceItemInPile'] = wrong_lane
            self.assertEqual(f.commit(), 2 if create_fails else 0)
            self.assertTrue(all(not it.removed for it in f.items[:5]))
            self.assertEqual(len(f.removed), 0 if create_fails else 1)
            self.assertIsNone(f.n['output'])

    def test_source_invalidation_after_placement_discards_only_hidden_output(self):
        f = CraftFixture()
        original = f.n['tdTryPlaceItemInPile']
        def invalidate(*args):
            result = original(*args)
            f.invalidated = True
            return result
        f.n['tdTryPlaceItemInPile'] = invalidate
        self.assertEqual(f.commit(), 0)
        self.assertEqual(f.removed, [f.items[-1]])
        self.assertFalse(f.items[-1].visible)
        self.assertTrue(all(not it.removed for it in f.items[:5]))

    def test_inventory_prepares_near_original_point_and_returns_to_inventory(self):
        f = CraftFixture(lane=3, quality=4, inventory=True, reject_final=True)
        self.assertEqual(f.commit(), 1)
        output = f.items[-1]
        self.assertEqual(f.moves, [('near', output, 3, f.origin.x, f.origin.y)])
        self.assertIs(f.inventory_result, output)
        self.assertTrue(output.visible)


if __name__ == '__main__':
    unittest.main()
