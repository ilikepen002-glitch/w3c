#!/usr/bin/env python3
"""Actual-source cosmetic/geometry gate. No compiled JASS or client rendering claim."""
from pathlib import Path
import argparse, hashlib, json, math, re, subprocess
from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources, uncomment
from VerifyEquipmentAbilityArtifact import require

ROOT = Path(__file__).resolve().parents[1]
BASE = '4567e0dd7a1decb80ea78269b57eec5c95bbab7a'
FILES = ('pets/TDPetActiveDirect.wurst', 'pets/TDPetActivePeriodic.wurst', 'pets/TDPetActiveRuntime.wurst')
VISUAL = 'pets/TDPetActiveVisuals.wurst'
DATA = 'pets/TDPetActiveVisualData.wurst'

def mechanics(text, runtime=False):
    source = uncomment(text)
    # Only the old 36 pure-visual placement loop disappears. No target loop is elided.
    source = re.sub(r'^\t\t\tlet side = vec2\(-this.direction.y, this.direction.x\)\n'
                    r'\t\t\tfor index = -1 to 1\n'
                    r'\t\t\t\tthis.addVisual\(TD_PET_VFX_FAN, [^\n]+\n', '', source, flags=re.M)
    source = re.sub(r'^\s*this\.(?:visual\w+|addVisual|clearVisuals)\([^\n]*\)\s*$', '', source, flags=re.M)
    source = re.sub(r'^\s*cast\.visualPrepare\(\)\s*$', '', source, flags=re.M)
    if runtime:
        before = '''\t\tboolean continuing
\t\tif skill == 19 or skill == 20 or skill == 23 or skill == 27 or skill == 28 or skill == 29 or skill == 32 or skill == 35 or skill == 36
\t\t\tcontinuing = this.stepDirect(now)
\t\telse
\t\t\tcontinuing = this.stepPeriodic(now)
\t\tif not continuing
\t\treturn continuing'''
        after = '''\t\tif skill == 19 or skill == 20 or skill == 23 or skill == 27 or skill == 28 or skill == 29 or skill == 32 or skill == 35 or skill == 36
\t\t\treturn this.stepDirect(now)
\t\treturn this.stepPeriodic(now)'''
        compact = '\n'.join(line.rstrip() for line in source.splitlines() if line.strip())
        require(before in compact or 'boolean continuing' not in compact, 'Unexpected active dispatcher wrapper')
        source = compact.replace(before, after)
    return '\n'.join(line.strip() for line in source.splitlines() if line.strip())

