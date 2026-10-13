#!/usr/bin/env python3
"""Run A artifact gates with the reviewed B native Fx boundary.

The full DamageEvent assertions and pet(list) fixture are retained. Real packed
Fx/stdlib initialization is inherited from the elemental verifier; only native
rendering/world bounds/dummy setters/collections are modeled there. This adapter
keeps its recording history separate from A's exact effect/lightning history.
"""
import sys
import VerifyPetAttackArtifact as attack
from VerifyElementalPetArtifact import ElementRuntime

OriginalPetAttackRuntime = attack.PetAttackRuntime
class CompatiblePetAttackRuntime(ElementRuntime):
    def __init__(self,script):
        self.element_visual_history=[]
        super().__init__(script)
    def pet(self,skills,host=101,slot=0,level=3):
        return OriginalPetAttackRuntime.pet(self,skills,host,slot,level)
    def native(self,name,args):
        history=getattr(self,'visual_history',None)
        if history is None:return super().native(name,args)
        self.visual_history=self.element_visual_history
        try:return super().native(name,args)
        finally:self.visual_history=history

attack.PetAttackRuntime=CompatiblePetAttackRuntime

def main():
    mode=sys.argv.pop(1)
    if mode=='attack':attack.main()
    elif mode=='visual':
        # Import after the native-only subclass is installed. No A assertions or
        # damage methods are replaced, and A's original pet(list) stays legal.
        import VerifyCombatVisualArtifact as visual
        visual.main()
    else:raise ValueError('Expected attack or visual gate')
if __name__=='__main__':main()
