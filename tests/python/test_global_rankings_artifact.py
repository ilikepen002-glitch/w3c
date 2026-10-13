"""Fresh B regressions. Actual-map tests require the newly built B artifact."""
from copy import deepcopy
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile
import unittest
from python_check_inputs import candidate_map
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq, mpq_hash
from VerifySemanticIconArtifact import Field, Object
import VerifyDamageRankingJass as scalar
import VerifyGlobalRankingsArtifact as gate
from VerifyInheritedJassAliases import inherited_script_view

PLAYER = '''function tdDamagePlayerPrecedes takes real total, integer lane, real otherTotal, integer otherLane returns boolean
if total > otherTotal then
return true
endif
if total < otherTotal then
return false
endif
return lane < otherLane
endfunction
'''
TOWER = '''function tdDamageTowerPrecedes takes real total, integer lane, integer serial, real otherTotal, integer otherLane, integer otherSerial returns boolean
if total > otherTotal then
return true
endif
if total < otherTotal then
return false
endif
if lane < otherLane then
return true
endif
if lane > otherLane then
return false
endif
return serial < otherSerial
endfunction
'''
RANK = '''function tdDamagePlayerRank takes real total, integer lane, real total0, boolean p0, real total1, boolean p1, real total2, boolean p2, real total3, boolean p3 returns integer
local integer rank = 0
'''+''.join(f'''if p{i} then
if tdDamagePlayerPrecedes(total{i}, {i}, total, lane) then
set rank = rank + 1
endif
endif
''' for i in range(4))+'''return rank
endfunction
'''
SCRIPT = PLAYER + TOWER + RANK


def field(obj, name, value, level=0, column=0):
    kind = 3 if isinstance(value, str) else 0
    raw = name.encode() + struct.pack('<III', kind, level, column)
    raw += value.encode() + b'\0' if kind == 3 else struct.pack('<i', value)
    raw += obj.identity[4:]
    obj.fields[(name, level, column)] = Field((name, level, column), kind, value, raw)


def fixture():
    abilities = {key: Object(1, parent.encode() + key.encode(), {}) for key, parent in
                 [('A119', 'ANcl'), ('Dsta', 'ANcl'), ('Gupg', 'ANcl'), ('Geqb', 'Aspb')]}
    for slot, key in enumerate(('A119', 'Dsta', 'Gupg')):
        field(abilities[key], 'Ncl6', gate.ORDER_FACTORY[slot], 1, 6)
        field(abilities[key], 'alev', 1)
    field(abilities['Geqb'], 'spb1', 'A119,Gupg,Dsta', 1, 1)
    field(abilities['Geqb'], 'spb3', 3, 1, 3); field(abilities['Geqb'], 'spb4', 3, 1, 4)
    field(abilities['Geqb'], 'aub1', '合成、升级和伤害统计', 1)
    units = {'uA01': Object(1, b'hfoo' + b'uA01', {})}
    field(units['uA01'], 'uabi', 'Geqb')
    old = {'war3map.w3a': abilities, 'war3map.w3u': units}
    new = deepcopy(old); a = new['war3map.w3a']; del a['Dsta']
    field(a['Gupg'], 'Ncl6', gate.ORDER_FACTORY[1], 1, 6)
    field(a['Geqb'], 'spb1', 'A119,Gupg', 1, 1)
    field(a['Geqb'], 'spb3', 2, 1, 3); field(a['Geqb'], 'spb4', 2, 1, 4)
    field(a['Geqb'], 'aub1', gate.BOOK_TEXT, 1)
    return old, new


