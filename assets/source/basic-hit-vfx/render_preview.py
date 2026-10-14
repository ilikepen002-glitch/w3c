"""Software orthographic preview, from exported/reparsed MDX only. Not a game capture."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,math
R=Path(__file__).resolve().parent;D=json.loads((R/'validation-frames.json').read_text());O=R/'previews';O.mkdir(exist_ok=True)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
def render(m,frame,size=256,bg=(19,27,28)):
 im=Image.new('RGB',(size,size),bg);draw=ImageDraw.Draw(im);s=size/210
 def project(v):
  x,y,z=[v[k]*frame['scale'][k] for k in range(3)];return (size*.48+(x*.866-y*.5)*s,size*.6+(x*.5+y*.866)*.62*s-z*.78*s)
 faces=[]
 for gi,g in enumerate(m['geometry']):
  vs=[g['vertices'][i:i+3] for i in range(0,len(g['vertices']),3)]
  for i in range(0,len(g['faces']),3):
   p=[vs[j] for j in g['faces'][i:i+3]];depth=sum(v[0]*.5+v[1]*.866+v[2]*.8 for v in p)/3
   faces.append((depth,gi,p))
 for _,gi,p in sorted(faces):
  a=frame['alpha'][gi];g=m['geometry'][gi]
  rgb=[min(255,round(g['rgb'][c]*D['textureSampleRGBA'][c])) for c in range(3)]
  col=tuple(round(bg[c]*(1-a)+rgb[c]*a) for c in range(3))
  if a>0:draw.polygon([project(v) for v in p],fill=col)
 return im
frames=[]
for fi in range(37):
 im=Image.new('RGB',(1750,430),(13,19,22));dr=ImageDraw.Draw(im)
 dr.text((16,10),'EXPORTED MDX / OFFLINE FRAME PREVIEW',font=font,fill=(233,238,242))
 dr.text((16,36),'Fixed camera. Approximate blending. Not a Warcraft screenshot.',font=small,fill=(153,172,184))
 for k,m in enumerate(D['models']):
  x=k*350+20;f=m['frames'][fi];art=render(m,f);im.paste(art,(x,84));im.paste(art.resize((64,64),Image.Resampling.LANCZOS),(x+270,180))
  dr.text((x,62),m['name'].replace('TDPetHit','')+' / '+str(m['triangles'])+' tris',font=font,fill=(244,220,167))
  dr.text((x+270,255),'64 px',font=small,fill=(180,197,205))
  dr.text((x,349),f"{f['time']:03} ms   {f['sequence']}   alpha {f['alpha'][0]:.2f}",font=small,fill=(214,220,226))
  dr.text((x,371),f"Budgeted lifetime: {m['lifetimeMs']} ms",font=small,fill=(155,175,185))
 dr.text((16,406),'Complete fade in Stand; transparent Death. Native rendering unverified.',font=small,fill=(155,175,185));frames.append(im)
for name,dur in [('actual-speed.gif',10),('slow-4x.gif',40)]:frames[0].save(O/name,save_all=True,append_images=frames[1:],duration=[dur]*36+[600],loop=0,optimize=False)
frames[5].save(O/'readable-at-50ms.png')
# Sparse contact sheet from exact sampled times for alpha/shape review.
indices=[0,5,10,15,18,23,28];sheet=Image.new('RGB',(1750,430*len(indices)),(13,19,22))
for j,i in enumerate(indices):sheet.paste(frames[i],(0,j*430))
sheet.save(O/'frame-contact-sheet.png')
print(O)
