#!/usr/bin/env python3
"""Source contracts and deterministic budget/lifecycle model (not a Warcraft/FPS test).

The gate is evaluated from the checked-in Wurst expression. Native Fx effect
failure is modeled as a valid dummy with a null effect, matching Fx.setFx.
Run the existing packed combat replay after the serial compiler gate as well.
"""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = 'wurst/towers/TDTowerRuntime.wurst'
SOURCE = (ROOT / PATH).read_text()
LIVE = int(re.search(r'TD_ARCHER_VISUAL_LIVE_LIMIT = (\d+)', SOURCE)[1])
RATE = int(re.search(r'TD_ARCHER_VISUAL_NEW_PER_SECOND = (\d+)', SOURCE)[1])
EXPR = re.search(r'function tdArcherVisualBudgetAllows[^\n]+\n\treturn ([^\n]+)', SOURCE)[1]

def allowed(live, created):
    return eval(EXPR, {'__builtins__': {}}, dict(liveCount=live, creationCount=created,
        TD_ARCHER_VISUAL_LIVE_LIMIT=LIVE, TD_ARCHER_VISUAL_NEW_PER_SECOND=RATE))

class Model:
    def __init__(self):
        self.now = 0.; self.epoch = 0; self.window = -1; self.created = 0
        self.arrows = []; self.cooling = []; self.attempts = 0; self.timer = False
        self.effects = 0; self.destroyed = 0
    def launch(self, duration=10., source=True, target=True, effect=True):
        if not source or not target: return
        window = int(self.now)
        if self.window != window: self.window, self.created = window, 0
        if not allowed(len(self.arrows), self.created): return
        self.created += 1; self.attempts += 1
        self.arrows.append([max(.03, duration), 0., self.epoch, effect])
        self.effects += int(effect); self.timer = True
    def tick(self):
        self.now += .03
        for arrow in self.arrows[:]:
            arrow[1] += .03
            if arrow[2] != self.epoch or arrow[1] >= arrow[0]:
                self.arrows.remove(arrow); self.effects -= int(arrow[3])
                self.destroyed += 1; self.cooling.append(self.now + 1.)
        self.cooling = [expiry for expiry in self.cooling if expiry > self.now]
        self.timer = bool(self.arrows)

class BudgetTests(unittest.TestCase):
    def test_source_limits_gate_before_allocation(self):
        body = SOURCE.split('function tdLaunchArcherSplitArrowVisual', 1)[1].split('\nfunction ', 1)[0]
        self.assertLess(body.index('source == null'), body.index('getElapsedGameTime'))
        self.assertLess(body.index('tdArcherVisualBudgetAllows'), body.index('new TDArcherArrowVisual'))
        self.assertLess(body.index('tdArcherVisualCreationCount += 1'), body.index('new TDArcherArrowVisual'))
        self.assertEqual(body.count('doPeriodically('), 1)
        self.assertIn('if arrow.epoch != tdFlowEpoch()\n\t\t\t\titr.remove()\n\t\t\t\tdestroy arrow\n\t\t\t\tcontinue', body)
        self.assertIn('if tdArcherArrowVisuals.isEmpty()\n\t\t\ttdArcherVisualTimerRunning = false\n\t\t\tdestroy cb', body)
        self.assertNotIn('tdArcherVisualCreationCount = 0', body.split('doPeriodically', 1)[1])
        self.assertEqual((LIVE, RATE), (8, 6))
    def test_combat_source_identical_to_official_base(self):
        before = subprocess.check_output(['git', 'show', 'bfd59de:' + PATH], cwd=ROOT, text=True)
        # Everything before/after the sole visual-owner block, apart from its two imports.
        clean = SOURCE.replace('import TDWaveFlowState\n', '').replace('import GameTimer\n', '')
        self.assertEqual(before.split('class TDArcherArrowVisual')[0], clean.split('// The shared recycler')[0])
        self.assertEqual(before.split('function tdFindFarthestArcherSplitArrowShot')[1], clean.split('function tdFindFarthestArcherSplitArrowShot')[1])
    def test_large_pressure_and_normal_noop(self):
        m = Model()
        for _ in range(100000): m.launch()
        self.assertEqual((len(m.arrows), m.attempts), (RATE, RATE))
        m.now = 1.
        for _ in range(100000): m.launch()
        self.assertEqual((len(m.arrows), m.attempts), (LIVE, LIVE))
        self.assertTrue(allowed(0, 0)); self.assertTrue(allowed(7, 5))
        self.assertFalse(allowed(8, 0)); self.assertFalse(allowed(0, 6))
    def test_null_is_free(self):
        m = Model()
        m.launch(source=False); m.launch(target=False)
        self.assertEqual((m.window, m.created, m.attempts), (-1, 0, 0))
        self.assertFalse(m.timer)
    def test_boundary_burst_and_one_second_recycle(self):
        m = Model(); m.now = .90
        for _ in range(RATE): m.launch(.03)
        m.tick(); self.assertEqual(len(m.cooling), RATE)
        m.now = 1.01
        for _ in range(RATE): m.launch(.03)
        m.tick(); self.assertEqual((m.attempts, len(m.cooling)), (12, 12))
        self.assertFalse(m.timer); self.assertEqual(m.effects, 0)
        m.now = 1.89; m.tick(); self.assertEqual(len(m.cooling), 12)
        m.now = 2.05; m.tick(); self.assertFalse(m.cooling)
    def test_null_effect_still_bounded_and_finishes(self):
        m = Model()
        for _ in range(1000): m.launch(.03, effect=False)
        self.assertEqual((m.attempts, m.effects), (RATE, 0))
        m.tick()
        self.assertEqual((m.destroyed, m.created), (RATE, RATE))
        self.assertFalse(m.timer)
    def test_repeated_resets_do_not_refund(self):
        m = Model()
        for _ in range(20):
            m.launch(); m.epoch += 1; m.tick()
            self.assertFalse(m.arrows); self.assertFalse(m.timer)
        self.assertEqual((m.attempts, m.destroyed), (RATE, RATE))
        m.now = 1.; m.launch(); self.assertEqual(len(m.arrows), 1)
    def test_duration_edges_and_settlement_are_visual_independent(self):
        for duration in (-1., 0., .001, .03, .1, 10.):
            for effect in (True, False):
                m = Model(); shots = [(i, duration, 100.) for i in range(1000)]
                expected = list(shots)
                for _, flight, _ in shots: m.launch(flight, effect=effect)
                self.assertEqual(shots, expected)
                self.assertEqual(sum(damage for _, _, damage in shots), 100000.)
                for _ in range(335): m.tick()
                self.assertFalse(m.arrows); self.assertFalse(m.timer)
                self.assertEqual(m.effects, 0)

if __name__ == '__main__': unittest.main(verbosity=2)