class ScalarTests(unittest.TestCase):
    def test_fractional_comparator_and_participation_matrix(self):
        self.assertEqual(scalar.verify_comparators(SCRIPT), 16000)
        self.assertEqual(scalar.verify_player_selection(SCRIPT), 8192)

    def test_fractions_are_not_truncated_and_large_rounding_is_binary32(self):
        p = scalar.ScalarProgram(SCRIPT)
        self.assertTrue(p.run(scalar.HELPERS[0], (.625, 3, .375, 0)))
        self.assertFalse(p.run(scalar.HELPERS[0], (.375, 0, .625, 3)))
        self.assertEqual(scalar.real32(16777217.0), 16777216.0)

    def test_wrong_total_lane_and_serial_are_rejected(self):
        for before, after in [('return lane < otherLane', 'return lane > otherLane'),
                              ('return serial < otherSerial', 'return serial > otherSerial'),
                              ('if total > otherTotal then', 'if total < otherTotal then')]:
            with self.subTest(before=before), self.assertRaisesRegex(ValueError, 'oracle mismatch'):
                scalar.verify_comparators(SCRIPT.replace(before, after))

    def test_old_boolean_grouping_and_integer_truncation_rejected(self):
        body = 'return total > otherTotal or total == otherTotal and lane < otherLane\n'
        mutant = SCRIPT.replace(PLAYER, PLAYER.split('\n', 1)[0] + '\n' + body + 'endfunction\n')
        with self.assertRaisesRegex(ValueError, 'explicit branches'): scalar.verify_comparators(mutant)
        with self.assertRaisesRegex(ValueError, 'signature changed'):
            scalar.verify_comparators(SCRIPT.replace('takes real total', 'takes integer total', 1))

    def test_wrong_participation_or_duplicate_rank_is_rejected(self):
        for rank in [RANK.replace('if p2 then', 'if p1 then'), RANK.replace('return rank', 'return 0')]:
            with self.subTest(rank=rank), self.assertRaises(ValueError):
                scalar.verify_player_selection(PLAYER + TOWER + rank)

    def test_native_call_global_read_and_write_rejected(self):
        for result in ('GetPlayerId()', 'tdGlobalFlag', 'rank'):
            with self.assertRaises(ValueError):
                scalar.verify_comparators(SCRIPT.replace('return lane < otherLane', 'return ' + result))
        with self.assertRaisesRegex(ValueError, 'Nonlocal scalar write'):
            scalar.verify_comparators(SCRIPT.replace('return lane < otherLane', 'set tdGlobalFlag = true\nreturn lane < otherLane'))


class DeltaTests(unittest.TestCase):
    def test_exact_removal_and_one_slot_compaction(self):
        old, new = fixture(); gate.verify_object_delta(new, old)

    def test_wrong_book_fields_and_unrelated_field_rejected(self):
        for name, value, level, col in [('spb1', 'A119,Gupg,Dsta', 1, 1), ('spb3', 3, 1, 3),
                                      ('spb4', 3, 1, 4), ('aub1', 'wrong', 1, 0), ('anam', 'changed', 0, 0)]:
            old, new = fixture(); field(new['war3map.w3a']['Geqb'], name, value, level, col)
            with self.subTest(name=name), self.assertRaises(ValueError): gate.verify_object_delta(new, old)

    def test_removed_ghost_parent_and_attachment_rejected(self):
        for rawcode in ('Dsta', 'Pmas', 'Pfor'):
            old, new = fixture(); field(new['war3map.w3u']['uA01'], 'uabi', 'Geqb,' + rawcode)
            with self.assertRaisesRegex(ValueError, 'removed ability'): gate.verify_object_delta(new, old)
            old, new = fixture(); new['war3map.w3u']['uA01'].identity = rawcode.encode() + b'uA01'
            with self.assertRaisesRegex(ValueError, 'removed ability'): gate.verify_object_delta(new, old)

    def test_arbitrary_unique_order_swap_is_not_legitimate_compaction(self):
        old, new = fixture()
        field(new['war3map.w3a']['A119'], 'Ncl6', gate.ORDER_FACTORY[1], 1, 6)
        field(new['war3map.w3a']['Gupg'], 'Ncl6', gate.ORDER_FACTORY[0], 1, 6)
        with self.assertRaisesRegex(ValueError, 'unjustified'): gate.verify_object_delta(new, old)

    def test_field_encoding_and_object_order_rejected(self):
        old, new = fixture(); obj = new['war3map.w3a']['Geqb']; key = ('spb3', 1, 3); item = obj.fields[key]
        obj.fields[key] = Field(key, item.kind, item.value, item.raw[:-4] + b'XXXX')
        with self.assertRaisesRegex(ValueError, 'encoding'): gate.verify_object_delta(new, old)
        old, new = fixture(); new['war3map.w3a'] = dict(reversed(list(new['war3map.w3a'].items())))
        with self.assertRaisesRegex(ValueError, 'set/order'): gate.verify_object_delta(new, old)


