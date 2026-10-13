"""Execute actual ball delivery/pickup source with deterministic native stubs.
These tests are source behavior checks, not Warcraft-native playtest evidence.
"""
import unittest
from types import SimpleNamespace
from test_elemental_pet_runtime_source import compile_body, source


class Owners(dict):
    def saveInt(self, key, value):
        self[key] = value

    def loadInt(self, key):
        return self.get(key, 0)

    def removeInt(self, key):
        self.pop(key, None)


class Handle:
    def __init__(self, key, owner=0):
        self.key, self.owner, self.removed = key, owner, False
        self.position = SimpleNamespace(x=100., y=200.)
        self.level = None

    def getHandleId(self):
        return self.key

    def getPos(self):
        return self.position

    def setAbilityLevel(self, ability, level):
        self.level = level

    def remove(self):
        self.removed = True


class AutoCollectTests(unittest.TestCase):
    def setUp(self):
        self.ground, self.notices, self.removals = [], [], []
        self.carrier, self.ball = Handle(99), None
        self.active, self.defeated, self.over = [True] * 4, [False] * 4, False
        self.n = dict(tdPetBalls=[3] * 4, TD_PET_BALL_LIMIT=60,
            tdPetPlayerLeft=[False] * 4, tdPetFarmers=[Handle(200 + i, i) for i in range(4)],
            tdPetBallOwners=Owners(), TD_PET_BALL_ITEM_ID=123, TD_PET_CAPTURE_ABILITY_ID=456,
            tdIsLanePlayer=lambda lane: 0 <= lane < 4,
            tdIsLaneActive=lambda lane: self.active[lane],
            tdIsLaneDefeated=lambda lane: self.defeated[lane], tdIsGameOver=lambda: self.over,
            tdPetNotice=lambda *args: self.notices.append(args), IMinBJ=min,
            tdPetBallsForLane=lambda lane: self.n['tdPetBalls'][lane],
            createItem=self.create_item, GetManipulatedItem=lambda: self.ball,
            GetManipulatingUnit=lambda: self.carrier, GetItemTypeId=lambda ball: 123,
            GetOwningPlayer=lambda unit: unit.owner, GetPlayerId=lambda player: player,
            UnitRemoveItem=lambda unit, ball: self.removals.append(ball),
            SetItemPosition=lambda ball, x, y: setattr(ball, 'position', SimpleNamespace(x=x, y=y)))
        for name in ('tdPetAddBall', 'tdPetTakeBall', 'tdPetLaneCanManage'):
            compile_body(source('TDPetState'), name, self.n)
        # The shared translator handles scalar toString, not call-result toString.
        # Normalize only the display conversion; all branch/state code is unchanged.
        runtime = source('TDPetRuntime').replace('tdPetBallsForLane(lane).toString()', 'str(tdPetBallsForLane(lane))')
        for name in ('tdPetLaneCanAct', 'tdPetSyncBallAbility', 'tdPetDeliverBallDrop', 'tdPetHandleBallPickup'):
            compile_body(runtime, name, self.n)

    def create_item(self, item_type, position):
        ball = Handle(len(self.ground) + 1)
        ball.position = position
        self.ground.append(ball)
        return ball

    def deliver(self, lane):
        self.n['tdPetDeliverBallDrop'](lane, self.carrier.getPos())

    def test_credit_only_own_lane_once_and_sync_q_without_inventory_item(self):
        self.deliver(2)
        self.assertEqual(self.n['tdPetBalls'], [3, 3, 4, 3])
        self.assertEqual(self.n['tdPetFarmers'][2].level, 5)
        self.assertEqual(self.ground, [])
        self.assertEqual(len(self.notices), 1)

    def test_null_farmer_credits_shared_counter_without_losing_reward(self):
        self.n['tdPetFarmers'][2] = None
        self.deliver(2)
        self.assertEqual(self.n['tdPetBalls'][2], 4)
        self.assertEqual(self.ground, [])
        farmer = self.n['tdPetFarmers'][2] = Handle(202, 2)
        self.n['tdPetSyncBallAbility'](2)
        self.assertEqual(farmer.level, 5)

    def test_fifty_nine_reaches_sixty_then_preserves_owned_ground_ball(self):
        self.n['tdPetBalls'][1] = 59
        self.deliver(1)
        self.assertEqual(self.n['tdPetFarmers'][1].level, 61)
        self.assertEqual(self.ground, [])
        self.deliver(1)
        self.assertEqual(self.n['tdPetBalls'][1], 60)
        self.assertEqual(len(self.ground), 1)
        self.assertEqual(self.n['tdPetBallOwners'][1], 2)

    def test_old_ground_ball_keeps_manual_pickup_and_cannot_credit_twice(self):
        self.n['tdPetBalls'][0] = 60
        self.deliver(0)
        self.ball = self.ground[0]
        self.n['tdPetHandleBallPickup']()
        self.assertFalse(self.ball.removed)
        self.assertIn(1, self.n['tdPetBallOwners'])
        self.n['tdPetTakeBall'](0)
        self.n['tdPetHandleBallPickup']()
        self.assertEqual(self.n['tdPetBalls'][0], 60)
        self.assertTrue(self.ball.removed)
        self.assertNotIn(1, self.n['tdPetBallOwners'])
        self.n['tdPetTakeBall'](0)
        self.n['tdPetHandleBallPickup']()
        self.assertEqual(self.n['tdPetBalls'][0], 59)

    def test_other_lane_cannot_take_fallback_ball(self):
        self.n['tdPetBalls'][1] = 60
        self.deliver(1)
        self.ball = self.ground[0]
        self.n['tdPetHandleBallPickup']()
        self.assertEqual(self.n['tdPetBalls'][0], 3)
        self.assertFalse(self.ball.removed)
        self.assertEqual(self.n['tdPetBallOwners'][1], 2)

    def test_left_inactive_defeated_game_over_and_invalid_lane_do_not_credit(self):
        self.n['tdPetPlayerLeft'][0] = True
        self.active[1] = False
        self.defeated[2] = True
        for lane in (-1, 0, 1, 2, 4):
            self.deliver(lane)
        self.over = True
        self.deliver(3)
        self.assertEqual(self.n['tdPetBalls'], [3] * 4)
        self.assertEqual(self.ground, [])

    def test_left_player_cannot_pick_up_existing_ball(self):
        self.n['tdPetBalls'][0] = 60
        self.deliver(0)
        self.ball = self.ground[0]
        self.n['tdPetTakeBall'](0)
        self.n['tdPetPlayerLeft'][0] = True
        self.n['tdPetHandleBallPickup']()
        self.assertEqual(self.n['tdPetBalls'][0], 59)
        self.assertFalse(self.ball.removed)
        self.assertIn(1, self.n['tdPetBallOwners'])

    def test_both_drop_paths_keep_budget_then_use_common_delivery(self):
        from VerifyPetManagerSource import function_body
        runtime = source('TDPetRuntime')
        for name in ('tdPetHandleEnemyBallDrop', 'tdPetHandleBossBallCompensation'):
            _, body = function_body(runtime, name)
            self.assertLess(body.index('tdPetTakeDropBudget(lane, wave)'), body.index('tdPetDeliverBallDrop(lane, enemy.getPos())'))
            self.assertNotIn('createItem(', body)
        self.assertEqual(runtime.count('createItem(TD_PET_BALL_ITEM_ID,'), 1)


if __name__ == '__main__':
    unittest.main()
