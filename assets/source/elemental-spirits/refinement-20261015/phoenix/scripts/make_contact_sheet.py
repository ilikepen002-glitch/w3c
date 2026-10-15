from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib
R=Path(__file__).resolve().parents[1];m=json.loads((R/'previews/contract-frames/render-manifest.json').read_text());assert m['sourceSha256']==hashlib.sha256((R/'output/QiLingPhoenix-Display.mdx').read_bytes()).hexdigest();w,h=320,256;im=Image.new('RGB',(1280,10*(h+42)+94),(13,17,24));draw=ImageDraw.Draw(im);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16);big=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',23);draw.text((14,10),'Phoenix compact: actual final MDX / sequence indices 0-9',font=big,fill='white');draw.text((14,42),'G4-8 body mesh + BLP readback. Native ribbons/Death FX omitted. Not a game screenshot.',font=font,fill=(180,195,215));draw.text((14,65),'Final SHA256: '+m['sourceSha256'][:24]+'...',font=font,fill=(180,195,215))
for fr in m['frames']:
 i=fr['index'];j=round(fr['phase']*3);x=j*w;y=94+i*(h+42);pic=Image.open(fr['file']).convert('RGB').resize((w,h));im.paste(pic,(x,y));draw.text((x+8,y+h+3),f'{i}: {fr["sequence"]} / {fr["phase"]:.0%}',font=font,fill='white')
im.save(R/'previews/Phoenix-contract-contact-sheet.jpg',quality=95)
