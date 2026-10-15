'use strict';
// Deterministic append-only tower-display poses. Never changes mesh/UV/rig/atlas
// or any key in the five original sequences. No per-frame source JSON is stored.
const SEQUENCES = [
  ['Display Float',8000,10000,true], ['Display Jump',10100,10900,false],
  ['Display Spin',11000,12200,false], ['Display Sleep',12300,15300,true],
  ['Display Cast',15400,16600,false],
];
const PROFILES = {
  SteelwingFalcon: 'wingbeats, talon tuck, banking turn, folded-wing rest, wing flare',
  BrassPangolin: 'tail sway, digging-paw hop, tail sweep, tucked curl, digging brace',
  LeafwingSpirit: 'four-leaf flutter, root kick, leafy twirl, folded leaves, arm/leaf flare',
  RootbudStag: 'ear/tail alertness, lifted forehoof, looking turn, head-down rest, antler brace',
  MosscapSprite: 'cap/leaf sway, root-foot hop, cap wobble, cap-down breathing, spore-cap thrust',
  TideWyrm: 'traveling spine wave, cresting surge, serpentine sway, slow spine breathing, head/fin charge',
  FrostFinManta: 'fin ripple, double fin beat, banking sweep, lowered fins, fin/head thrust',
  SnowManeOtter: 'tail/paw paddle, playful hop, tail wag turn, tucked paws, double-paw brace',
  EmberBird: 'wing/crest flutter, rising wingbeat, banking turn, folded-wing rest, crest/wing flare',
  MoltenHornSalamander: 'tail/head sway, low paw hop, tail sweep, low resting breath, horn brace',
  CinderTailFox: 'three-tail flutter, forepaw hop, three-tail fan, head-down rest, tail/head flare',
  RockShellTurtle: 'head/tail alertness, forefoot lift, shell rocking, tucked head/feet, shell/head brace',
  BoulderArmGibbon: 'arm/torso sway, heavy arm bounce, shoulder sway, crouched breathing, chest-level double-fist raise',
  SandSpiralSnail: 'eye-stalk/shell sway, shell bob, shell rocking, tucked stalks, stalk/head reach',
};

