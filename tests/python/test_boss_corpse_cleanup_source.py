"""Narrow source contracts; runtime/compiled checks are separate gates."""
from pathlib import Path
import re
import struct
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BossCorpseCleanupSourceTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / 'wurst/TDGame.wurst').read_text()

    def body(self, name):
        return re.search(r'(?:public )?function ' + name +
                         r'\([^\n]*\n(.*?)(?=\n(?:public )?function |\Z)',
                         self.source, re.S).group(1)

    def test_cleanup_is_boss_only_one_shot_and_retains_unit(self):
        body = self.body('tdScheduleBossCorpseCleanup')
        self.assertIn('not tdIsBossUnitTypeId(originalType) or not tdEnemyBelongsToCurrentMatch(enemy)', body)
        self.assertEqual(body.count('doAfter('), 1)
        self.assertNotIn('doPeriodically', body)
        self.assertNotIn('getHandleId', body)
        self.assertIn('identity = enemy.getUserData() div 100', body)
        self.assertIn('GetUnitTypeId(enemy), identity, enemy.getUserData() div 100, enemy.isAlive()', body)
        self.assertIn('\n\t\t\tenemy.remove()', body)
        self.assertNotIn('tdIsGameOver()', body)
        self.assertNotIn('tdFlowEpoch()', body)

    def test_schedule_precedes_all_settlement_early_exits(self):
        body = self.body('tdHandleEnemyDeath')
        self.assertEqual(body.count('tdScheduleBossCorpseCleanup(enemy)'), 1)
        self.assertLess(body.index('tdScheduleBossCorpseCleanup(enemy)'), body.index('tdPetIsWild(enemy)'))
        self.assertLess(body.index('tdScheduleBossCorpseCleanup(enemy)'), body.index('tdClaimEnemyKill(enemy)'))
        self.assertNotIn('enemy.remove()', body)
        # Existing consumers continue to use the unit synchronously, in order.
        self.assertLess(body.index('tdPetHeroForgetEnemy(enemy, true)'), body.index('tdHandlePureBossLoot'))
        self.assertLess(body.index('tdHandlePureBossLoot'), body.rindex('tdForgetEnemyMatch(enemy)'))

    def test_predicate_excludes_removed_revived_changed_and_nonboss(self):
        body = self.body('tdBossCorpseCanRemove')
        self.assertIn('tdIsBossUnitTypeId(originalType)', body)
        self.assertIn('currentType == originalType', body)
        self.assertIn('originalIdentity == currentIdentity', body)
        self.assertIn('not alive', body)

    def test_original_asset_deaths_fit_delay(self):
        self.assertIn('return 3.0', self.body('tdBossCorpseCleanupDelay'))
        for name in ('RiftwindHunter', 'EclipseSpellweaver', 'UncrownedAbyssKing'):
            data = (ROOT / 'imports/war3mapImported' / (name + '.mdx')).read_bytes()
            offset, deaths = 4, []
            while offset < len(data):
                tag, size = struct.unpack_from('<4sI', data, offset)
                chunk = data[offset + 8:offset + 8 + size]
                offset += 8 + size
                if tag == b'SEQS':
                    for i in range(0, size, 132):
                        if chunk[i:i + 80].split(b'\0')[0].lower() == b'death':
                            start, end = struct.unpack_from('<II', chunk, i + 80)
                            deaths.append((end - start) / 1000)
            self.assertEqual(deaths, [2.0], name)


if __name__ == '__main__':
    unittest.main()