class ArchiveTests(unittest.TestCase):
    def test_unrelated_resource_set_or_bytes_rejected(self):
        class Stub:
            def extract(self, name): return b''
        before = {'war3map.w3a': ('war3map.w3a', b'old'), 'terrain': ('terrain', b'unchanged')}
        after = deepcopy(before)
        old, new = fixture()
        def validate(changed):
            with patch.object(gate, 'members', side_effect=[changed, before]), patch.object(gate, 'parse_objects', side_effect=[new['war3map.w3a'], old['war3map.w3a']]), patch.object(gate, 'verify_global_channel_orders'), patch.object(gate, 'ability_objects'):
                return gate.verify_archive_delta(Stub(), Stub())
        self.assertEqual(validate(after), 2)
        after['terrain'] = ('terrain', b'mutated')
        with self.assertRaisesRegex(ValueError, 'Unrelated resource'): validate(after)
        after = deepcopy(before); after['extra'] = ('extra', b'')
        with self.assertRaisesRegex(ValueError, 'resource set'): validate(after)

    def test_only_build_timestamp_may_change_in_map_info(self):
        def info(time, tail=b'fixed-tail'):
            text = lambda v: v.encode() + b'\0'
            name = '深渊守望 20261012-' + time + '-UTC+8'
            return (struct.pack('<III', 25, 7, 6060) + text(name) + text('author') +
                    text('description') + text('1-4') + bytes(65) + text('model') +
                    text('loading') + text(name) + tail)
        self.assertEqual(gate.normalize_info(info('0123')), gate.normalize_info(info('0234')))
        self.assertNotEqual(gate.normalize_info(info('0123')), gate.normalize_info(info('0123', b'mutated-tail')))
        with self.assertRaisesRegex(ValueError, 'timestamp'):
            gate.normalize_info(info('2460'))
        broken = info('0123').replace(('深渊守望 20261012-0123-UTC+8').encode(), ('深渊守望 20261012-0124-UTC+8').encode(), 1)
        with self.assertRaisesRegex(ValueError, 'timestamp'): gate.normalize_info(broken)

    def test_member_coverage_rejects_hidden_duplicate_alias_and_capture_icon(self):
        class Archive:
            def __init__(self, names):
                self.data = {n: b'x' for n in names}; self.data['(listfile)'] = '\n'.join(names).encode()
                self.blocks = [(0, 0, 0, 0x80000000)] * len(self.data)
                self.hashes = [(*[mpq_hash(n, i) for i in (1, 2)], 0, 0, k) for k, n in enumerate(self.data)]
            def has(self, name): return name in self.data
            def extract(self, name): return self.data[name]
        archive = Archive(['terrain']); self.assertEqual(len(gate.members(archive)), 2)
        archive.hashes.append(archive.hashes[0])
        with self.assertRaisesRegex(ValueError, 'Duplicate'): gate.members(archive)
        archive = Archive(['terrain']); archive.hashes.append((1, 2, 0, 0, 0))
        with self.assertRaisesRegex(ValueError, 'Unlisted'): gate.members(archive)
        with self.assertRaisesRegex(ValueError, 'alias'): gate.members(Archive(['terrain', 'Terrain']))
        with self.assertRaisesRegex(ValueError, 'capture icon'): gate.members(Archive(['war3mapImported\\BTNTDActionMasterCapture.blp']))