function pose(model, bone, action, u) {
  const t=[0,0,0], e=[0,0,0], s=[1,1,1];
  const w=Math.sin(2*Math.PI*u), pulse=Math.sin(Math.PI*u), beat=Math.sin(4*Math.PI*u);
  const sleep=action===8, idle=action===5, jump=action===6, spin=action===7, cast=action===9;
  const left=/Left/.test(bone), right=/Right/.test(bone), side=left?1:right?-1:0;
  const root=bone==='Root';
  if(root) {
    t[2]=idle?4+1.8*w:jump?12*pulse:spin?3*pulse:sleep?2:4*pulse;
    // A bounded looking/banking turn avoids full-turn shortest-arc ambiguity.
    if(spin)e[2]=.42*w;
  }
  const body=/Body|Torso|Spine$|Back|Trunk|Foot$|Chest/.test(bone)&&!root;
  const head=/Head|Face|Nose/.test(bone);
  const tail=/Tail/.test(bone);
  const limb=/Front|Hind|Rear|BackLeft|BackRight|Leg/.test(bone);
  if(body){t[2]=sleep?.32*w:idle?.4*w:jump?-1.5*pulse:cast?1.2*pulse:0;e[1]=sleep?.025*w:cast?-.08*pulse:jump?-.05*w:0;}
  if(head)e[1]=idle?.04*w:sleep?.14+.025*w:cast?-.14*pulse:jump?-.07*pulse:0;
  if(tail)e[2]=idle?.09*w:spin?.20*w:sleep?.08+.025*w:cast?.12*beat:.12*pulse;
  if(limb){e[1]=sleep?.12:jump?(bone.startsWith('Front')?-.20:.15)*pulse:cast?(bone.startsWith('Front')?-.12:.08)*pulse:0;if(jump)t[2]=3*pulse;}

  if(model==='SteelwingFalcon'||model==='EmberBird') {
    if(/Wing/.test(bone)) {
      const tip=/Tip/.test(bone), a=tip?.55:1;
      e[0]=side*a*(idle?.18*w:jump?.42*beat:spin?.20*w:sleep?-.32+.015*w:.50*pulse);
      if(sleep&&tip)e[2]=side*.12;
    }
    if(/Talons|FootLeft|FootRight/.test(bone))e[1]=sleep?.30:jump?.30*pulse:idle?.12:cast?.15*pulse:0;
    if(/Crest/.test(bone))e[1]=idle?.10*w:sleep?.08:cast?-.22*pulse:.12*beat*pulse;
    if(spin&&/Body|Chest/.test(bone))e[0]=.13*w;
  } else if(model==='FrostFinManta') {
    if(/Fin/.test(bone)){const tip=/Tip/.test(bone);e[0]=side*(tip?.65:1)*(idle?.16*w:jump?.32*beat:spin?.23*w:sleep?-.12+.018*w:.36*pulse);}
    if(bone==='MantaBody'&&spin)e[0]=.12*w;
    if(bone==='TailWhip')e[2]=(idle?.16:spin?.28:sleep?.04:.20)*w;
  } else if(model==='TideWyrm') {
    if(/^SwimSpine/.test(bone)){
      const i=Number(bone.slice(-1)), wave=Math.sin(2*Math.PI*u-i*.60);
      // Distributed, small rotations retain the continuous blended body seam.
      e[2]=idle?.052*wave:sleep?.026*wave:spin?.095*wave:jump?.09*wave*pulse:.065*wave*pulse;
      e[1]=jump?-.035*pulse:cast?-.035*pulse:0;
    }
    if(/Fin/.test(bone))e[0]=side*(idle?.10*w:sleep?.05*w:jump?.23*beat:cast?.24*pulse:.17*w);
    if(/Whisker/.test(bone))e[2]=side*(idle?.07*w:sleep?.025*w:cast?.16*pulse:.10*w);
    if(bone==='LongWaterHead'){e[1]=sleep?.08+.015*w:cast?-.18*pulse:jump?-.12*pulse:.035*w;}
  } else if(model==='LeafwingSpirit') {
    if(/^Leaf(Upper|Lower)/.test(bone)){
      const lower=/Lower/.test(bone), phase=lower?Math.PI/4:0;
      e[0]=side*(idle?.20*Math.sin(2*Math.PI*u+phase):jump?.32*beat:spin?.26*w:sleep?-.27+.025*w:.36*pulse);
    }
    if(/^Arm/.test(bone)){e[1]=sleep?.18:cast?-.44*pulse:jump?-.18*pulse:.06*w;}
    if(/^Root(Left|Right)/.test(bone)){e[1]=sleep?.15:jump?side*.28*pulse:cast?.12*pulse:side*.08*w;}
  } else if(model==='MosscapSprite') {
    if(bone==='WideMushroomCap'){e[0]=idle?.065*w:spin?.16*w:sleep?.06+.025*w:0;e[1]=jump?-.08*pulse:cast?-.16*pulse:0;}
    if(bone==='CapLeaf')e[0]=idle?.15*w:sleep?.05*w:cast?.24*beat*pulse:.18*w;
    if(/^VineArm/.test(bone)){e[1]=cast?-.42*pulse:sleep?.14:jump?-.18*pulse:0;e[0]=idle?side*.09*w:spin?side*.13*w:0;}
    if(/^RootFoot/.test(bone)){t[2]=jump?4*pulse:0;e[1]=sleep?.14:jump?side*.18*pulse:cast?-.08*pulse:0;}
  } else if(model==='RootbudStag') {
    // Forehoof rotates about (17,7,31), not translated away from its socket.
    if(/Ear/.test(bone))e[1]=idle?side*.12*w:sleep?-.16:cast?-.10*pulse:.06*w;
    if(bone==='FrontLeft'){e[1]=idle?-.08*(.5+.5*w):jump?-.40*pulse:cast?-1.00*pulse:sleep?.17:0;t[2]=jump?6*pulse:0;}
    if(cast&&bone==='FrontRight')e[1]=-.45*pulse;
    if(cast&&bone==='AlertDeerHead')e[1]=-.26*pulse;
    if(bone==='AlertDeerHead'&&spin)e[2]=.16*w;
  } else if(model==='BrassPangolin') {
    if(bone==='LowBack'){e[1]=sleep?-.10+.02*w:cast?-.10*pulse:0;}
    if(bone==='LongNose'){e[1]=sleep?.28+.015*w:cast?-.28*pulse:.05*w;}
    if(bone==='TailBase')e[1]=sleep?.24:jump?.12*pulse:0;
    if(bone==='TailTip')e[1]=sleep?.34:jump?.16*pulse:cast?-.10*pulse:0;
    if(/^DiggingArm/.test(bone)){e[1]=sleep?.18:jump?-.26*pulse:cast?-.95*pulse:0;t[2]=jump?4*pulse:0;}
  } else if(model==='SnowManeOtter') {
    if(/^Front.*Paw/.test(bone)){e[1]=idle?side*.12*w:jump?-.25*pulse:cast?-.95*pulse:sleep?.20:0;t[2]=0;if(cast)e[0]=side*.15*pulse;}
    if(bone==='LongOtterBody'&&spin)e[0]=.10*w;
    if(cast&&bone==='RoundOtterHead')e[1]=-.25*pulse;
  } else if(model==='MoltenHornSalamander') {
    if(bone==='BroadHead'){e[1]=sleep?.12+.02*w:cast?-.50*pulse:.045*w;}
    if(cast&&/^Front/.test(bone)){e[1]=-.85*pulse;e[0]=side*.12*pulse;}
    if(cast&&bone==='LowSpine')e[1]=-.12*pulse;
    if(jump&&root)t[2]=8*pulse;
  } else if(model==='CinderTailFox') {
    if(/Tail/.test(bone)){
      const sign=/Left/.test(bone)?1:/Right/.test(bone)?-1:0;
      e[2]=idle?.10*Math.sin(2*Math.PI*u+sign*.6):spin?.23*w:cast?sign*.16*pulse:sleep?.05*w:0;
      e[1]=cast?-.13*pulse:sleep?.12:jump?.15*pulse:0;
    }
  } else if(model==='RockShellTurtle') {
    if(jump&&root)t[2]=6*pulse;
    if(bone==='Body'&&spin)e[0]=.07*w;
    if(bone==='Head'&&sleep){t[0]=-4;e[1]=.07+.018*w;}
    if(limb&&sleep){t[1]=-side*2;e[1]=.10;}
    if(bone==='FrontLeft'&&jump){t[2]=5*pulse;e[1]=-.25*pulse;}
    if(bone==='Head'&&cast){t[0]=3*pulse;e[1]=-.13*pulse;}
  } else if(model==='BoulderArmGibbon') {
    // Shoulder pivots are (0,+/-18,47); -1.2rad brings low fists to chest/head height.
    if(/^.*Arm$/.test(bone)){e[1]=idle?side*.07*w:jump?-.26*pulse:spin?side*.13*w:sleep?.18:-1.20*pulse;}
    if(/Hand/.test(bone))e[1]=idle?.04*w:sleep?.08:cast?-.12*pulse:.08*pulse;
    if(/Leg/.test(bone))e[1]=sleep?.12:jump?.17*pulse:0;
    if(bone==='HeavyTorso'&&sleep)t[2]=-2+.35*w;
  } else if(model==='SandSpiralSnail') {
    if(jump&&root)t[2]=7*pulse;
    if(bone==='SpiralShell'){e[0]=idle?.04*w:spin?.11*w:sleep?.015*w:0;e[1]=jump?.08*pulse:cast?-.07*pulse:0;}
    if(/EyeStalk/.test(bone)){e[1]=sleep?.28+.015*w:cast?-.16*pulse:idle?.09*w:jump?-.13*pulse:0;e[2]=side*(idle?.07*w:spin?.09*w:cast?.11*pulse:0);}
    if(bone==='SlugHead'){t[0]=sleep?-2:cast?3*pulse:0;e[1]=sleep?.08:cast?-.12*pulse:0;}
  }
  // Euler x/y/z composition, continuous quaternion hemisphere between samples.
  const [x,y,z]=e.map(a=>a/2), sx=Math.sin(x),cx=Math.cos(x),sy=Math.sin(y),cy=Math.cos(y),sz=Math.sin(z),cz=Math.cos(z);
  return {KGTR:t,KGRT:[sx*cy*cz-cx*sy*sz,cx*sy*cz+sx*cy*sz,cx*cy*sz-sx*sy*cz,cx*cy*cz+sx*sy*sz],KGSC:s};
}

