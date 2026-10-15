"""Replay actual startup ownership source with bounded native stubs, not gameplay."""
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from test_elemental_pet_runtime_source import compile_body

ROOT = Path(__file__).resolve().parents[2]


class AmbientCritterTests(unittest.TestCase):
    def test_precise_once_only_ownership_and_group_cleanup(self):
        text = (ROOT / 'wurst/TDAmbientCritters.wurst').read_text()
        units = [SimpleNamespace(owner=owner, raw=raw) for owner in range(16)
                 for raw in ('nech', 'nshe', 'nfro', 'npig', 'hfoo', 'hT01', 'nP01', 'hpea')]
        enumerations, destroyed, changed, ghosted = [], [], [], []
        def enumerate_player(group, player, predicate):
            self.assertIsNone(predicate)
            enumerations.append(player)
            group.extend(u for u in units if u.owner == player)
        def change_owner(unit, owner, color):
            changed.append((unit.raw, unit.owner, owner, color))
            unit.owner = owner
        env = dict(tdAmbientCritterOwnershipReady=False, CreateGroup=list,
                   Player=lambda p: p, PLAYER_NEUTRAL_PASSIVE=15,
                   GroupEnumUnitsOfPlayer=enumerate_player,
                   FirstOfGroup=lambda g: g[0] if g else None,
                   GroupRemoveUnit=lambda g, u: g.remove(u),
                   GetPlayerId=lambda p: p, GetOwningPlayer=lambda u: u.owner,
                   GetUnitTypeId=lambda u: int.from_bytes(u.raw.encode(), "big"), SetUnitOwner=change_owner,
                   DestroyGroup=lambda g: destroyed.append(list(g)),
                   UnitAddAbility=lambda u, ability: ghosted.append((u.raw, u.owner, ability)))
        compile_body(text, 'tdShouldNeutralizeAmbientCritter', env)
        setup = compile_body(text, 'tdSetupAmbientCritterOwnership', env,
                             ('tdAmbientCritterOwnershipReady',))
        for _ in range(3):
            setup()
        self.assertEqual(enumerations, [0])
        self.assertEqual(destroyed, [[]])
        self.assertEqual(changed, [(raw, 0, 15, True) for raw in ('nech', 'nshe', 'nfro', 'npig')])
        self.assertEqual(sum(u.owner == 0 for u in units), 4)
        self.assertEqual(ghosted, [(raw, 15, int.from_bytes(b"Aeth", "big"))
                                   for raw in ("nech", "nshe", "nfro", "npig")])
        # Preserve native Wander/terrain movement and targeting; no Locust,
        # invisible Ghost, unit removal, or global terrain/pathing changes.
        for forbidden in ("Aloc", "Agho", "SetUnitPathing", "SetTerrainPathable",
                          "RemoveUnit", "PauseUnit", "UnitRemoveAbility"):
            self.assertNotRegex(text, r"\b" + forbidden + r"\b")

    def test_startup_runs_before_gameplay_and_never_on_reset(self):
        init = (ROOT / 'wurst/TDInit.wurst').read_text()
        self.assertEqual(init.count('tdSetupAmbientCritterOwnership()'), 1)
        self.assertLess(init.index('tdSetupAmbientCritterOwnership()'), init.index('tdCreatePads()'))
        for path in (ROOT / 'wurst').rglob('*.wurst'):
            if path.name != 'TDAmbientCritters.wurst':
                self.assertNotIn('tdAmbientCritterOwnershipReady =', path.read_text())

    def test_editor_source_has_exactly_the_expected_player_zero_critters(self):
        from GenerateTowerTerrainMask import Mpq
        script = Mpq((ROOT / 'maps/ExampleMap.source.w3x').read_bytes()).extract('war3map.j').decode()
        from collections import Counter
        section = script.split('function CreateUnitsForPlayer0 takes')[1].split('endfunction')[0]
        counts = Counter(re.findall(r"CreateUnit\(\s*p,\s*'(nech|nshe|nfro|npig)'", section))
        self.assertEqual(counts, dict(nech=4, nshe=11, nfro=2, npig=4))
        self.assertRegex(section, r'local player p\s*=\s*Player\(0\)')


if __name__ == '__main__':
    unittest.main()
