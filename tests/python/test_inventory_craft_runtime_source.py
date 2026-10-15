"""Fresh current source-body contracts. Planner/allocation/native APIs are fixtures.
This is not Wurst checking, current-map acceptance, or Warcraft-client evidence.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from CraftingSourceHarness import CraftSourceFixture,Backend
from VerifyTowerUpgradeArtifact import rawcode

class InventoryCraftRuntimeSourceTests(unittest.TestCase):
    def test_inv01_four_players_same_chain_and_all_mixed_source_oracles(self):
        count=0
        for lane in range(4):
            for quality in (1,2,3):
                for mixed in (False,True):
                    for roll in (range(1,11) if mixed else (1,)):
                        f=CraftSourceFixture(lane=lane,quality=quality,mixed=mixed,roll=roll)
                        self.assertEqual(f.commit(),1)
                        self.assertEqual(f.products[0].raw,rawcode(f.expected))
                        self.assertEqual(f.products[0].holder,f.farmer)
                        self.assertEqual(f.commit(),3)
                        self.assertEqual(len(f.products),1);count+=1
        self.assertEqual(count,132)
    def test_inv02_all_slot_counts_no_terrain_dependency_and_one_exact_detach(self):
        for count in (3,4,5,6):
            for lane in range(4):
                f=CraftSourceFixture(count,lane=lane)
                leftovers=list(f.originals[3:]);self.assertEqual(f.commit(),1)
                self.assertEqual(f.detaches,[] if count<6 else [f.originals[0]])
                self.assertEqual(f.moves,[])
                self.assertEqual(f.removed,f.originals[:3])
                for slot,item in enumerate(leftovers,3):self.assertIs(f.farmer.slots[slot],item)
    def test_inv03_creation_null_wrong_and_original_alias_never_consume(self):
        for mode in ('null','wrong','alias'):
            f=CraftSourceFixture(6);f.create_mode=mode
            self.assertEqual(f.commit(),2);f.conserved()
            self.assertEqual(f.detaches,[])
    def test_inv03_native_return_and_exact_membership_both_required(self):
        for count in (3,6):
            for result,member in ((True,False),(False,True),(False,False)):
                f=CraftSourceFixture(count);f.output_mode=(result,member)
                self.assertEqual(f.commit(),0);f.conserved()
                self.assertTrue(all(not i.raw for i in f.products))
    def test_inv03_output_callback_delete_retype_transfer(self):
        for mode in ('delete','retype','foreign'):
            f=CraftSourceFixture(6)
            def callback(u,i):
                if i not in f.products:return
                if mode=='delete':f.unlink(i);i.raw=0
                elif mode=='retype':i.raw=f.pools[4][-1]
                else:f.pickup(f.other,i)
            f.on_add=callback
            if mode=='delete':
                # RemoveItem of an already-deleted newly-created handle is legal
                # engine cleanup; fixture keeps the deletion ledger exact once.
                original=f.n['RemoveItem'];f.n['RemoveItem']=lambda i:original(i) if i.raw else None
            self.assertEqual(f.commit(),0);f.conserved()
    def test_inv04_real_available_slot_handle_raw_pickup_farmer_and_gameover(self):
        for mode in ('slot','handle','raw','pickup','death','remove','type','owner','gameover'):
            f=CraftSourceFixture()
            if mode=='slot':f.farmer.slots[0],f.farmer.slots[1]=f.farmer.slots[1],f.farmer.slots[0]
            elif mode=='handle':
                f.unlink(f.originals[0]);f.place(f.farmer,f.item(f.originals[0].raw),0)
            elif mode=='raw':f.originals[0].raw=f.pools[2][0]
            elif mode=='pickup':f.pickup(f.farmer,f.originals[0],0)
            elif mode=='death':f.farmer.alive=False
            elif mode=='remove':f.farmer.raw=0
            elif mode=='type':f.farmer.raw=rawcode('uT01')
            elif mode=='owner':f.farmer.owner=3
            else:f.over=True
            self.assertFalse(f.backend.available(1,f.backend.records[1].rawcode))
            self.assertEqual(f.commit(),0);f.conserved();self.assertEqual(f.products,[])
    def test_inv04_each_source_changes_in_create_and_output_add_callbacks(self):
        for boundary in ('create','add'):
            for key in range(3):
                for mode in ('delete','raw','swap','foreign','repick'):
                    f=CraftSourceFixture(6)
                    def change(*args):
                        item=f.originals[key]
                        if mode=='delete':f.unlink(item);item.raw=0
                        elif mode=='raw':item.raw=f.pools[2][-1]
                        elif mode=='swap':
                            slot=next((s for s in range(6) if f.farmer.slots[s] is item),None)
                            if slot is not None:
                                other=(slot+1)%6;f.farmer.slots[slot],f.farmer.slots[other]=f.farmer.slots[other],item
                            else:item.x+=111.
                        elif mode=='foreign':f.pickup(f.other,item)
                        else:
                            f.pickup(f.other,item);f.unlink(item)
                            slot=next((s for s in range(6) if f.farmer.slots[s] is None),None)
                            if slot is not None:f.pickup(f.farmer,item,slot)
                    if boundary=='create':f.on_create=change
                    else:f.on_add=lambda u,i:change() if i in f.products else None
                    self.assertNotEqual(f.commit(),1);f.conserved()
    def test_inv04_farmer_and_gameover_after_add_no_early_consumption(self):
        for mode in ('death','remove','type','owner','gameover'):
            f=CraftSourceFixture(6)
            def callback(u,i):
                if i not in f.products:return
                if mode=='death':u.alive=False
                elif mode=='remove':u.raw=0
                elif mode=='type':u.raw=rawcode('uT01')
                elif mode=='owner':u.owner=2
                else:f.over=True
            f.on_add=callback;self.assertEqual(f.commit(),0);f.conserved()
    def test_inv04_remaining_sources_changed_in_drop_before_and_after_callbacks(self):
        for order in ('before','after'):
            for index in (1,2):
                for mode in ('delete','raw','swap','foreign','repick'):
                    with self.subTest(order=order,index=index,mode=mode):
                        f=CraftSourceFixture(6);f.drop_mode=order;observed=[]
                        def callback(u,dropped):
                            observed.append(dropped)
                            item=f.originals[index]
                            if mode=='delete':f.unlink(item);item.raw=0
                            elif mode=='raw':item.raw=f.pools[2][-1]
                            elif mode=='swap':
                                slot=f.farmer.slots.index(item);other=(slot+1)%6
                                f.farmer.slots[slot],f.farmer.slots[other]=f.farmer.slots[other],item
                            elif mode=='foreign':f.pickup(f.other,item)
                            else:f.pickup(f.other,item);f.unlink(item)
                        f.on_drop=callback
                        self.assertEqual(f.commit(),0);f.conserved()
                        self.assertEqual(observed,[f.originals[0]])
                        self.assertEqual(f.detaches,[f.originals[0]])
                        self.assertFalse(any(item in f.products for _,item in f.adds))
                        self.assertTrue(all(not item.raw for item in f.products))
                        self.assertEqual(f.n['tdCraftBackendCommitOwner'],0)
                        if mode=='foreign':self.assertIs(f.originals[index].holder,f.other)
    def test_inv04_farmer_and_gameover_changed_in_drop_before_and_after_callbacks(self):
        for order in ('before','after'):
            for mode in ('death','remove','type','owner','gameover'):
                with self.subTest(order=order,mode=mode):
                    f=CraftSourceFixture(6);f.drop_mode=order;observed=[]
                    def callback(u,dropped):
                        observed.append(dropped)
                        if mode=='death':u.alive=False
                        elif mode=='remove':u.raw=0
                        elif mode=='type':u.raw=rawcode('uT01')
                        elif mode=='owner':u.owner=2
                        else:f.over=True
                    f.on_drop=callback
                    self.assertEqual(f.commit(),0);f.conserved()
                    self.assertEqual(observed,[f.originals[0]])
                    self.assertEqual(f.detaches,[f.originals[0]])
                    self.assertFalse(any(item in f.products for _,item in f.adds))
                    self.assertTrue(all(not item.raw for item in f.products))
                    self.assertEqual(f.n['tdCraftBackendCommitOwner'],0)
    def test_inv05_drop_before_after_transfer_repick_occupation_and_no_detach(self):
        for mode in ('before','after','none','foreign','repick','occupied'):
            f=CraftSourceFixture(6)
            if mode in ('before','after','none'):f.drop_mode=mode
            elif mode=='foreign':f.on_drop=lambda u,i:f.pickup(f.other,i)
            elif mode=='repick':f.on_drop=lambda u,i:f.pickup(u,i,0)
            else:f.on_drop=lambda u,i:f.place(u,f.item(f.pools[4][-1]),0)
            result=f.commit()
            self.assertEqual(result,1 if mode in ('before','after') else 0)
            if result!=1:f.conserved()
            self.assertEqual(len(f.detaches),1)
    def test_inv05_add_and_create_reentry_same_other_batch_and_other_backend(self):
        for boundary in ('create','add'):
            f=CraftSourceFixture(6);other=Backend(f,f.farmer,True,0)
            plan=NS(capture=lambda key,raw:True)
            for slot,i in enumerate(f.originals[:3]):self.assertTrue(other.capture(plan,i,slot))
            observed=[]
            def callback(*args):
                if boundary=='add' and args[-1] not in f.products:return
                observed.append(f.commit())
                observed.append(f.backend.prepareResult(rawcode(f.expected)))
                observed.append(f.backend.consumeThree(1,2,3))
                observed.append(other.prepareResult(rawcode(f.expected)))
                observed.append(other.consumeThree(1,2,3))
            if boundary=='create':f.on_create=callback
            else:f.on_add=callback
            self.assertEqual(f.commit(),1)
            self.assertEqual(observed,[3,0,False,0,False])
            self.assertEqual(len(f.products),1);self.assertEqual(len(f.detaches),1)
            f.destroy(other);f.destroy(f.backend)
            self.assertEqual(f.n['tdCraftPickupRecords'],{})
    def test_inv05_duplicate_keys_handles_and_stale_result_tokens(self):
        for keys in ((1,1,3),(1,2,2),(1,2,99)):
            f=CraftSourceFixture();key=f.backend.prepareResult(rawcode(f.expected))
            self.assertFalse(f.backend.consumeThree(*keys));f.backend.discardResult(key);f.conserved()
        f=CraftSourceFixture();f.backend.records[2].itemHandle=f.originals[0]
        key=f.backend.prepareResult(rawcode(f.expected));self.assertFalse(f.backend.consumeThree(1,2,3))
        f.backend.discardResult(key);f.conserved()
        f=CraftSourceFixture();key=f.backend.prepareResult(rawcode(f.expected))
        f.backend.discardResult(key+1);self.assertTrue(f.products[0].raw)
        self.assertTrue(f.backend.consumeThree(1,2,3))
        f.backend.publishResult(key+1);self.assertIs(f.backend.output,f.products[0])
        f.backend.publishResult(key);self.assertIsNone(f.backend.output)
        f.backend.discardResult(key);self.assertTrue(f.products[0].raw)
    def test_inv05_same_object_add_reentry_uses_live_delivering_phase_three_and_six_slots(self):
        for count in (3,6):
            with self.subTest(count=count):
                f=CraftSourceFixture(count);observed=[]
                def callback(u,i):
                    if i not in f.products:return
                    observed.append((f.backend.phase,f.n['phase']))
                    # Disable the callback so a broken phase guard produces a
                    # finite, observable second consumption instead of recursion.
                    f.on_add=None
                    observed.append(f.backend.consumeThree(1,2,3))
                f.on_add=callback
                self.assertEqual(f.commit(),1)
                self.assertEqual(observed,[(3,3),False])
                self.assertEqual(f.removed,f.originals[:3])
                self.assertEqual(len(f.products),1)
                self.assertEqual(len(f.detaches),int(count==6))
    def test_inv05_cancel_return_keeps_phase_and_owner_through_native_callback(self):
        f=CraftSourceFixture(6);f.output_mode=(False,False)
        other=Backend(f,f.farmer,True,0);observed=[]
        def callback(u,i):
            if i is not f.originals[0]:return
            observed.append((f.backend.phase,f.n['tdCraftBackendCommitOwner']))
            observed.append(f.backend.prepareResult(rawcode(f.expected)))
            observed.append(f.backend.consumeThree(1,2,3))
            observed.append(other.prepareResult(rawcode(f.expected)))
        f.on_add=callback
        self.assertEqual(f.commit(),0);f.conserved()
        self.assertEqual(observed,[(3,f.backend.taskToken),0,False,0])
        self.assertEqual(len(f.products),1)
        self.assertEqual(f.n['tdCraftBackendCommitOwner'],0)
        self.assertEqual(f.backend.phase,0)
        self.assertIsNone(f.pending());self.assertIs(f.originals[0].holder,f.farmer)
    def test_inv06_pending_survives_destructor_returns_original_once(self):
        f=CraftSourceFixture(6);f.output_mode=f.return_mode=(False,False)
        self.assertEqual(f.commit(),0);record=f.pending();self.assertIs(record.material,f.originals[0])
        f.destroy(f.backend);self.assertIs(f.pending(),record);f.conserved()
        f.return_mode=(False,True);f.pump();self.assertIsNone(f.pending())
        self.assertIs(f.originals[0].holder,f.farmer);before=len(f.adds);f.pump();self.assertEqual(len(f.adds),before)
        self.assertEqual(f.n['tdCraftPickupRecords'],{})
    def test_inv06_sync_original_quality_pile_always_reports_destination(self):
        for quality in (1,2,3):
            f=CraftSourceFixture(6,quality=quality);f.output_mode=f.return_mode=(False,False);f.pile_available=True
            self.assertEqual(f.commit(),0);self.assertIsNone(f.pending());f.conserved()
            self.assertEqual(f.originals[0].pile,(0,quality));self.assertTrue(f.originals[0].visible)
            self.assertTrue(any(f.n['tdItemQualityName'](quality)+'材料堆' in m for _,m in f.messages))
    def test_inv07_registered_external_move_reveal_and_hide_never_stolen(self):
        for mode in ('move','reveal','move_reveal'):
            f=CraftSourceFixture(6);f.output_mode=f.return_mode=(False,False);f.commit();record=f.pending()
            if 'move' in mode:f.originals[0].x+=1234.
            if 'reveal' in mode:f.originals[0].visible=True
            before=(len(f.adds),len(f.moves));f.return_mode=(True,True);f.pump();f.pump()
            self.assertEqual((len(f.adds),len(f.moves)),before);self.assertIs(f.pending(),record);f.conserved()
    def test_inv07_output_add_and_failed_material_return_custody_changes(self):
        for boundary in ('output','return'):
            for mode in ('move','reveal','hide'):
                f=CraftSourceFixture(6);f.output_mode=f.return_mode=(False,False)
                def callback(u,i):
                    target=f.originals[0]
                    if (boundary=='output' and i in f.products) or (boundary=='return' and i is target):
                        if mode=='move':target.x+=777.
                        elif mode=='reveal':target.visible=True
                        else:target.visible=False
                f.on_add=callback;self.assertEqual(f.commit(),0)
                record=f.pending();before=(len(f.adds),len(f.moves));f.return_mode=(True,True);f.pump()
                # Hide while already hidden / reveal while already visible are
                # idempotent and unobservable, not evidence of external change.
                if (boundary,mode) not in (('output','hide'),('return','reveal')):
                    self.assertEqual((len(f.adds),len(f.moves)),before);self.assertIs(f.pending(),record)
                f.conserved()
    def test_inv07_external_original_holder_hide_or_retype_never_overwritten(self):
        for mode in ('hide','retype','hide_retype'):
            with self.subTest(mode=mode):
                f=CraftSourceFixture(6);f.output_mode=f.return_mode=(False,False)
                self.assertEqual(f.commit(),0);record=f.pending()
                f.pickup(f.farmer,record.material)
                if 'hide' in mode:record.material.visible=False
                if 'retype' in mode:record.material.raw=f.pools[2][-1]
                before=(record.material.visible,record.material.raw,len(f.adds),len(f.moves))
                f.pump();f.pump();f.conserved()
                self.assertEqual((record.material.visible,record.material.raw,len(f.adds),len(f.moves)),before)
                self.assertIsNone(f.pending())
                self.assertTrue(any('原物品已在背包' in m for _,m in f.messages))
    def test_inv07_successful_return_callback_display_and_type_are_preserved(self):
        for original_visible in (False,True):
            for mode in ('unchanged','hide','retype','hide_retype'):
                with self.subTest(original_visible=original_visible,mode=mode):
                    f=CraftSourceFixture(6);f.originals[0].visible=original_visible
                    f.output_mode=(False,False)
                    def callback(u,i):
                        if i is not f.originals[0]:return
                        if 'hide' in mode:i.visible=False
                        if 'retype' in mode:i.raw=f.pools[2][-1]
                    f.on_add=callback
                    self.assertEqual(f.commit(),0);f.conserved()
                    self.assertIsNone(f.pending());self.assertIs(f.originals[0].holder,f.farmer)
                    self.assertEqual(f.originals[0].visible,False if 'hide' in mode else original_visible)
                    self.assertEqual(f.originals[0].raw,f.pools[2][-1] if 'retype' in mode else f.pools[1][0])
    def test_inv08_one_record_per_player_max_four_and_watch_shared_lifecycle(self):
        f=CraftSourceFixture(6)
        records=[]
        for owner in range(4):
            u=f.unit(owner);i=f.item(f.pools[1][0])
            record=f.n['tdCraftReserveRecovery'](u,i,i.raw,1,0);records.append(record)
            self.assertIsNone(f.n['tdCraftReserveRecovery'](u,i,i.raw,1,0))
        self.assertEqual(f.n['tdCraftRecoveryCount'],4)
        self.assertEqual(f.commit(),0);self.assertEqual(f.detaches,[]);f.conserved()
        for r in records:f.n['tdCraftReleaseRecovery'](r)
        self.assertEqual(f.n['tdCraftRecoveryCount'],0)
        self.assertTrue(f.backend.available(1,f.originals[0].raw))
    def test_inv09_gameover_stops_actual_pump_and_truthful_notification(self):
        f=CraftSourceFixture(6);f.output_mode=(False,False)
        f.on_add=lambda u,i:setattr(f,'over',True) if i in f.products else None
        self.assertEqual(f.commit(),0);self.assertIsNotNone(f.pending());f.conserved()
        self.assertTrue(any('自动归还已停止' in m for _,m in f.messages))
        self.assertFalse(any('系统会自动重试' in m for _,m in f.messages))
        before=(len(f.adds),len(f.moves));f.pump();f.pump()
        self.assertEqual((len(f.adds),len(f.moves)),before)
    def test_inv09_external_holder_retype_delete_and_idempotent_cleanup(self):
        for mode in ('foreign','raw','delete'):
            f=CraftSourceFixture(6);f.output_mode=f.return_mode=(False,False);f.commit()
            if mode=='foreign':f.pickup(f.other,f.originals[0])
            elif mode=='raw':f.originals[0].raw=f.pools[2][0]
            else:f.originals[0].raw=0
            before=(len(f.adds),len(f.moves));f.pump();f.pump()
            self.assertEqual((len(f.adds),len(f.moves)),before);f.conserved()
            f.backend.discardResult(1);f.backend.discardResult(1);f.destroy(f.backend);f.conserved()

if __name__=='__main__':unittest.main()

class InventoryCraftSourceMutationTests(unittest.TestCase):
    def mutated(self,package,old,new,**kwargs):
        def change(name,text):
            if name!=package:return text
            self.assertIn(old,text);return text.replace(old,new,1)
        return CraftSourceFixture(source_mutation=change,**kwargs)
    def test_postadd_material_revalidation_mutation_rejected(self):
        f=self.mutated('TDCraftingNativeBackend','let unchanged = sourcesValid(first, second, third)','let unchanged = true')
        f.on_add=lambda u,i:f.pickup(f.other,f.originals[1]) if i in f.products else None
        with self.assertRaises(AssertionError):self.assertEqual(f.commit(),0)
    def test_output_actual_membership_mutation_rejected(self):
        f=self.mutated('TDCraftingNativeBackend',' and tdCraftItemInInventory(farmer, output)','')
        f.output_mode=(True,False)
        with self.assertRaises(AssertionError):self.assertEqual(f.commit(),0)
    def test_recovery_record_loss_mutation_rejected(self):
        f=self.mutated('TDCraftingNativeBackend','tdCraftCancelRecovery(record, externalChanged)','tdCraftReleaseRecovery(record)',count=6)
        f.output_mode=f.return_mode=(False,False);self.assertEqual(f.commit(),0)
        with self.assertRaises(AssertionError):self.assertIsNotNone(f.pending())
    def test_custody_position_and_visibility_mutation_rejected(self):
        old='return record.custodyReady and not IsItemVisible(record.material) and GetItemX(record.material) == record.custodyX and GetItemY(record.material) == record.custodyY'
        f=self.mutated('TDCraftingRecovery',old,'return true',count=6)
        f.output_mode=f.return_mode=(False,False);f.commit();record=f.pending()
        f.originals[0].x+=123.;f.return_mode=(True,True);f.pump()
        with self.assertRaises(AssertionError):self.assertIs(f.pending(),record)
    def test_synchronous_pile_notification_mutation_rejected(self):
        old='\t\tDisplayTimedTextToPlayer(record.owner, 0, 0, 5.0, "原材料已退回本路" + tdItemQualityName(record.quality) + "材料堆。")'
        f=self.mutated('TDCraftingRecovery',old,'\t\tif record.notified\n\t'+old,count=6)
        f.output_mode=f.return_mode=(False,False);f.pile_available=True;f.commit()
        with self.assertRaises(AssertionError):self.assertTrue(any('材料堆' in m for _,m in f.messages))
    def test_gameover_retry_text_mutation_rejected(self):
        old='if tdIsGameOver()\n\t\t\tDisplayTimedTextToPlayer(record.owner, 0, 0, 5.0, "原材料已保留；游戏已结束，自动归还已停止。")'
        f=self.mutated('TDCraftingRecovery',old,old.replace('if tdIsGameOver()','if false'),count=6)
        f.output_mode=(False,False);f.on_add=lambda u,i:setattr(f,'over',True) if i in f.products else None;f.commit()
        with self.assertRaises(AssertionError):self.assertFalse(any('系统会自动重试' in m for _,m in f.messages))
    def test_inventory_terrain_dependency_mutation_rejected(self):
        old='\t\tSetItemVisible(output, false)'
        f=self.mutated('TDCraftingNativeBackend',old,'\t\tif inventory\n\t\t\ttdTryPlaceItemNear(output, lane, origin, false)\n'+old)
        with self.assertRaisesRegex(AssertionError,'nearby-terrain'):f.commit()
    def test_other_backend_native_owner_guard_mutation_rejected(self):
        f=self.mutated('TDCraftingNativeBackend',' or tdCraftBackendCommitOwner != 0','')
        other=Backend(f,f.farmer,True,0);observed=[]
        def callback(i):
            f.on_create=None;observed.append(other.prepareResult(rawcode(f.expected)))
        f.on_create=callback;f.commit()
        with self.assertRaises(AssertionError):self.assertEqual(observed,[0])
    def test_shared_pickup_observer_must_not_reset_history(self):
        f=self.mutated('TDCraftingItemWatch','record.refs += 1','record.refs += 1\n\t\trecord.pickupSerial = 0')
        f.pickup(f.farmer,f.originals[0],0)
        other=Backend(f,f.farmer,True,0);other.capture(NS(capture=lambda *a:True),f.originals[0],0)
        with self.assertRaises(AssertionError):self.assertFalse(f.backend.available(1,f.originals[0].raw))
    def test_three_slot_delivering_phase_guard_mutation_is_observable(self):
        f=self.mutated('TDCraftingNativeBackend',
            'phase != TD_CRAFT_PHASE_PREPARED or tdCraftBackendCommitOwner != this castTo int',
            'tdCraftBackendCommitOwner != this castTo int',count=3)
        observed=[]
        def callback(u,i):
            if i not in f.products:return
            f.on_add=None;observed.append(f.backend.consumeThree(1,2,3))
        f.on_add=callback
        self.assertEqual(f.commit(),0)
        with self.assertRaises(AssertionError):self.assertEqual(observed,[False])
        self.assertEqual(observed,[True]);self.assertEqual(f.removed[:3],f.originals[:3])
    def test_cancel_recovery_early_owner_release_mutation_is_observable(self):
        f=self.mutated('TDCraftingNativeBackend',
            '\t\t\ttdCraftCancelRecovery(record, externalChanged)',
            '\t\t\treleaseCommitOwner()\n\t\t\ttdCraftCancelRecovery(record, externalChanged)',count=6)
        other=Backend(f,f.farmer,True,0);observed=[];f.output_mode=(False,False)
        f.on_add=lambda u,i:observed.append(other.prepareResult(rawcode(f.expected))) if i is f.originals[0] else None
        self.assertEqual(f.commit(),0)
        with self.assertRaises(AssertionError):self.assertEqual(observed,[0])
        self.assertEqual(observed,[1]);self.assertEqual(len(f.products),2)
    def test_successful_return_visibility_override_mutation_is_observable(self):
        old='\t\t\t// Do not overwrite the successful return callback\'s newer display/type.'
        f=self.mutated('TDCraftingRecovery',old,'\t\t\tSetItemVisible(material, record.originalVisible)\n'+old,count=6)
        f.output_mode=(False,False)
        f.on_add=lambda u,i:setattr(i,'visible',False) if i is f.originals[0] else None
        self.assertEqual(f.commit(),0)
        with self.assertRaises(AssertionError):self.assertFalse(f.originals[0].visible)
