"""Evidence layout only: no painting or editing texture assets."""
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];rows=json.loads((ROOT/'evidence/water-earth-hashes.json').read_text())
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
sheet=Image.new('RGB',(1536,1100),'#25313d');draw=ImageDraw.Draw(sheet);draw.text((20,12),'ACTUAL MDX + BLP / OFFLINE BLENDER / BEFORE vs REFINED',fill='white',font=font)
for k,row in enumerate(rows):
 n=row['model'];d=ROOT/'evidence'/n;col=k%3;rr=k//3;x=col*512;y=50+rr*525
 draw.text((x+15,y),n,fill='white',font=font)
 for j,kind in enumerate(['before','after']):
  im=Image.open(d/(kind+'-Stand-0.2.png')).convert('RGBA').resize((384,336),Image.Resampling.LANCZOS)
  # Both are actual mesh renders. Resize to a readable half-row, with exact same scale.
  im=im.resize((256,224),Image.Resampling.LANCZOS);sheet.paste(im,(x+j*256,y+35),im);draw.text((x+j*256+12,y+255),kind,fill='#bed6e8',font=small)
 # Preserve full-size final below each paired comparison.
 im=Image.open(d/'after-Stand-0.2.png').convert('RGBA').resize((256,224),Image.Resampling.LANCZOS);sheet.paste(im,(x+128,y+278),im)
sheet.save(ROOT/'evidence/water-earth-before-after.png')
for row in rows:
 n=row['model'];d=ROOT/'evidence'/n;sheet=Image.new('RGB',(930,1720),'#25313d');draw=ImageDraw.Draw(sheet);draw.text((20,12),n+' | actual final MDX sampled poses (offline)',fill='white',font=font)
 for r,seq in enumerate(['Walk','Display Float','Display Jump','Display Spin','Display Sleep','Display Cast']):
  y=50+r*275;draw.text((12,y),seq,fill='#bed6e8',font=small)
  for c,u in enumerate([.2,.5,.8]):
   im=Image.open(d/('after-'+seq.replace(' ','-')+'-'+str(u)+'.png')).convert('RGBA');sheet.paste(im,(c*310,y+12),im)
 sheet.save(d/'animation-contact-sheet.png')
