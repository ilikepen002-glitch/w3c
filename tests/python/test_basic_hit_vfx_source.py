"""Narrow production resource and bounded ownership contracts; no engine claims."""
from pathlib import Path
import hashlib
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'assets/source/basic-hit-vfx'

class BasicHitVfxSourceTests(unittest.TestCase):
    def test_exported_meshes_are_live_imports_with_complete_fade(self):
        report = json.loads((ASSETS / 'validation-frames.json').read_text())
        self.assertEqual(len(report['models']), 5)
        data = (ROOT / 'wurst/visuals/TDCombatVisualData.wurst').read_text()
        expected = {'GoldCrescent': (184,180), 'WoodThorns': (80,280),
                    'WaterShards': (96,260), 'FireCrown': (96,230), 'EarthFault': (88,280)}
        for model in report['models']:
            name = model['name']
            self.assertEqual((model['triangles'], model['lifetimeMs']), expected[name.removeprefix('TDPetHit')])
            self.assertEqual((model['materials'],model['bones'],model['particleEmitters'],model['ribbons']), (2,1,0,0))
            payload = (ROOT / 'imports/war3mapImported' / (name+'.mdx')).read_bytes()
            self.assertEqual(payload, (ASSETS / 'output' / (name+'.mdx')).read_bytes())
            self.assertEqual(hashlib.sha256(payload).hexdigest(), model['sha256'])
            self.assertIn(name+'.mdx', data)
            self.assertEqual(model['texture'], 'Textures\\TDPetVfxAtlas.blp')
            for frame in model['frames']:
                if frame['time'] <= 50:
                    self.assertEqual(frame['alpha'], [1,1])
                if frame['time'] >= model['lifetimeMs']:
                    self.assertEqual(frame['alpha'], [0,0])
        self.assertEqual(hashlib.sha256((ROOT/'imports/Textures/TDPetVfxAtlas.blp').read_bytes()).hexdigest(),report['atlasSha256'])

    def test_finisher_never_replaces_creates_or_extends(self):
        source = (ROOT/'wurst/visuals/TDCombatVisualRuntime.wurst').read_text()
        finisher = source.split('public function tdCombatVisualFinisher',1)[1].split('public function tdCombatVisualRefreshGear',1)[0]
        self.assertNotIn('AddSpecialEffect',finisher)
        self.assertNotIn('DestroyEffect',finisher)
        self.assertNotIn('expiresAt',finisher)
        self.assertNotIn('creationCount',finisher)
        self.assertEqual(finisher.split('\n',1)[1].strip(),'return')

    def test_existing_admission_caps(self):
        source=(ROOT/'wurst/visuals/TDCombatVisualData.wurst').read_text()
        for key,value in [('SHORT_LIMIT',128),('HIT_LIMIT',32),('NEW_PER_SECOND',120),('MOVING_LIMIT',8)]:
            self.assertRegex(source, rf'TD_VISUAL_{key} = {value}\b')
        self.assertIn('sourceCount < 2',source)
        self.assertIn('laneGroups < TD_VISUAL_LANE_GROUPS_PER_SECOND',source)

    def test_possession_keeps_native_attack_art_and_skill_effects(self):
        combat=(ROOT/'wurst/pets/TDPetCombat.wurst').read_text()
        # The legacy elemental renderer remains available, but no production
        # caller may decorate a basic hit with it (including its gold beam).
        for path in (ROOT/'wurst').rglob('*.wurst'):
            source=path.read_text()
            calls=re.sub(r'public function tdCombatVisualHit\([^\n]*', '', source)
            self.assertNotIn('tdCombatVisualHit(', calls, str(path))
        # Visual removal must not bypass the decisive multiplier, queued damage,
        # hero passives, active spells, buff feedback, or companion cast motion.
        for entry in (
            'DamageEvent.setAmount(DamageEvent.getAmount() * resolve)',
            'pet.resolveRotation = tdPetNextAttackCount(pet.resolveRotation, 5)',
            'tdPetApplyAttackDebuffs(', 'tdPetHeroCapturePrimary(',
            'tdPetQueueAttack(', 'tdPetStartElementActive(',
            'tdCombatVisualStartPetBuff(', 'tdPetDisplayCast(',
        ):
            self.assertIn(entry, combat)
        for passive in ('comboSnapshot', 'chargeSnapshot', 'pursuitSnapshot', 'heavySnapshot'):
            self.assertIn('tdPetDamage(pet, host, generation, target, base * ' + passive + ')', combat)
        towers=(ROOT/'wurst/towers/TDTowerRuntime.wurst').read_text()
        self.assertIn('tdLaunchArcherSplitArrowVisual(source, shot.target, shot.flightTime)', towers)
        objects=(ROOT/'wurst/towers/TDTowerObjectGen.wurst').read_text()
        self.assertIn('setAttack1ProjectileArt(tdTowerProjectileArt(towerChoice))', objects)

if __name__ == '__main__':
    unittest.main()
