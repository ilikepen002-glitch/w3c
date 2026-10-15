"""Fresh actual candidate matrix preparation. Never run as source-only proof.

The candidate constructor rejects missing new production bodies. This file has
not run against a newly built candidate: all map contracts remain PENDING.
"""
from pathlib import Path
import sys
import unittest
from python_check_inputs import candidate_map

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from GenerateTowerTerrainMask import Mpq
from ReadEquipmentCatalog import catalog
from InventoryCraftJassRuntime import InventoryCraftJassRuntime
from VerifyGroundUpgradeArtifact import expected_pile_position
from VerifyTowerUpgradeArtifact import rawcode


class InventoryCraftArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script=Mpq(candidate_map().read_bytes()).extract('war3map.j').decode('utf-8')
        cls.entries=catalog();cls.pools={q:[e for e in cls.entries if e.quality==q] for q in (1,2,3,4)}
        # Fail-closed preflight, no fake catalog or available replacement.
        cls.preflight=InventoryCraftJassRuntime(cls.script)

    def scenario(self,count=3,lane=0,quality=1,mixed=False,roll=1,ground=False):
        r=InventoryCraftJassRuntime(self.script);r.roll=roll
        x,y=expected_pile_position(lane,quality)
        u=r.add_unit(lane,x,y);originals=[]
        for index in range(count):
            entry=self.pools[quality][index if mixed else 0] if index<3 else self.pools[4][-1]
            i=r.add_item(rawcode(entry.rawcode),x,y);originals.append(i)
            if not ground:r.place(u,i,index)
        expected=rawcode(self.pools[quality+1][roll-1].rawcode if mixed else self.pools[quality][0].next_id)
        return r,u,originals,expected

    def start(self,r,u,ground=False,quality=1,expect_started=True):
        if ground:
            r.block_terrain=False
            r.invoke('tdStartGroundCraft',u,*expected_pile_position(r.units[u]['owner'],quality))
        else:r.invoke('tdStartInventoryCraft',u)
        session=r.globals['TDCraftingRuntime_tdCraftSession']
        if expect_started:self.assertTrue(session,'valid scenario never entered the actual craft session')
        else:self.assertFalse(session,'rejected scenario unexpectedly entered a craft session')
        return session

    def conserved(self,r,originals):
        self.assertFalse(set(originals[:3]) & set(r.removed),'transaction removed an original on failure')
        for i in originals:
            holders=[u for u,data in r.units.items() if i in data['slots']]
            self.assertLessEqual(len(holders),1)
            self.assertEqual(holders[0] if holders else None,r.items[i]['holder'])

    def pending(self,r,lane=0):
        return r.globals['TDCraftingRecovery_tdCraftRecoveryRecords'][lane]

    def backend(self,r):
        session=r.globals['TDCraftingRuntime_tdCraftSession']
        return r.globals['TDCraftSession_backend'][session]

    def test_cf06_actual_catalog_ready_twice_no_loop_or_duplicate_registration(self):
        r=InventoryCraftJassRuntime(self.script)
        self.assertTrue(r.invoke('tdCraftCatalogReady'))
        first=r.globals['TDCraftingRuntime_tdRuntimeCraftCatalog']
        count=r.globals['TDItemData_tdItemDefinitionTotal']
        self.assertTrue(r.invoke('tdCraftCatalogReady'))
        self.assertEqual(r.globals['TDCraftingRuntime_tdRuntimeCraftCatalog'],first)
        self.assertEqual(r.globals['TDItemData_tdItemDefinitionTotal'],count)
        self.assertEqual(count,40)

    def test_inv01_real_catalog_planner_four_players_fixed_and_every_mixed_roll(self):
        cases=0
        for lane in range(4):
            for quality in (1,2,3):
                for mixed in (False,True):
                    for roll in (range(1,11) if mixed else (1,)):
                        with self.subTest(lane=lane,quality=quality,mixed=mixed,roll=roll):
                            r,u,originals,expected=self.scenario(lane=lane,quality=quality,mixed=mixed,roll=roll)
                            self.assertTrue(self.start(r,u));r.drain()
                            self.assertEqual(r.removed,originals[:3]);self.assertEqual(len(r.products),1)
                            self.assertEqual(r.items[r.products[0]]['id'],expected)
                            self.assertEqual(r.items[r.products[0]]['holder'],u)
                            self.assertFalse(self.pending(r,lane));cases+=1
        self.assertEqual(cases,132)

    def test_inv02_three_to_six_slots_zero_terrain_and_single_exact_detach(self):
        for count in (3,4,5,6):
            r,u,originals,expected=self.scenario(count);r.units[u].update(x=1234.,y=-2345.)
            self.assertTrue(self.start(r,u));r.drain()
            self.assertEqual(r.detaches,[] if count<6 else [originals[0]])
            self.assertEqual(r.pathing_calls,[]);self.assertEqual(r.moves,[])
            self.assertEqual(r.removed,originals[:3]);self.assertEqual(r.items[r.products[0]]['id'],expected)
            for slot,item in enumerate(originals[3:],3):self.assertEqual(r.units[u]['slots'][slot],item)

    def test_inv01_real_front_three_pair_mixed_quality_purple_and_non_equipment_rejection(self):
        for mode in ('pair','gap','mixed_quality','purple','non_equipment'):
            r,u,originals,_=self.scenario()
            if mode=='pair':r.unlink(originals[2])
            elif mode=='gap':r.unlink(originals[1]);r.place(u,originals[1],4)
            elif mode=='mixed_quality':r.items[originals[1]]['id']=rawcode(self.pools[2][0].rawcode)
            else:
                for i in originals:r.items[i]['id']=rawcode(self.pools[4][0].rawcode if mode=='purple' else 'ratf')
            self.assertFalse(self.start(r,u,expect_started=False));self.assertEqual(r.products,[])
            self.assertEqual(r.detaches,[]);self.conserved(r,originals)

    def test_inv03_create_and_native_return_membership_contradictions_keep_originals(self):
        for mode in ('null','wrong','alias','true_missing','false_member','false_missing'):
            with self.subTest(mode=mode):
                r,u,originals,_=self.scenario(6)
                if mode in ('null','wrong','alias'):r.create_mode=mode;r.alias_item=originals[0]
                else:r.output_mode={'true_missing':(True,False),'false_member':(False,True),'false_missing':(False,False)}[mode]
                self.start(r,u);r.drain();self.conserved(r,originals)
                self.assertTrue(all(not r.items[i]['id'] for i in r.products))

    def test_inv03_output_deleted_retyped_or_transferred_in_add_callback(self):
        for mode in ('delete','raw','foreign'):
            r,u,originals,_=self.scenario(6);other=r.add_unit(1);observed=[]
            def callback(farmer,item):
                if item not in r.products:return
                observed.append(item)
                if mode=='delete':r.unlink(item);r.items[item]['id']=0
                elif mode=='raw':r.items[item]['id']=rawcode(self.pools[4][-1].rawcode)
                else:r.pickup(other,item)
            r.on_add=callback;self.start(r,u);r.drain();self.conserved(r,originals)
            self.assertEqual(len(r.products),1);self.assertEqual(observed,r.products)
            self.assertTrue(all(not r.items[i]['id'] for i in r.products))

    def test_inv04_each_source_changed_in_create_and_output_add_callbacks(self):
        for boundary in ('create','add'):
            for index in range(3):
                for mode in ('delete','raw','foreign','repick','move'):
                    with self.subTest(boundary=boundary,index=index,mode=mode):
                        r,u,originals,_=self.scenario(6);other=r.add_unit(1);observed=[]
                        def change(*args):
                            observed.append(originals[index])
                            i=originals[index]
                            if mode=='delete':r.unlink(i);r.items[i]['id']=0
                            elif mode=='raw':r.items[i]['id']=rawcode(self.pools[2][-1].rawcode)
                            elif mode=='foreign':r.pickup(other,i)
                            elif mode=='repick':r.pickup(other,i);r.unlink(i)
                            elif r.items[i]['holder'] is None:r.items[i]['x']+=555.
                            else:
                                slots=r.units[u]['slots'];slot=slots.index(i);other_slot=(slot+1)%6
                                slots[slot],slots[other_slot]=slots[other_slot],slots[slot]
                        if boundary=='create':r.on_create=change
                        else:r.on_add=lambda farmer,item:change() if item in r.products else None
                        self.start(r,u);r.drain();self.conserved(r,originals)
                        self.assertEqual(observed,[originals[index]])

    def test_inv04_farmer_and_gameover_changed_at_create_or_output_add(self):
        for boundary in ('create','add'):
            for mode in ('death','remove','type','owner','gameover'):
                with self.subTest(boundary=boundary,mode=mode):
                    r,u,originals,_=self.scenario(6);observed=[]
                    def change(*args):
                        observed.append(mode)
                        if mode=='death':r.units[u]['alive']=False
                        elif mode=='remove':r.units[u]['id']=0
                        elif mode=='type':r.units[u]['id']=rawcode('uT01')
                        elif mode=='owner':r.units[u]['owner']=1
                        else:r.globals['TDState_tdGameOver']=True
                    if boundary=='create':r.on_create=change
                    else:r.on_add=lambda farmer,item:change() if item in r.products else None
                    self.start(r,u);r.drain();self.conserved(r,originals)
                    self.assertEqual(observed,[mode])

    def test_inv04_remaining_sources_changed_in_drop_before_and_after_callbacks(self):
        for order in ('before','after'):
            for index in (1,2):
                for mode in ('delete','raw','swap','foreign','repick'):
                    with self.subTest(order=order,index=index,mode=mode):
                        r,u,originals,_=self.scenario(6);r.drop_mode=order
                        other=r.add_unit(1);observed=[]
                        def callback(farmer,dropped):
                            observed.append(dropped)
                            item=originals[index]
                            if mode=='delete':r.unlink(item);r.items[item]['id']=0
                            elif mode=='raw':r.items[item]['id']=rawcode(self.pools[2][-1].rawcode)
                            elif mode=='swap':
                                slots=r.units[u]['slots'];slot=slots.index(item);other_slot=(slot+1)%6
                                slots[slot],slots[other_slot]=slots[other_slot],item
                            elif mode=='foreign':r.pickup(other,item)
                            else:r.pickup(other,item);r.unlink(item)
                        r.on_drop=callback
                        self.assertTrue(self.start(r,u));r.drain();self.conserved(r,originals)
                        self.assertEqual(observed,[originals[0]])
                        self.assertEqual(r.detaches,[originals[0]])
                        self.assertFalse(any(item in r.products for _,item in r.adds))
                        self.assertTrue(all(not r.items[item]['id'] for item in r.products))
                        self.assertEqual(r.globals['TDCraftingNativeBackend_tdCraftBackendCommitOwner'],0)
                        if mode=='foreign':self.assertEqual(r.items[originals[index]]['holder'],other)

    def test_inv04_farmer_and_gameover_changed_in_drop_before_and_after_callbacks(self):
        for order in ('before','after'):
            for mode in ('death','remove','type','owner','gameover'):
                with self.subTest(order=order,mode=mode):
                    r,u,originals,_=self.scenario(6);r.drop_mode=order;observed=[]
                    def callback(farmer,dropped):
                        observed.append(dropped)
                        if mode=='death':r.units[u]['alive']=False
                        elif mode=='remove':r.units[u]['id']=0
                        elif mode=='type':r.units[u]['id']=rawcode('uT01')
                        elif mode=='owner':r.units[u]['owner']=2
                        else:r.globals['TDState_tdGameOver']=True
                    r.on_drop=callback
                    self.assertTrue(self.start(r,u));r.drain();self.conserved(r,originals)
                    self.assertEqual(observed,[originals[0]])
                    self.assertEqual(r.detaches,[originals[0]])
                    self.assertFalse(any(item in r.products for _,item in r.adds))
                    self.assertTrue(all(not r.items[item]['id'] for item in r.products))
                    self.assertEqual(r.globals['TDCraftingNativeBackend_tdCraftBackendCommitOwner'],0)

    def test_inv05_drop_interleavings_transfer_repick_occupation_and_no_detach(self):
        for mode in ('before','after','none','foreign','repick','occupied'):
            with self.subTest(mode=mode):
                r,u,originals,_=self.scenario(6);other=r.add_unit(1)
                if mode in ('before','after','none'):r.drop_mode=mode
                elif mode=='foreign':r.on_drop=lambda farmer,item:r.pickup(other,item)
                elif mode=='repick':r.on_drop=lambda farmer,item:(r.pickup(other,item),r.unlink(item))
                else:
                    extra=r.add_item(rawcode(self.pools[4][-1].rawcode),0.,0.)
                    r.on_drop=lambda farmer,item:r.pickup(farmer,extra)
                self.start(r,u);r.drain()
                if mode in ('before','after'):self.assertEqual(r.removed,originals[:3])
                else:self.conserved(r,originals)
                self.assertEqual(r.detaches,[originals[0]])

    def test_inv05_actual_same_backend_add_reentry_three_and_six_slots(self):
        for count in (3,6):
            r,u,originals,expected=self.scenario(count);observed=[]
            self.start(r,u);backend=self.backend(r)
            def callback(farmer,item):
                if item not in r.products:return
                observed.append(r.globals['TDCraftNativeBackend_phase'][backend])
                r.on_add=None
                observed.append(r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_consumeThree',backend,1,2,3))
                observed.append(r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_prepareResult',backend,expected))
            r.on_add=callback;r.drain()
            self.assertEqual(observed,[3,False,0]);self.assertEqual(r.removed,originals[:3]);self.assertEqual(len(r.products),1)

    def test_inv05_actual_cancel_return_other_backend_prepare_stays_blocked(self):
        r,u,originals,expected=self.scenario(6);r.output_mode=(False,False)
        self.start(r,u);backend=self.backend(r)
        other=r.invoke('new_TDCraftNativeBackend',u,0,r.units[u]['x'],r.units[u]['y'],True)
        observed=[]
        def callback(farmer,item):
            if item!=originals[0]:return
            observed.append((r.globals['TDCraftNativeBackend_phase'][backend],r.globals['TDCraftingNativeBackend_tdCraftBackendCommitOwner']))
            observed.append(r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_prepareResult',other,expected))
        r.on_add=callback;r.drain();self.conserved(r,originals)
        self.assertEqual(observed,[(3,backend),0]);self.assertEqual(len(r.products),1)
        r.invoke('dispatch_TDCraftNativeBackend_destroyTDCraftNativeBackend',other)

    def test_inv05_create_and_add_same_and_different_batch_reentry_cannot_prepare(self):
        for boundary in ('create','add'):
            r,u,originals,expected=self.scenario();self.start(r,u)
            session=r.globals['TDCraftingRuntime_tdCraftSession'];backend=self.backend(r)
            plan=r.globals['TDCraftSession_plan'][session]
            catalog_id=r.globals['TDCraftingRuntime_tdRuntimeCraftCatalog']
            other_plan=r.invoke('new_TDCraftPlan',catalog_id)
            for index,i in enumerate(originals,1):
                self.assertTrue(r.invoke('dispatch_TDCraftPlan_TDCraftPlan_capture',other_plan,index,r.items[i]['id']))
            # freeze() is a test-only convenience that the production compiler
            # omits. Exercise the real staged planner entry points instead.
            self.assertTrue(r.invoke('dispatch_TDCraftPlan_TDCraftPlan_beginFreeze',other_plan))
            for _ in range(len(originals)+1):
                if r.invoke('dispatch_TDCraftPlan_TDCraftPlan_isFrozen',other_plan):break
                r.invoke('dispatch_TDCraftPlan_TDCraftPlan_planningStep',other_plan,24)
            self.assertTrue(r.invoke('dispatch_TDCraftPlan_TDCraftPlan_isFrozen',other_plan))
            observed=[]
            def change(*args):
                observed.append(r.invoke('tdCommitCraftBatch',plan,0,catalog_id,backend,1))
                observed.append(r.invoke('tdCommitCraftBatch',other_plan,0,catalog_id,backend,1))
            if boundary=='create':r.on_create=change
            else:r.on_add=lambda farmer,item:change() if item in r.products else None
            r.drain();self.assertEqual(observed,[3,2])
            self.assertEqual(r.removed,originals[:3]);self.assertEqual(len(r.products),1)
            r.invoke('dispatch_TDCraftPlan_destroyTDCraftPlan',other_plan)

    def test_inv05_duplicate_keys_handles_and_stale_result_tokens_real_backend(self):
        for keys in ((1,1,3),(1,2,2),(1,2,99)):
            r,u,originals,expected=self.scenario();self.start(r,u);backend=self.backend(r)
            key=r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_prepareResult',backend,expected)
            self.assertTrue(key)
            self.assertFalse(r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_consumeThree',backend,*keys))
            r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_discardResult',backend,key)
            r.invoke('tdFinishCraftSession');self.conserved(r,originals)
        r,u,originals,expected=self.scenario();self.start(r,u);backend=self.backend(r)
        records=r.table(r.globals['TDCraftNativeBackend_records'][backend])
        second=records[2]
        r.globals['TDCraftNativeIngredient_itemHandle'][second]=originals[0]
        key=r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_prepareResult',backend,expected)
        self.assertFalse(r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_consumeThree',backend,1,2,3))
        r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_discardResult',backend,key)
        r.invoke('tdFinishCraftSession');self.conserved(r,originals)
        r,u,originals,expected=self.scenario();self.start(r,u);backend=self.backend(r)
        key=r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_prepareResult',backend,expected)
        r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_discardResult',backend,key+1)
        self.assertTrue(r.items[r.products[0]]['id'])
        self.assertTrue(r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_consumeThree',backend,1,2,3))
        r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_publishResult',backend,key+1)
        self.assertEqual(r.globals['TDCraftNativeBackend_output'][backend],r.products[0])
        r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_publishResult',backend,key)
        r.invoke('dispatch_TDCraftCommitBackend_TDCraftCommitBackend_discardResult',backend,key)
        r.invoke('tdFinishCraftSession');self.assertTrue(r.items[r.products[0]]['id'])

    def test_inv06_pending_survives_actual_finish_destructor_then_returns_exact_once(self):
        r,u,originals,_=self.scenario(6);r.output_mode=r.return_mode=(False,False)
        self.start(r,u);r.drain();record=self.pending(r);self.assertTrue(record)
        self.assertEqual(r.globals['TDCraftRecoveryRecord_material'][record],originals[0]);self.conserved(r,originals)
        r.return_mode=(False,True);r.invoke('tdCraftPumpRecovery',.5)
        self.assertFalse(self.pending(r));self.assertEqual(r.items[originals[0]]['holder'],u)
        before=len(r.adds);r.invoke('tdCraftPumpRecovery',.5);self.assertEqual(len(r.adds),before)

    def test_inv06_synchronous_original_quality_pile_destination_feedback(self):
        for quality in (1,2,3):
            r,u,originals,_=self.scenario(6,quality=quality)
            r.output_mode=r.return_mode=(False,False);r.block_terrain=False
            self.start(r,u);r.drain();self.conserved(r,originals);self.assertFalse(self.pending(r))
            self.assertTrue(r.items[originals[0]]['visible'])
            self.assertTrue(r.invoke('tdItemActualInPile',originals[0],0,quality))
            name=('白装','绿装','蓝装')[quality-1]
            self.assertTrue(any('本路'+name+'材料堆' in m[-1] for m in r.messages))

    def test_inv07_registered_external_move_reveal_never_reclaimed(self):
        for mode in ('move','reveal','both'):
            r,u,originals,_=self.scenario(6);r.output_mode=r.return_mode=(False,False)
            self.start(r,u);r.drain();record=self.pending(r);self.assertTrue(record)
            if mode in ('move','both'):r.items[originals[0]]['x']+=999.
            if mode in ('reveal','both'):r.items[originals[0]]['visible']=True
            before=(len(r.adds),len(r.moves));r.return_mode=(True,True)
            r.invoke('tdCraftPumpRecovery',.5);r.invoke('tdCraftPumpRecovery',.5)
            self.assertEqual((len(r.adds),len(r.moves)),before);self.assertEqual(self.pending(r),record);self.conserved(r,originals)

    def test_inv07_original_holder_and_successful_return_callback_hide_retype_preserved(self):
        for boundary in ('external','return'):
            for mode in ('hide','retype','both'):
                r,u,originals,_=self.scenario(6);r.output_mode=(False,False);observed=[]
                def change(*args):
                    observed.append(originals[0])
                    if mode in ('hide','both'):r.items[originals[0]]['visible']=False
                    if mode in ('retype','both'):r.items[originals[0]]['id']=rawcode(self.pools[2][-1].rawcode)
                if boundary=='external':
                    r.return_mode=(False,False);self.start(r,u);r.drain();self.assertTrue(self.pending(r))
                    r.pickup(u,originals[0]);change()
                    r.invoke('tdCraftPumpRecovery',.5)
                else:
                    r.on_add=lambda farmer,item:change() if item==originals[0] else None
                    self.start(r,u);r.drain()
                self.assertEqual(observed,[originals[0]])
                self.assertFalse(self.pending(r));self.conserved(r,originals)
                if mode in ('hide','both'):self.assertFalse(r.items[originals[0]]['visible'])
                if mode in ('retype','both'):self.assertEqual(r.items[originals[0]]['id'],rawcode(self.pools[2][-1].rawcode))

    def test_inv07_output_or_failed_return_callback_custody_changes_stop_later_native(self):
        for boundary,mode in (('output','move'),('output','reveal'),('return','move'),('return','hide')):
            with self.subTest(boundary=boundary,mode=mode):
                r,u,originals,_=self.scenario(6);r.output_mode=r.return_mode=(False,False);observed=[]
                def callback(farmer,item):
                    if not ((boundary=='output' and item in r.products) or (boundary=='return' and item==originals[0])):return
                    observed.append(item)
                    if mode=='move':r.items[originals[0]]['x']+=888.
                    else:r.items[originals[0]]['visible']=mode=='reveal'
                r.on_add=callback;self.start(r,u);r.drain();record=self.pending(r);self.assertTrue(record)
                self.assertEqual(observed,[r.products[0] if boundary=='output' else originals[0]])
                before=(len(r.adds),len(r.moves));r.return_mode=(True,True);r.invoke('tdCraftPumpRecovery',.5)
                self.assertEqual((len(r.adds),len(r.moves)),before);self.assertEqual(self.pending(r),record);self.conserved(r,originals)

    def test_inv08_real_four_record_limit_and_shared_watch_reference_lifetime(self):
        r,u,originals,_=self.scenario(6);records=[]
        for owner in range(4):
            farmer=r.add_unit(owner);i=r.add_item(rawcode(self.pools[1][0].rawcode),0.,0.)
            record=r.invoke('tdCraftReserveRecovery',farmer,i,r.items[i]['id'],1,0);records.append(record)
            self.assertTrue(record)
            self.assertFalse(r.invoke('tdCraftReserveRecovery',farmer,i,r.items[i]['id'],1,0))
        self.assertEqual(r.globals['TDCraftingRecovery_tdCraftRecoveryCount'],4)
        self.start(r,u,expect_started=False);self.assertFalse(r.globals['TDCraftingRuntime_tdCraftSession'])
        self.assertEqual(r.detaches,[]);self.conserved(r,originals)
        for record in records:r.invoke('tdCraftReleaseRecovery',record)
        self.assertEqual(r.globals['TDCraftingRecovery_tdCraftRecoveryCount'],0)
        first=r.invoke('tdCraftWatchAcquire',originals[0]);second=r.invoke('tdCraftWatchAcquire',originals[0])
        self.assertEqual(first,second);r.pickup(u,originals[0],0)
        serial=r.globals['TDCraftPickupRecord_pickupSerial'][first]
        r.invoke('tdCraftWatchRelease',first)
        self.assertEqual(r.globals['TDCraftPickupRecord_refs'][second],1)
        self.assertEqual(r.globals['TDCraftPickupRecord_pickupSerial'][second],serial)
        r.invoke('tdCraftWatchRelease',second)

    def test_inv08_pending_player_continuation_other_player_and_ground_after_lock_release(self):
        r,u,originals,_=self.scenario(6);r.output_mode=r.return_mode=(False,False)
        self.start(r,u);r.drain();record=self.pending(r);self.assertTrue(record)
        # A newly-filled full inventory for the same player cannot unload again.
        extra=r.add_item(rawcode(self.pools[1][0].rawcode),0.,0.);r.place(u,extra,0)
        before=len(r.detaches);self.start(r,u,expect_started=False);self.assertFalse(r.globals['TDCraftingRuntime_tdCraftSession'])
        self.assertEqual(len(r.detaches),before);self.assertEqual(self.pending(r),record)
        other=r.add_unit(1,*expected_pile_position(1,1));other_items=[]
        for slot in range(3):
            i=r.add_item(rawcode(self.pools[1][0].rawcode),*expected_pile_position(1,1));other_items.append(i);r.place(other,i,slot)
        r.output_mode=(True,True);self.assertTrue(self.start(r,other));r.drain()
        self.assertTrue(set(other_items)<=set(r.removed));self.assertEqual(self.pending(r),record)
        ground_items=[r.add_item(rawcode(self.pools[1][0].rawcode),*expected_pile_position(1,1)) for _ in range(3)]
        self.assertTrue(self.start(r,other,ground=True));r.drain()
        self.assertTrue(set(ground_items)<=set(r.removed));self.conserved(r,originals)
        # Pump may safely finish original-quality fallback once terrain permits.
        self.assertTrue(self.pending(r)==record or r.invoke('tdItemActualInPile',originals[0],0,1) or r.items[originals[0]]['holder']==u)

    def test_inv09_gameover_stops_retries_without_automatic_retry_promise(self):
        r,u,originals,_=self.scenario(6);r.output_mode=(False,False)
        r.on_add=lambda farmer,item:r.globals.update(TDState_tdGameOver=True) if item in r.products else None
        self.start(r,u);r.drain();self.conserved(r,originals);self.assertTrue(self.pending(r))
        self.assertTrue(any('自动归还已停止' in m[-1] for m in r.messages))
        self.assertFalse(any('系统会自动重试' in m[-1] for m in r.messages))
        before=(len(r.adds),len(r.moves));r.invoke('tdCraftPumpRecovery',.5);self.assertEqual((len(r.adds),len(r.moves)),before)

    def test_ground01_real_capture_plan_guaranteed_batches_leftovers_next_pile(self):
        for lane in range(4):
            for quality in (1,2,3):
                r,u,originals,_=self.scenario(3,lane,quality,ground=True)
                x,y=expected_pile_position(lane,quality)
                leftovers=[r.add_item(rawcode(self.pools[quality][-1].rawcode),x,y) for _ in range(2)]
                self.start(r,u,ground=True,quality=quality);r.drain()
                self.assertEqual(len(r.removed),3);self.assertFalse(set(leftovers)&set(r.removed))
                self.assertEqual(r.detaches,[]);self.assertEqual(r.adds,[])
                self.assertEqual(len(r.products),1);self.assertTrue(r.invoke('tdItemActualInPile',r.products[0],lane,quality+1))
