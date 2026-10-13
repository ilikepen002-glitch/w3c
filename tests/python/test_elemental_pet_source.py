"""Phase2 real-source catalogue/rawcodes/geometry/lifecycle contracts.
Source checks only: never claim Wurst types, compiled JASS or live control.
"""
from dataclasses import dataclass
import hashlib,json,math,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from VerifyActiveCooldownContract import SourceScalarEvaluator,read_sources,definitions
from VerifyPetManagerSource import scalar_helpers,source,function_body
from VerifyPetAttackArtifact import verify_phase_fence_source
@dataclass(frozen=True)
class Vec:
    x:float
    y:float
    def __add__(self,v):return Vec(self.x+v.x,self.y+v.y)
    def __sub__(self,v):return Vec(self.x-v.x,self.y-v.y)
    def __mul__(self,v):return Vec(self.x*v,self.y*v)
    def __truediv__(self,v):return Vec(self.x/v,self.y/v)
class GeometrySource(SourceScalarEvaluator):
    def __init__(self,sources):
        super().__init__(sources);self.tuples['vec2']=Vec
    def call(self,name,values,fields=None):
        if name=='SquareRoot':return math.sqrt(values[0])
        if name=='RAbsBJ':return abs(values[0])
        return super().call(name,values,fields)
class ElementalPetSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.sources=read_sources();cls.rules=GeometrySource(cls.sources)
    def test_forty_three_real_definitions_with_twenty_fixed_element_ids(self):
        r=self.rules
        actual=[i for i in range(50) if r.call('tdPetSkillDefined',[i])]
        self.assertEqual(actual,[*range(4),*range(5,9),11,12,*range(16,49)])
        self.assertEqual(r.call('tdPetSkillDefinitionCount',[]),43)
        active=definitions(r);pet=[d for d in active if d.petSkillId>=0]
        self.assertEqual(len(pet),22)
        self.assertEqual({d.petSkillId for d in pet},{11,12,*range(19,39)})
        for element in range(1,6):
            for quality in range(1,5):
                skill=r.call('tdPetElementSkill',[element,quality])
                self.assertEqual(skill,19+(element-1)*4+quality-1)
                self.assertEqual(r.call('tdPetSkillFixedQuality',[skill]),quality)
                self.assertEqual(r.call('tdActiveSkillDefinitionForPetSkill',[skill]).baseCooldown,[10,12,14,18][quality-1])
                for q in range(0,6):self.assertEqual(r.call('tdPetSkillQualityValid',[skill,q]),q==quality)
    def test_all_species_share_only_their_element_and_one_active_slot(self):
        r=self.rules
        for species in range(1,16):
            element=(species-1)//3+1
            self.assertEqual(r.call('tdPetSpeciesElement',[species]),element)
            for slot in range(4):
                actual=[s for s in range(50) if r.call('tdPetSkillAllowedForSpecies',[s,slot,species,False])]
                expected=([*range(4)], [*range(5,9),16,17,18], [*range(5,9),16,17,18,*range(39,49)], [11,12,*range(19+(element-1)*4,23+(element-1)*4)])[slot]
                self.assertEqual(actual,expected)
                for skill in actual:self.assertFalse(r.call('tdPetSkillAllowedForSpecies',[skill,slot,species,True]))
        for species in (-1,0,16,99):
            for slot in range(4):
                for skill in range(49):
                    self.assertFalse(r.call('tdPetSkillAllowedForSpecies',[skill,slot,species,False]))
        for q in range(1,5):
            for skill in (11,12):self.assertTrue(r.call('tdPetSkillQualityValid',[skill,q]))
    def test_full_four_byte_rawcodes_and_all_2410_collection_states(self):
        r=self.rules
        wild=set()
        for wave in range(1,33):
            for species in range(1,16):
                code=r.call('tdPetWildUnitId',[wave,species]);wild.add(code)
                self.assertEqual(code,int.from_bytes(f'p{wave:02X}{species:X}'.encode(),'big'))
                self.assertEqual(r.call('tdPetSpeciesForWildType',[code]),species)
        self.assertEqual(len(wild),480)
        for bad in ('p001','p011','p200','p21F','p01f','p0aF','P01F','p00F','p0/F','p7/F','p8?1','p8/F','p01/','p01?','p01a','pFFF'):
            # p001 is wave00; p011 is a deliberately valid control.
            expected=1 if bad=='p011' else 0
            self.assertEqual(r.call('tdPetSpeciesForWildType',[int.from_bytes(bad.encode(),'big')]),expected)
        ids=set()
        for cell in range(10):
            for variant in range(241):
                spec,q,n=(0,0,0) if variant==0 else ((variant-1)//16+1,((variant-1)%16)//4+1,(variant-1)%4+1)
                code=r.call('tdPetListAbilityId',[cell,spec,q,n]);ids.add(code)
                self.assertEqual(code,int.from_bytes(f'L{cell*241+variant:03X}'.encode(),'big'))
        self.assertEqual(len(ids),2410)
        self.assertEqual(max(ids),int.from_bytes(b'L969','big'))
        for species in (-1,0,16,99):self.assertEqual(r.call('tdPetVisualUnitId',[species]),0)
        self.assertEqual(len({r.call('tdPetDisplayUnitId',[s,q]) for s in range(1,16) for q in range(1,5)}),60)
    def test_real_line_fan_and_zero_vector_boundaries(self):
        r=self.rules;o=Vec(0,0);d=r.call('tdPetDirection',[o,Vec(100,0)])
        for point,valid in [(Vec(650,90),True),(Vec(650.01,0),False),(Vec(-.01,0),False),(Vec(10,90.01),False)]:
            self.assertEqual(r.call('tdPetLineContains',[o,d,point,650.,90.]),valid)
        for point,valid in [(Vec(100,100),True),(Vec(100,100.01),False),(Vec(-1,0),False),(Vec(500,0),True),(Vec(500.01,0),False)]:
            self.assertEqual(r.call('tdPetFanContains',[o,d,point,500.]),valid)
        self.assertEqual(r.call('tdPetDirection',[o,o]),Vec(1.,0.))
    def test_shared_control_and_cancellation_ownership_wiring(self):
        state=source('TDPetState');runtime=source('TDPetRuntime');scheduler=source('TDPetEffectScheduler')
        self.assertIn('tdPetCancelEffectTasks(this castTo int)',function_body(state,'invalidateCombat')[1])
        self.assertNotIn('doAfter(4.0)',runtime)
        self.assertLess(runtime.index('tdPetShutdownEffects()'),runtime.index('destroy pet',runtime.index('tdPetShutdownEffects()')))
        self.assertIn('if not tdPetCanDestroyMatchRecords()',runtime)
        self.assertIn('if tdPetPendingOriginal != 0',scheduler)
        self.assertLess(scheduler.index('tasks.remove(task)',scheduler.index('function tick')),scheduler.index('task.runEffect(',scheduler.index('function tick')))
        self.assertIn('task.schedulerTick == tickSerial',scheduler)
        self.assertTrue(verify_phase_fence_source())
        self.assertIn('tdTryEnemyControl(',self.sources['items/TDShieldRuntime.wurst'])
        self.assertIn('tdTryEnemyControlToken(',source('TDPetCastContext'))
        for path,body in self.sources.items():
            if path.startswith('pets/') and path not in ('pets/TDPetWild.wurst','pets/TDPetUIView.wurst','pets/TDPetUI.wurst','pets/TDPetRuntime.wurst','pets/TDPetCombat.wurst','pets/TDPetAttackQueue.wurst','pets/TDPetEffectScheduler.wurst'):
                self.assertNotIn('doPeriodically(',body,path);self.assertNotIn('doAfter(',body,path)
        self.assertNotIn('PauseUnit(',''.join(self.sources.values()))
    def test_stable_source_host_tag_and_single_extra_spell_factor(self):
        combat=source('TDPetCombatSource')
        self.assertEqual(combat.count('tdEnemyMechanicScaleSpellDamage(target, amount)'),1)
        for text in ('DamageEvent.setNextDamageFromCode()','DamageEvent.setNextDamageId(TD_PET_DAMAGE_ID)','host.damageTarget(target, amount)'):self.assertIn(text,combat)
        mechanism=self.sources['enemies/TDEnemyMechanicState.wurst']
        self.assertIn('1.0 - (1.0 - factor) * (1.0 - RMinBJ(0.20',mechanism)
        # Exercise actual production state method body through the scalar evaluator.
        methods=re.search(r'\tfunction scaledSpellAmount\(real amount, real weakening\) returns real\n(.*?)(?=\n\tfunction)',mechanism,re.S).group(1)
        src=dict(self.sources);src['test_method']='function stageFactor(real amount, real weakening, boolean active, int role, int wave) returns real\n'+methods
        ev=GeometrySource(src)
        for wave in (8,16,24,32):
            factor=ev.call('tdWaveBossSpellDamageTakenFactor',[wave])
            self.assertAlmostEqual(ev.call('stageFactor',[100.,.2,True,3,wave]),100*(1-(1-factor)*.8))
    def test_exact_final_model_imports_and_real_shape_identity(self):
        m=json.loads((ROOT/'assets/source/elemental-spirits/import-manifest.json').read_text())
        self.assertEqual(len(m['models']),15)
        hashes=set()
        for a in m['models']:
            for p,h in [('modelImportPath','modelSha256'),('requiredTextureImportPath','textureSha256')]:
                data=(ROOT/'imports'/a[p].replace('\\','/')).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(),a[h])
            hashes.add(a['modelSha256'])
        self.assertEqual(len(hashes),15)
        self.assertFalse(m['game127aTested'])
if __name__=='__main__':unittest.main()
