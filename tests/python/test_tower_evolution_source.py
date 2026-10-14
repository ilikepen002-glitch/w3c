"""Source ownership/lifecycle negative mutants; no compiler or stale-map PASS."""
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import VerifyTowerEvolutionSource as v
from VerifyActiveCooldownContract import read_sources

class EvolutionSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.sources = read_sources()
    def test_current_source_contract(self): v.verify_source(sources=self.sources)
    def reject(self, path, old, new, message):
        sources = self.sources.copy()
        self.assertIn(old, sources[path])
        sources[path] = sources[path].replace(old, new, 1)
        with self.assertRaisesRegex(ValueError, message): v.verify_source(sources=sources)
    def test_reject_automatic_refresh_claim(self):
        self.reject(v.RUNTIME, 'let record = tdEvolutionRecord(tower)\n\tlet lane',
                    'let record = tdEvolutionRecord(tower)\n\ttdEvolutionLane(0).tryClaim(6, true, false, false)\n\tlet lane',
                    'Only the confirmation')
    def test_reject_duplicate_spending(self):
        self.reject(v.STATE, 'not qualified or spent or working', 'not qualified or working', 'Claim admission')
    def test_reject_preview_guard_bypasses(self):
        for guard in ('ticket.nonce != nonce', 'ticket.epoch != tdFlowEpoch()',
                      'record.identity != ticket.identity', 'record.workGeneration != ticket.workGeneration',
                      'GetUnitTypeId(tower) != ticket.rawcode', 'GetPlayerId(actor) != lane'):
            with self.subTest(guard=guard):
                self.reject(v.RUNTIME, guard, 'false', 'Confirmation lost guard|Cancellation lost nonce guard')
    def test_reject_paid_state_after_ui_destruction(self):
        self.reject(v.RUNTIME, 'record.evolved = true\n\tdestroy ticket',
                    'destroy ticket\n\trecord.evolved = true', 'writes must precede')
    def test_reject_reuse_of_retired_wage_rawcode(self):
        self.reject('towers/TDTowerCatalogData.wurst', "TD_TOWER_EVOLUTION_CHOOSE_ABILITY_ID = 'AeEC'",
                    "TD_TOWER_EVOLUTION_CHOOSE_ABILITY_ID = 'A109'", 'reuse retired wage')
    def test_reject_evolution_overwriting_orc_skill_hotkey(self):
        self.reject('towers/TDTowerObjectGen.wurst', '..presetHotkey("R")', '..presetHotkey("E")', 'preserve combat hotkeys')
    def test_reject_nonce_reset_reusing_old_match_authority(self):
        self.reject(v.RUNTIME, 'public function tdEvolutionResetForNewMatch()\n',
                    'public function tdEvolutionResetForNewMatch()\n\ttdEvolutionNonce = 0\n', 'cannot reset')
    def test_reject_missing_new_match_reset(self):
        self.reject('TDInit.wurst', 'tdEvolutionResetForNewMatch()', 'unrelatedReset()', 'not in list|substring not found')
    def test_reject_global_wave_qualification(self):
        self.reject(v.RUNTIME, '.creditWave(wave, tdEvolutionLaneCanChoose(lane)',
                    '.creditWave(tdGetGlobalWave(), tdEvolutionLaneCanChoose(lane)', 'original formally settled')
    def test_reject_cancel_new_preview_from_stale_callback(self):
        self.reject(v.RUNTIME, 'ticket.nonce != nonce', 'ticket.nonce < nonce', 'Confirmation lost guard|Cancellation lost nonce guard')

if __name__ == '__main__': unittest.main(verbosity=2)