class SourceTests(unittest.TestCase):
    def test_source_contract_and_duplicate_player_mutation(self):
        from trial_formal72_fixture import Formal72SourceFixture
        frozen = Formal72SourceFixture(); self.addCleanup(frozen.cleanup)
        gate.verify_source(frozen.root)
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); shutil.copytree(frozen.root / 'wurst', root / 'wurst')
            p = root / 'wurst/damage/TDDamageHud.wurst'
            p.write_text(p.read_text().replace('tdDamageSetPlayerHud(ledger, 2, p0, p1, p2, p3)', 'tdDamageSetPlayerHud(ledger, 1, p0, p1, p2, p3)'))
            with self.assertRaisesRegex(ValueError, 'selected exactly once|Duplicate'): gate.verify_source(root)


class AliasProofTests(unittest.TestCase):
    def fixture(self):
        real = "function max_2 takes real a, real b returns real\nif a > b then\nreturn a\nendif\nreturn b\nendfunction\n"
        old = real.replace('max_2', 'max_2_1')
        return real, old

    def test_only_exact_math_identifier_is_rewritten(self):
        current, baseline = self.fixture()
        current += 'function unrelated takes nothing returns nothing\ncall max_2(0.58, 10000.)\ncall dispatch_Handler(828)\ncall BJDebugMsg("max_2 828")\nendfunction\n'
        view, mapping = inherited_script_view(current, baseline)
        self.assertEqual(mapping, {'max_2': 'max_2_1'})
        self.assertIn('call max_2_1(0.58, 10000.)', view)
        self.assertIn('call dispatch_Handler(828)', view)
        self.assertIn('"max_2 828"', view)

    def test_signature_body_and_alias_collision_mutations_rejected(self):
        current, baseline = self.fixture()
        for mutant in (current.replace('real a', 'integer a'), current.replace('return b', 'return a'),
                       current + baseline):
            with self.subTest(mutant=mutant), self.assertRaises(ValueError): inherited_script_view(mutant, baseline)


class ActualArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = Mpq((candidate_map()).read_bytes()).extract('war3map.j').decode('utf-8')

    def test_final_real_comparators(self): self.assertEqual(scalar.verify_comparators(self.script), 16000)
    def test_final_player_selection(self): self.assertEqual(scalar.verify_player_selection(self.script), 8192)
    def test_final_snapshot_lifecycle(self): gate.verify_packaged_structure(self.script)

    def test_final_timer_freeze_and_constants_mutations_rejected(self):
        callback = scalar.functions(self.script)['call_doPeriodically_TDHud']
        body = callback[4]
        for mutated in (body.replace('if tdIsGameOver() then', 'if false then'),
                        body.replace('call tdRefreshStatusBoard(', 'call obsolete_refresh(')):
            script = self.script[:callback.start(4)] + mutated + self.script[callback.end(4):]
            with self.assertRaisesRegex(ValueError, 'final refresh/timer stop'): gate.verify_packaged_structure(script)
        marker = re.search(r'\bset \w*TD_DAMAGE_HUD_ROWS = 16\b', self.script)
        self.assertIsNotNone(marker)
        mutated = self.script[:marker.start()] + marker[0].replace('16', '15') + self.script[marker.end():]
        with self.assertRaisesRegex(ValueError, 'constant changed'): gate.verify_packaged_structure(mutated)

    def test_final_wrong_tie_mutation_is_rejected(self):
        m = scalar.functions(self.script)['tdDamageTowerPrecedes']
        names = [p.strip().split()[1] for p in m[2].split(',')]
        old = names[2] + ' < ' + names[5]
        self.assertIn(old, m[4])
        mutant = self.script[:m.start(4)] + m[4].replace(old, old.replace(' < ', ' > ')) + self.script[m.end(4):]
        with self.assertRaisesRegex(ValueError, 'Tower comparator oracle mismatch'): scalar.verify_comparators(mutant)


if __name__ == '__main__': unittest.main()
