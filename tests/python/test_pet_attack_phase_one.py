"""Actual production scalar functions/source wiring plus native critical mutations.
No test claims the pending Wurst build, gameplay or FPS has passed.
"""
from copy import deepcopy
from pathlib import Path
import re
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources
from VerifyPetManagerSource import scalar_helpers, compile_source_helper, source
from VerifyPetUIArtifact import phase_one_catalog, four_slot_allowed
from VerifyPetAttackArtifact import verify_native_critical_catalog
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTowerPlacementArtifact import unit_objects
from python_check_inputs import candidate_map

class PetAttackPhaseOneSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules=SourceScalarEvaluator(read_sources())

    def test_seven_attack_passive_values_and_exact_eligibility_boundaries(self):
        expected={5:[.06]*4,6:[2,4,6,8],7:[.40,.55,.70,.85],8:[.20,.30,.40,.50],16:[.10,.15,.20,.25],17:[1.5,1.7,1.9,2.1],18:[.12,.18,.24,.30]}
        for skill,values in expected.items():
            for quality,value in enumerate(values,1):
                self.assertAlmostEqual(self.rules.call('tdPetSkillPower',[skill,quality]),value)
        for life, pursuit, heavy in [(30.,True,False),(30.001,False,False),(65.,False,False),(65.001,False,True)]:
            self.assertEqual(self.rules.call('tdPetPursuitEligible',[life,100.]),pursuit)
            self.assertEqual(self.rules.call('tdPetHeavyEligible',[life,100.]),heavy)

    def test_full_integer_owned_ids_and_defined_stage_one_pool(self):
        n=phase_one_catalog()
        self.assertEqual([i for i in range(n['TD_PET_SKILL_COUNT']) if n['tdPetSkillDefined'](i)], [*range(4),*range(5,9),11,12,*range(16,49)])
        for skill,values in [(32,[0,16,32,40]),(40,[0,16,32,40]),(0,[32,33,34,35])]:
            self.assertEqual(n['tdPetSkillOwned'](skill,*values),skill in values)
        for skill in range(-1,45):
            for slot in range(-1,5):
                self.assertFalse(n['tdPetSkillAllowed'](skill,slot,True,False))
                self.assertEqual(n['tdPetSkillAllowed'](skill,slot,False,False),four_slot_allowed(skill,slot))
        state=source('TDPetState')
        self.assertNotIn('BitSet',state)
        self.assertNotIn('usedSkills',state)
        self.assertIn('return tdPetSkillOwned(skill,',state)
        self.assertIn('TD_PET_SKILL_COUNT - 1',state)

    def test_compact_legal_ui_count_derived_from_production_definitions(self):
        n=phase_one_catalog();count=n['TD_PET_SKILL_COUNT'];empty=n['TD_PET_SLOT_EMPTY']
        slots=[(slot,variant) for slot in range(4) for variant in range(empty+1) if variant==empty or (n['tdPetSkillAllowed'](variant%count,slot,False,False) and (variant<count or slot>=2))]
        self.assertEqual(len(slots),93)
        self.assertEqual(len([i for i in range(count) if n['tdPetSkillDefined'](i)])*2,86)
        objects=source('TDPetObjectGen')
        self.assertIn('setLevels(empty ? 1 : 4)',objects)
        self.assertIn('tdPetSkillAllowed(skill, slot, false, false)',objects)
        self.assertNotIn('for variant = 0 to 128',objects)
        self.assertNotIn('for skill = 0 to 15',objects)

    def test_rawcodes_full_three_hex_capacity_and_no_runtime_strings(self):
        n=scalar_helpers();compile_source_helper(source('TDPetData'),'tdPetWildUnitId',n,2)
        for index in range(4096):
            self.assertEqual(n['tdPetHex3Rawcode'](int.from_bytes(b'L000','big'),index,4096),int.from_bytes(f'L{index:03X}'.encode(),'big'))
        for index,limit in [(-1,4096),(4096,4096),(0,4097)]:self.assertEqual(n['tdPetHex3Rawcode'](int.from_bytes(b'L000','big'),index,limit),0)
        for wave in range(1,33):
            for species in range(1,4):self.assertEqual(n['tdPetWildUnitId'](wave,species),int.from_bytes(f'p{wave:02X}{species}'.encode(),'big'))
        self.assertNotIn('SubString',source('TDPetData'))
        self.assertNotIn('fromRawCode',source('TDPetData').replace('// Runtime string.fromRawCode scans CHARMAP four times per ID during UI startup.',''))

    def test_one_early_sampler_and_immutable_derived_basis(self):
        combat=source('TDPetCombat')
        self.assertEqual(combat.count('DamageEvent.addUnreducedListener(3)'),1)
        self.assertEqual(combat.count('DamageEvent.addListener(3)'),1)
        self.assertEqual(combat.count('DamageEvent.getUnreducedOriginalAmount()'),2)
        sample=combat.index('let base = DamageEvent.getUnreducedOriginalAmount()')
        decisive=combat.index('DamageEvent.setAmount(DamageEvent.getAmount() * resolve)')
        for phrase in ('let preLife = target.getLife()','tdPetNextAttackCount(pet.rotation, 4)','tdCaptureEquipmentTrialAoe(pet.lane, context)','tdPetProcReady('):
            self.assertLess(combat.index(phrase,sample),decisive)
        tower=(ROOT/'wurst/towers/TDTowerRuntime.wurst').read_text()
        self.assertIn('let attackDamage = DamageEvent.getUnreducedOriginalAmount()',tower)
        self.assertNotIn('let attackDamage = DamageEvent.getUnreducedAmount()',tower)
        self.assertIn('setNextDamageFromCode()',source('TDPetCombatSource'))
        self.assertIn('setNextDamageId(TD_PET_DAMAGE_ID)',source('TDPetCombatSource'))

    def test_original_phase_fence_and_gate_models_actual_library_timer(self):
        combat=source('TDPetCombat')
        self.assertIn('tdPetQueueAttack(pet castTo int)',combat)
        self.assertNotIn('doAfter(0.01)',combat)
        self.assertNotIn('doAfter(0.0)',combat)
        from VerifyPetAttackArtifact import verify_phase_fence_source
        self.assertTrue(verify_phase_fence_source())
        changed=read_sources();changed['pets/TDPetCombat.wurst']+='\nfunction bad()\n\tDamageEvent.abortCurrent()\n'
        with self.assertRaisesRegex(ValueError,'abort'):
            verify_phase_fence_source(changed)
        # Check that the exact packed library's zero-post is scheduled and driven,
        # rather than directly calling onDamage before deferred pet callbacks.
        from VerifyPetAttackArtifact import PetAttackRuntime
        from VerifyEquipmentCombatReplay import EquipmentTrialRuntime
        class TimerBoundaryRuntime(PetAttackRuntime):
            def __init__(self,script):
                EquipmentTrialRuntime.__init__(self,script)
                self.roll=.99;self.emitted=[];self.visible_units=[]
                self.timer_trace=[];self.pumping_zero=False;self.auto_post=True
                self.initialize_match()
                self.timer_trace.clear()
                self.units[102].update(life=1000.,maxLife=1000.,abilities={})
        script=Mpq(candidate_map().read_bytes()).extract('war3map.j').decode()
        r=TimerBoundaryRuntime(script);event=r.emit(100.)
        self.assertEqual(event['life'],900.)
        self.assertEqual(r.calls['DamageEvent_onDamage'],1)
        self.assertEqual(r.timer_trace[0][:2],('schedule',0.))
        self.assertEqual(r.timer_trace[1],('run',r.timer_trace[0][2]))
        self.assertFalse(r.scheduled)

    def test_no_pet_aura_scan_and_target_local_independent_debuff_sources(self):
        aura=(ROOT/'wurst/auras/TDAuraRuntime.wurst').read_text()
        for identity in ('TD_AURA_PET_COMMAND','TD_AURA_PET_STASIS'):
            self.assertNotIn('aggregate.offer('+identity,aura)
        combat=source('TDPetCombat');self.assertIn('var speed = 0.0',combat)
        attack=source('TDPetAttackState')
        for phrase in ('constant Table targetIndex','record.sources','entry.armorUntil = now + 3.0','armor = RMaxBJ(armor, entry.armor)','pet.generation == generation','tdEnemySlowRemoveTimed(target, source, TD_AURA_PET_REDUCE)'):
            self.assertIn(phrase,attack)
        self.assertNotIn('enumUnitsIn',attack)
        self.assertIn('tdIsBossUnitTypeId(GetUnitTypeId(target)) ? 0.5 : 1.0',attack)
        for hit in range(1,7):self.assertEqual(self.rules.call('tdPetReduceStacks',[hit-1,3.,0.]),min(5,hit))
        self.assertEqual(self.rules.call('tdPetReduceStacks',[5,3.,3.]),1)

    def test_native_critical_positive_and_unknown_chance_mutation(self):
        artifact=Mpq(candidate_map().read_bytes())
        abilities=ability_objects(artifact.extract('war3map.w3a'));units=unit_objects(artifact.extract('war3map.w3u'))
        self.assertEqual(verify_native_critical_catalog(abilities,units,abilities),['A102','A112'])
        changed=dict(abilities);changed['s000']=(abilities['s000'][0],dict(abilities['s000'][1]));key=next(key for key in changed['s000'][1] if key[0]=='Ocr1')
        changed['s000'][1][key]=(1,1.)
        units=dict(units);units['uG6B']=dict(units['uG6B']);units['uG6B']['uabi']+=',s000'
        with self.assertRaisesRegex(ValueError,'Unclassified mounted native critical'):
            verify_native_critical_catalog(changed,units)

    def test_packed_math_initialization_and_dead_field_fail_closed(self):
        from VerifyPetAttackArtifact import PetAttackRuntime
        script=Mpq(candidate_map().read_bytes()).extract('war3map.j').decode()
        r=PetAttackRuntime(script)
        self.assertEqual(r.invoke('tdEffectiveDamage',40.,10000.),40.)
        # Reproduce the formerly omitted actual init_Real, without replacing min.
        r.globals['Real_REAL_MAX']=0.
        self.assertEqual(r.invoke('tdEffectiveDamage',40.,10000.),0.)
        self.assertNotIn('DamageInstance_unreducedAmount',r.globals)
        broken=script+'\nfunction DamageEvent_getUnreducedAmount takes nothing returns real\nreturn 0.\nendfunction\n'
        with self.assertRaisesRegex(ValueError,'Live unreduced getter'):
            PetAttackRuntime(broken).emit(100.)

