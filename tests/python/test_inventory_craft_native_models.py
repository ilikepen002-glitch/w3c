"""Synthetic native-model regressions only; no map/craft behavior acceptance."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from InventoryCraftJassRuntime import InventoryCraftJassRuntime
from VerifyTowerUpgradeArtifact import JassScalarEvaluator,rawcode

SCRIPT='''globals
integer observed
endglobals
function tdCraftTrackPickup takes nothing returns nothing
set observed = observed + 1
endfunction
'''

class InventoryCraftNativeModelTests(unittest.TestCase):
    def runtime(self):
        # Deliberate synthetic object, never accepted by the public candidate
        # constructor and never counted as an actual packaged-map result.
        r=object.__new__(InventoryCraftJassRuntime)
        JassScalarEvaluator.__init__(r,SCRIPT);r.initialize_models(SCRIPT)
        return r
    def test_candidate_constructor_rejects_missing_delivery_contract(self):
        with self.assertRaisesRegex(ValueError,'PENDING new candidate'):
            InventoryCraftJassRuntime(SCRIPT)
    def test_constructor_executes_catalog_dependency_initializers_before_item_data(self):
        # Synthetic generated bodies prove initialization order without copying
        # the production catalog or substituting any successful catalog result.
        script='''globals
integer observed
integer TDItemCatalogIds_SAMPLE
integer TDItemCatalogSchema_SAMPLE
integer TDCraftingItemWatch_tdCraftPickupRecords
integer array TDCraftNativeBackend_phase
integer array TDCraftNativeBackend_staging
endglobals
function init_TDItemCatalogIds takes nothing returns nothing
set TDItemCatalogIds_SAMPLE = 17
endfunction
function init_TDItemCatalogSchema takes nothing returns nothing
set TDItemCatalogSchema_SAMPLE = 23
endfunction
function init_TDItemData takes nothing returns nothing
set observed = TDItemCatalogIds_SAMPLE + TDItemCatalogSchema_SAMPLE
endfunction
function tdSetupCraftPickupWatch takes nothing returns nothing
endfunction
function alloc_CallbackPeriodic_doPeriodically_TDCraftingRuntime takes nothing returns integer
return 1
endfunction
function construct_CallbackPeriodic takes integer callback returns nothing
endfunction
'''
        for name in InventoryCraftJassRuntime.REQUIRED:
            script+=f'function {name} takes nothing returns nothing\nendfunction\n'
        r=InventoryCraftJassRuntime(script)
        self.assertEqual(r.globals['observed'],40)
    def test_pathing_is_opaque_walkability_and_unknown_type_fails_closed(self):
        r=self.runtime();self.assertEqual(r.native('IsTerrainPathable',[1.,2.,r.walkability]),(True,True))
        r.block_terrain=False;self.assertEqual(r.native('IsTerrainPathable',[1.,2.,r.walkability]),(True,False))
        with self.assertRaisesRegex(ValueError,'incorrect native pathing type'):
            r.native('IsTerrainPathable',[1.,2.,0])
    def test_add_return_and_actual_membership_are_independent(self):
        for result,member in ((True,True),(True,False),(False,True),(False,False)):
            r=self.runtime();u=r.add_unit(2,123.,-456.);i=r.add_item(rawcode('iG01'),0.,0.)
            r.products.append(i);r.output_mode=(result,member)
            self.assertEqual(r.native('UnitAddItem',[u,i]),(True,result))
            self.assertEqual(r.items[i]['holder']==u,member)
            self.assertEqual(r.globals['observed'],int(member))
            self.assertEqual(r.native('GetUnitX',[u]),(True,123.))
            self.assertEqual(r.native('GetUnitY',[u]),(True,-456.))
    def test_drop_before_after_no_detach_and_callback_transfer(self):
        for mode in ('before','after','none'):
            r=self.runtime();u=r.add_unit(0);i=r.add_item(rawcode('iW01'),0.,0.);r.place(u,i,0)
            observed=[];r.on_drop=lambda unit,item:observed.append(r.items[item]['holder'])
            r.drop_mode=mode;r.native('UnitRemoveItem',[u,i])
            self.assertEqual(observed,[None if mode=='after' else u])
            self.assertEqual(r.items[i]['holder'],u if mode=='none' else None)
        r=self.runtime();u=r.add_unit(0);other=r.add_unit(1);i=r.add_item(rawcode('iW01'),0.,0.);r.place(u,i,0)
        r.drop_mode='before';r.on_drop=lambda unit,item:r.pickup(other,item)
        r.native('UnitRemoveItem',[u,i]);self.assertEqual(r.items[i]['holder'],other)
    def test_collection_table_lifetime_and_unknown_operations_fail_closed(self):
        r=self.runtime();_,ll=r.native('new_LinkedList',['source'])
        r.native('dispatch_LinkedList_LinkedList_add_1',[ll,'source',17])
        _,it=r.native('dispatch_LinkedList_LinkedList_iterator',[ll,'source'])
        self.assertEqual(r.native('dispatch_LLIterator_LLIterator_next',[it,'source']),(True,17))
        self.assertEqual(r.native('dispatch_LLIterator_LLIterator_hasNext',[it,'source']),(True,False))
        with self.assertRaisesRegex(ValueError,'advanced past end'):r.native('dispatch_LLIterator_LLIterator_next',[it,'source'])
        r.native('dispatch_LLIterator_destroyLLIterator',[it,'source'])
        with self.assertRaisesRegex(ValueError,'Invalid modeled iterator'):r.native('dispatch_LLIterator_LLIterator_next',[it,'source'])
        _,table=r.native('new_HashMap',['source']);r.native('dispatch_HashMap_HashMap_put',[table,7,17,'source'])
        self.assertEqual(r.native('dispatch_HashMap_HashMap_get',[table,7,'source']),(True,17))
        r.native('dispatch_HashMap_HashMap_remove',[table,7,'source'])
        self.assertEqual(r.native('dispatch_HashMap_HashMap_has',[table,7,'source']),(True,False))
        with self.assertRaisesRegex(ValueError,'Unsupported modeled Table'):r.native('dispatch_HashMap_HashMap_unsafe',[table,'source'])
    def test_unknown_native_or_scalar_is_not_default_success(self):
        r=self.runtime();self.assertEqual(r.native('PretendAvailable',[1]),(False,None))
        with self.assertRaisesRegex(ValueError,'Missing packaged ground function'):r.call('PretendAvailable',[1])
        with self.assertRaisesRegex(ValueError,'Unknown Jass scalar'):r.expression('UnknownScalar',{})