function api(runtime) {
  const base=runtime+'/mdx-m3-viewer/src', get=n=>require(base+'/parsers/mdlx/'+n+'.ts').default;
  return {Model:get('model'),Sequence:get('sequence'),Extent:get('extent'),createTypedSd:require(base+'/viewer/handlers/mdx/sd.ts').createTypedSd,...require(runtime+'/gl-matrix')};
}
function sampler(m,runtime) {
  const {createTypedSd,mat4,mat3}=api(runtime), nodes=new Map(m.bones.concat(m.helpers).map(n=>[n.objectId,n]));
  const tracks=new Map([...nodes].map(([id,n])=>[id,Object.fromEntries(n.animations.map(a=>[a.name,createTypedSd(m,a)]))]));
  const groups=m.geosets.map(g=>{let off=0;return Array.from(g.matrixGroups,c=>{const ids=Array.from(g.matrixIndices.slice(off,off+c));off+=c;return ids;});});
  return function(si,time,withNormals=false){
    const mats=new Map(), normalMats=new Map();
    function node(id){if(mats.has(id))return mats.get(id);const n=nodes.get(id),tr=tracks.get(id),t=new Float32Array(3),q=new Float32Array([0,0,0,1]),s=new Float32Array([1,1,1]);if(!n)throw Error('Missing bone '+id);
      for(const [tag,out]of[['KGTR',t],['KGRT',q],['KGSC',s]])if(tr[tag])tr[tag].getValue(out,si,time,time-m.sequences[si].interval[0]);
      const a=mat4.create();mat4.fromRotationTranslationScaleOrigin(a,q,t,s,m.pivotPoints[id]);if(n.parentId!==-1)mat4.mul(a,node(n.parentId),a);mats.set(id,a);if(withNormals){const nm=mat3.create();mat3.normalFromMat4(nm,a);normalMats.set(id,nm);}return a;
    }
    return m.geosets.map((g,gi)=>{const vertices=new Float32Array(g.vertices.length),normals=withNormals?new Float32Array(g.normals.length):null;
      for(let i=0;i<g.vertices.length;i+=3){const ids=groups[gi][g.vertexGroups[i/3]],x=g.vertices[i],y=g.vertices[i+1],z=g.vertices[i+2];let ox=0,oy=0,oz=0,nx=0,ny=0,nz=0;
        for(const id of ids){const a=node(id);ox+=a[0]*x+a[4]*y+a[8]*z+a[12];oy+=a[1]*x+a[5]*y+a[9]*z+a[13];oz+=a[2]*x+a[6]*y+a[10]*z+a[14];if(withNormals){const b=normalMats.get(id),x=g.normals[i],y=g.normals[i+1],z=g.normals[i+2];nx+=b[0]*x+b[3]*y+b[6]*z;ny+=b[1]*x+b[4]*y+b[7]*z;nz+=b[2]*x+b[5]*y+b[8]*z;}}
        vertices[i]=ox/ids.length;vertices[i+1]=oy/ids.length;vertices[i+2]=oz/ids.length;if(withNormals){const len=Math.hypot(nx,ny,nz)||1;normals[i]=nx/len;normals[i+1]=ny/len;normals[i+2]=nz/len;}
      }return {vertices,normals};
    });
  };
}
function deriveNewBounds(m,runtime) {
  const {Extent}=api(runtime), sample=sampler(m,runtime);
  for(let si=5;si<10;si++){
    const sequence=m.sequences[si],lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
    const times=new Set(Array.from({length:129},(_,i)=>sequence.interval[0]+(sequence.interval[1]-sequence.interval[0])*i/128));
    for(const b of m.bones)for(const a of b.animations)for(const f of a.frames)if(f>=sequence.interval[0]&&f<=sequence.interval[1])times.add(f);
    for(const time of times)for(const g of sample(si,time))for(let i=0;i<g.vertices.length;i++){const v=g.vertices[i];lo[i%3]=Math.min(lo[i%3],v);hi[i%3]=Math.max(hi[i%3],v);}
    const e=new Extent();e.min.set(lo.map(v=>v-2));e.max.set(hi.map(v=>v+2));e.boundsRadius=Math.hypot(...e.min.map((v,k)=>Math.max(Math.abs(v),Math.abs(e.max[k]))));sequence.extent=e;
    for(const g of m.geosets){g.sequenceExtents.push(e);for(let k=0;k<3;k++){g.extent.min[k]=Math.min(g.extent.min[k],e.min[k]);g.extent.max[k]=Math.max(g.extent.max[k],e.max[k]);}g.extent.boundsRadius=Math.max(g.extent.boundsRadius,e.boundsRadius);}
    for(let k=0;k<3;k++){m.extent.min[k]=Math.min(m.extent.min[k],e.min[k]);m.extent.max[k]=Math.max(m.extent.max[k],e.max[k]);}m.extent.boundsRadius=Math.max(m.extent.boundsRadius,e.boundsRadius);
  }
}
function append(m,model,runtime) {
  if(!PROFILES[model])throw Error('Unknown display profile '+model);
  if(m.sequences.length!==5)throw Error('Expected exactly five original sequences; never append twice');
  const {Sequence}=api(runtime);
  for(const [name,start,end,loop]of SEQUENCES){const a=new Sequence();a.name=name;a.interval.set([start,end]);a.flags=loop?0:1;m.sequences.push(a);}
  for(const b of m.bones){const tracks=Object.fromEntries(b.animations.map(a=>[a.name,a]));for(const tag of ['KGTR','KGRT','KGSC'])if(!tracks[tag]||tracks[tag].interpolationType!==1||tracks[tag].globalSequenceId!==-1)throw Error('Unsupported original track '+b.name+'/'+tag);
    for(let si=0;si<5;si++){const [,start,end]=SEQUENCES[si];let previous=null;
      for(let i=0;i<=16;i++){const values=pose(model,b.name,si+5,i/16),q=values.KGRT;if(previous&&q.reduce((n,v,k)=>n+v*previous[k],0)<0)for(let k=0;k<4;k++)q[k]=-q[k];previous=q;
        for(const tag of ['KGTR','KGRT','KGSC']){tracks[tag].frames.push(Math.round(start+(end-start)*i/16));tracks[tag].values.push(new Float32Array(values[tag]));}
      }
    }
  }
  deriveNewBounds(m,runtime);return m;
}
module.exports={SEQUENCES,PROFILES,pose,api,sampler,append};
