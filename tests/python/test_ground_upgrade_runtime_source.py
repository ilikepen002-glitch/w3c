"""Current real ground backend availability/guards; allocation/native models only."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from CraftingSourceHarness import CraftSourceFixture

class GroundUpgradeRuntimeSourceTests(unittest.TestCase):
    def test_four_lanes_three_result_qualities_direct_delivery_and_leftovers(self):
        for lane in range(4):
            for quality in (1,2,3):
                f=CraftSourceFixture(5,lane,quality,False);f.pile_available=True
                leftovers=[(i,i.x,i.y) for i in f.originals[3:]]
                self.assertEqual(f.commit(),1);self.assertEqual(f.products[0].pile,(lane,quality+1))
                self.assertEqual(f.removed,f.originals[:3]);self.assertEqual(f.detaches,[]);self.assertEqual(f.adds,[])
                for i,x,y in leftovers:self.assertEqual((i.x,i.y,i.raw),(x,y,f.pools[4][-1]))
                self.assertEqual(f.commit(),3)
    def test_failed_preparation_or_final_projection_never_consumes_materials(self):
        for blocked,rejected,expected in ((True,False,2),(False,True,0)):
            f=CraftSourceFixture(inventory=False);f.pile_available=not blocked;f.pile_reject=rejected
            self.assertEqual(f.commit(),expected);f.conserved()
            self.assertEqual(f.detaches,[]);self.assertEqual(f.adds,[])
    def test_failed_creation_and_foreign_lane_projection_keep_inputs(self):
        for mode in ('null','foreign'):
            f=CraftSourceFixture(lane=2,inventory=False);f.pile_available=True
            if mode=='null':f.create_mode='null'
            else:
                original=f.n['tdTryPlaceItemInPile']
                def wrong(*args):
                    index=original(*args);args[0].x=1000.;return index
                f.n['tdTryPlaceItemInPile']=wrong
            self.assertEqual(f.commit(),2 if mode=='null' else 0);f.conserved()
    def test_source_invalidation_after_placement_discards_only_hidden_output(self):
        for mode in ('pickup','hidden','owned','circle','lane','raw'):
            f=CraftSourceFixture(inventory=False);f.pile_available=True
            original=f.n['tdTryPlaceItemInPile']
            def change(*args):
                index=original(*args);i=f.originals[1]
                if mode=='pickup':f.pickup(f.other,i);f.unlink(i)
                elif mode=='hidden':i.visible=False
                elif mode=='owned':f.pickup(f.other,i)
                elif mode=='circle':i.y+=145.
                elif mode=='lane':i.x+=1000.
                else:i.raw=f.pools[2][0]
                return index
            f.n['tdTryPlaceItemInPile']=change
            self.assertEqual(f.commit(),0);f.conserved()
    def test_inventory_full_and_ground_source_terrain_separation(self):
        f=CraftSourceFixture(6);self.assertEqual(f.commit(),1);self.assertEqual(f.moves,[])
        f=CraftSourceFixture(inventory=False);f.pile_available=True
        self.assertEqual(f.commit(),1);self.assertEqual(len(f.moves),1)

if __name__=='__main__':unittest.main()