def verify(sources, baseline):
    for path in FILES:
        require(mechanics(sources[path], path == FILES[2]) == mechanics(baseline[path], path == FILES[2]),
                'Damage/control/target/clock/fence logic changed: '+path)
    for path in (VISUAL, DATA):
        code = uncomment(sources[path])
        require(not re.search(r'\b(?:GetRandom\w*|DamageEvent|UnitDamageTarget|damageTarget|hitPrimary|hit|control|slow|CreateUnit|Issue\w*Order\w*|enumUnits\w*|TimerStart|doAfter|doPeriodically|AddLightning\w*|DestroyLightning|new Fx)\b', code),
                'Visual geometry acquired gameplay or a second lifecycle: '+path)
        require(not re.search(r'\bthis\.(?:stage|nextAt|expiresAt|damageBase|victimCount|markCount|controlCount)\s*(?:[+*/-]?=(?!=)|\+\+|--)', code),
                'Visual geometry writes battle state: '+path)
    v = uncomment(sources[VISUAL])
    require('visualFlight' not in v, 'Per-.05 destruction/recreation flight returned')
    tick = v[v.index('public function TDPetCastContext.visualTick'):v.index('public function TDPetCastContext.visualFinish')]
    require('addMoving(' not in tick and 'addVisual(' not in tick and 'clearVisuals(' not in tick,
            'Cosmetic motion directly creates/destroys on every scheduler tick')
    require('this.visualFrame != frame' in tick and 'this.visualSealPulse()' in tick,
            'Seal breathing is not one-second edge gated')
    require(v.count('this.clearMoving()') == 2, 'Mirror/meteor segment tails lost explicit Fx cleanup')
    required = ('visualInstantLine', 'visualStrike', 'visualSwordCut', 'visualSwordDrop',
                'visualSeedPulse', 'visualSeedBranch', 'visualFlowerContact', 'visualRoadSegment',
                'visualFreeze', 'visualIceBreak', 'visualVortexPulse', 'visualBrandPulse',
                'visualLotus', 'visualMeteorImpact', 'visualChainBurst', 'visualRockFan', 'visualFinish')
    callers = '\n'.join(sources[p] for p in FILES)
    for name in required:
        require('function TDPetCastContext.'+name+'(' in v and 'this.'+name+'(' in callers,
                'Stage visual is data-only/unwired: '+name)
    require('this.visualTrace(startPoint, endPoint, 2)' in v and 'this.lastPosition(this.stage + 1)' in v,
            'Weak seed/marked chain connection lost already-selected endpoint')
    require('TD_PET_VFX_VERDANT_ROOT : TD_PET_VFX_FAULT_RIDGE' in v,
            'Wood and stone road silhouettes merged')
    e = SourceScalarEvaluator(sources)
    call = lambda name,*args:e.call(name,list(args))
    scalar_cases=0
    for elapsed, expected in ((-1.,0.),(0.,0.),(.375,.5),(.75,1.),(3.,1.)):
        require(math.isclose(call('tdPetVisualProgress',elapsed,.75),expected),'Progress clamp changed');scalar_cases+=1
    for stage in range(4):
        for step, height in ((0.,260.),(.5,130.),(1.,0.)):
            require(math.isclose(call('tdPetVisualSwordHeight',stage+step,stage),height),'Sword round position changed');scalar_cases+=1
    for elapsed,height in ((0.,520.),(.375,260.),(.75,0.),(4.,0.)):
        require(math.isclose(call('tdPetVisualMeteorHeight',elapsed),height),'Meteor moved beyond existing .75 deadline');scalar_cases+=1
    for elapsed,radius in ((0.,180.),(.3,150.),(.6,120.),(.95,120.)):
        require(math.isclose(call('tdPetVisualMirrorRadius',elapsed),radius),'Mirror phase geometry changed');scalar_cases+=1
    for mask in range(8):
        for flower in range(3):
            bit=1<<flower
            require(call('tdPetVisualFlowerBit',flower)==bit and call('tdPetVisualFlowerAlreadyBloomed',mask,flower)==bool(mask&bit),
                    'Flower contact needs extra scans/repeated bloom');scalar_cases+=1
    return {'baselineCommit':BASE,'mechanicsFilesEqual':list(FILES),'scalarCases':scalar_cases,
            'wiredStageHelpers':len(required),'scope':'actual source, not compiled/client validation'}

def mutations(sources, baseline):
    changes=((VISUAL,'this.clearVisuals()','this.hitPrimary(2.0)'),
             (FILES[1],'this.area(this.center, 260.0, 0.45)','this.area(this.center, 260.0, 0.46)'),
             (DATA,'tdPetVisualProgress(elapsed, 0.75)','tdPetVisualProgress(elapsed, 1.00)'),
             (VISUAL,'this.clearMoving()','skip'))
    for path,before,after in changes:
        require(before in sources[path],'Missing mutation root')
        changed=dict(sources);changed[path]=changed[path].replace(before,after,1)
        try:verify(changed,baseline)
        except (AssertionError,ValueError):continue
        raise AssertionError('Visual source mutation escaped: '+before)
    return len(changes)

def assets():
    root=ROOT/'assets/source/elemental-vfx'
    manifest=json.loads((root/'production-manifest.json').read_text())
    total=0
    for asset in manifest['assets']:
        data=(ROOT/asset['file']).read_bytes();total+=len(data)
        require(len(data)==asset['bytes'] and hashlib.sha256(data).hexdigest()==asset['sha256'],'Frozen VFX asset differs')
        if asset['role']=='model':
            require(data[:4]==b'MDLX' and asset['triangles']<=600,'Wrong MDX/triangle ceiling')
            require(data.count(b'Textures\\TDPetVfxAtlas.blp')==1,'Unexpected model atlas path')
        else:require(data[:4]==b'BLP1' and asset['mipmaps']==7,'Wrong Classic BLP format')
    require(total==157068 and total<=180*1024,'Even raw VFX exceeds compressed B budget')
    for source in manifest['sourceFiles']:
        require(hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256'],'Reproducible source differs')
    return {'imports':4,'rawBytes':total,'models':3,'compressedLimit':180*1024,'nativeClientVerified':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);p.add_argument('--baseline-commit',default=BASE);args=p.parse_args()
    sources=read_sources(ROOT)
    baseline={path:subprocess.check_output(['git','show',args.baseline_commit+':wurst/'+path],cwd=ROOT,text=True) for path in FILES}
    result=verify(sources,baseline);result['baselineCommit']=args.baseline_commit;result['mutationRejections']=mutations(sources,baseline);result['assets']=assets()
    result['sourceSHA256']={path:hashlib.sha256(sources[path].encode()).hexdigest() for path in (*FILES,VISUAL,DATA)}
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