class FinalPetAttackArtifactTests(unittest.TestCase):
    """Explicit final-map fixtures and fail-closed adapter negatives.

    The full damage/fence/trial gate remains VerifyPetAttackArtifact.py; these
    tests isolate the changed fixture and packed-DCE boundaries.
    """
    @classmethod
    def setUpClass(cls):
        cls.artifact=Mpq(candidate_map().read_bytes())
        cls.script=cls.artifact.extract('war3map.j').decode()
        cls.abilities=ability_objects(cls.artifact.extract('war3map.w3a'))

    def test_actual_four_fixed_roles_and_exact_element_quality(self):
        from VerifyPetAttackArtifact import PetAttackRuntime
        r=PetAttackRuntime(self.script)
        self.assertTrue(r.final_catalog,'Supply the final 49-bound/43-defined candidate')
        pet=r.pet([(16,4),(7,4)])
        self.assertEqual([r.invoke('TDPet_skillAt',pet,i) for i in range(4)],[0,16,7,-1])
        self.assertEqual([r.invoke('TDPet_qualityAt',pet,i) for i in range(4)],[1,4,4,0])
        elemental=r.pet([(38,4)],host=101)
        self.assertEqual(r.globals['TDPet_species'][elemental],13)
        self.assertTrue(r.four_slot_contract,'Supply a candidate with the four-role slot contract')
        self.assertEqual(r.invoke('TDPet_skillAt',elemental,3),38)
        for invalid in ([(14,4)],[(4,1)],[(38,1)],[(16,1),(7,1),(17,1)],[(39,1),(48,1)]):
            with self.subTest(invalid=invalid),self.assertRaisesRegex(ValueError,'fixture|Fixture'):
                PetAttackRuntime(self.script).pet(invalid)

    def test_actual_math_init_and_missing_live_DCE_field_fail_closed(self):
        from VerifyPetAttackArtifact import PetAttackRuntime
        r=PetAttackRuntime(self.script)
        self.assertEqual(r.invoke('tdEffectiveDamage',40.,10000.),40.)
        r.globals['Real_REAL_MAX']=0.
        self.assertEqual(r.invoke('tdEffectiveDamage',40.,10000.),0.)
        self.assertNotIn('DamageInstance_unreducedAmount',r.globals)
        self.assertNotIn('DamageEvent_getUnreducedAmount',r.functions)
        broken=self.script+'\nfunction DamageEvent_getUnreducedAmount takes nothing returns real\nreturn 0.\nendfunction\n'
        with self.assertRaisesRegex(ValueError,'Live unreduced getter'):
            PetAttackRuntime(broken).emit(100.)

    def test_final_corpse_settlement_requires_actual_packed_owner(self):
        from VerifyPetAttackArtifact import verify_post_timer_order
        self.assertIn('function tdPetHeroOnCorpseExplosionSettled takes',self.script)
        broken,count=re.subn(r'(?m)^function tdPetHeroOnCorpseExplosionSettled takes[^\n]*\n.*?^endfunction\n','',self.script,flags=re.S)
        self.assertEqual(count,1)
        with self.assertRaisesRegex(ValueError,'Neither reviewed corpse-settlement'):
            verify_post_timer_order(broken)
        broken=self.script.replace('call tdPetHeroOnCorpseExplosionSettled(', 'call missingPetSettlement(')
        with self.assertRaisesRegex(ValueError,'actual production post branch'):
            verify_post_timer_order(broken)

    def test_actual_split_rejects_mutated_current_D_basis(self):
        from VerifyDamageRankingJass import functions
        from VerifyPetAttackArtifact import verify_split_original_basis
        bodies=[v[4] for v in functions(self.script).values()
                if 'DamageEvent_getUnreducedOriginalAmount()' in v[4] and 'TDArcherSplitArrowVolley' in v[4]]
        self.assertEqual(len(bodies),1)
        body=bodies[0]
        self.assertEqual(body.count('DamageEvent_getUnreducedOriginalAmount()'),1)
        broken=self.script.replace(body,body.replace('DamageEvent_getUnreducedOriginalAmount()','DamageEvent_getAmount()'),1)
        with self.assertRaisesRegex(ValueError,'Split immutable originalD'):
            verify_split_original_basis(broken)

    def test_exact_final_slot_titles_and_native_critical_mutation(self):
        from VerifyPetUIArtifact import verify_phase_one_slots
        self.assertEqual(verify_phase_one_slots(self.abilities),131)
        changed=deepcopy(self.abilities)
        key=next(k for k in changed['s00B'][1] if k[0]=='atp1' and k[1]==1)
        changed['s00B'][1][key]=(3,'|cffffffff白|r 疾风祝福')
        with self.assertRaisesRegex(ValueError,'quality/identity tooltip'):
            verify_phase_one_slots(changed)
        units=unit_objects(self.artifact.extract('war3map.w3u'))
        self.assertEqual(verify_native_critical_catalog(self.abilities,units,self.abilities),['A102','A112'])
        changed=deepcopy(self.abilities)
        key=next(k for k in changed['s110'][1] if k[0]=='Ocr1' and k[1]==1)
        changed['s110'][1][key]=(1,1.)
        units=deepcopy(units);units['uG6B']['uabi']+=',s110'
        with self.assertRaisesRegex(ValueError,'Unclassified mounted native critical'):
            verify_native_critical_catalog(changed,units)

if __name__=='__main__':unittest.main()
