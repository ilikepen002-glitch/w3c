"""Actual reparsed MDX triangle/bone/alpha preview. This is not a game capture."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json, math
R=Path(__file__).resolve().parent
D=json.loads((R/'parsed-preview-data.json').read_text())
O=R/'previews';O.mkdir(exist_ok=True)
FONT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
SMALL=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
BG=(19,29,27)

def pose(g,i,f):
    b=f['bones'][g['matrixIndices'][sum(g['matrixGroups'][:g['vertexGroups'][i]])]]
    p=[(g['vertices'][i*3+k]-b['pivot'][k])*b['scale'][k] for k in range(3)]
    q=b['rotation'];u=q[:3];s=q[3];dot=sum(u[k]*p[k] for k in range(3));uu=sum(x*x for x in u)
    cross=[u[1]*p[2]-u[2]*p[1],u[2]*p[0]-u[0]*p[2],u[0]*p[1]-u[1]*p[0]]
    return [2*dot*u[k]+(s*s-uu)*p[k]+2*s*cross[k]+b['pivot'][k]+b['translation'][k] for k in range(3)]

def render(m,f,size=340):
    im=Image.new('RGB',(size,size),BG)
    dr=ImageDraw.Draw(im);sc=size/(m['radius']*2.5)
    def project(p):
        x,y,z=p;return (size*.50+(x*.866-y*.5)*sc,size*.59+(x*.5+y*.866)*.52*sc-z*.86*sc)
    # Thin dashed grey reference marks exact damage/query radius. Not asset geometry.
    for i in range(48):
        if i%2: continue
        a=i*math.tau/48;b=(i+1)*math.tau/48
        dr.line([project([m['radius']*math.cos(a),m['radius']*math.sin(a),0]),project([m['radius']*math.cos(b),m['radius']*math.sin(b),0])],fill=(49,66,61),width=1)
    faces=[]
    for gi,g in enumerate(m['geometry']):
        if f['alphas'][gi]*f['layers'][g['materialId']][0]<=0:continue
        vs=[pose(g,i,f) for i in range(len(g['vertices'])//3)]
        for j in range(0,len(g['faces']),3):
            p=[vs[i] for i in g['faces'][j:j+3]];xy=[project(v) for v in p]
            cross=(xy[1][0]-xy[0][0])*(xy[2][1]-xy[0][1])-(xy[1][1]-xy[0][1])*(xy[2][0]-xy[0][0])
            if cross<=1e-8:continue # Same one-sided geometry as exported material.
            depth=sum(v[0]*.43+v[1]*.745+v[2]*.52 for v in p)/3
            faces.append((depth,gi,xy))
    for _,gi,xy in sorted(faces):
        g=m['geometry'][gi];a=f['alphas'][gi]*f['layers'][g['materialId']][0]
        rgb=tuple(min(255,round(v*255)) for v in f['colors'][gi]);layer=Image.new('RGBA',(size,size),(0,0,0,0));ld=ImageDraw.Draw(layer);ld.polygon(xy,fill=(*rgb,round(a*255)))
        # Approximate Warcraft additive appearance, explicitly marked offline.
        if g['filterMode']==3:
            from PIL import ImageChops
            mask=layer.getchannel('A');light=Image.new('RGB',(size,size),rgb);light=Image.composite(light,Image.new('RGB',(size,size)),mask);im=ImageChops.add(im,light)
        else: im=Image.alpha_composite(im.convert('RGBA'),layer).convert('RGB')
    return im

def frame_at(m,t):
    return next(f for f in m['frames'] if f['elapsedMs']==t)

def sheet(models,times,name):
    tile=360;row=400;im=Image.new('RGB',(tile*len(models),82+row*len(times)),(12,18,21));dr=ImageDraw.Draw(im)
    dr.text((12,10),'EXPORTED / REPARSED MDX800 — OFFLINE SOFTWARE PREVIEW',font=FONT,fill=(232,239,242))
    dr.text((12,37),'Neutral looping cores. No automatic freeze / impact. Dashed grey guide is actual skill radius.',font=SMALL,fill=(164,184,190))
    dr.text((12,57),'Not a Warcraft screenshot. Approximate blending; native depth, camera, terrain fitting and FPS untested.',font=SMALL,fill=(164,184,190))
    for j,t in enumerate(times):
        for i,m in enumerate(models):
            x=i*tile;y=82+j*row;f=frame_at(m,t);im.paste(render(m,f),(x+10,y+40))
            dr.text((x+12,y+3),m['name'].replace('TDPetVfx','')+' / r'+str(m['radius']),font=FONT,fill=(235,211,165))
            dr.text((x+12,y+25),str(t)+' ms / '+f['sequence']+' / '+str(m['triangles'])+' triangles',font=SMALL,fill=(164,184,190))
            if t=='Death': dr.text((x+12,y+365),'All geoset and material alpha = 0',font=SMALL,fill=(173,193,187))
    im.save(O/name)

primary=[m for m in D['models'] if m['loop']]
sheet(primary[:5],[0,50,590,600,950,1200,1750,3750,'Death'],'neutral-core-contact-sheet.png')
sheet(primary[:5],[0,950,2000],'neutral-core-loop-boundary.png')
if len(primary)>5:
    sheet(primary[5:],[0,50,590,600,950,1200,1750,3750,'Death'],'flower-lotus-contact-sheet.png')
    sheet(primary[5:],[0,950,2000],'flower-lotus-loop-boundary.png')
for m in primary:
    frames=[render(m,frame_at(m,t)) for t in [0,50,590,600,740,750,940,950,1200,1750,1999,2000]]
    frames[0].save(O/(m['name']+'-offline.gif'),save_all=True,append_images=frames[1:],duration=[50,540,10,140,10,190,10,250,550,249,1,50],loop=0)
print(O)
