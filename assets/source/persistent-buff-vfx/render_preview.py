"""Offline orthographic rasterization of exported/reparsed MDX triangles only.

The optional gray host is an invented 145-unit neutral proxy, not a Warcraft unit.
Effect triangles depth-test against it but do not write depth, matching layer flags.
"""
from pathlib import Path
import json
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
D = json.loads((ROOT/'validation-frames.json').read_text())
OUT = ROOT/'previews'
OUT.mkdir(exist_ok=True)
FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
SMALL = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
BG = np.array([17., 24., 28.])
RIGHT = np.array([math.sqrt(3)/2, -.5, 0])
SCREEN_Y = np.array([.5*.6, math.sqrt(3)/2*.6, -.8])
DEPTH = np.array([.5*.8, math.sqrt(3)/2*.8, .6])


def raster(m, frame, size=256, host=True):
    # Two-times supersampling. No invented glow, texture or particle sprites.
    n = size*2
    pixels = np.broadcast_to(BG, (n, n, 3)).copy()
    zbuffer = np.full((n, n), -np.inf)
    def project(v):
        v = np.asarray(v)
        return np.column_stack((n*.5+v@RIGHT*n/190,
                                n*.94+v@SCREEN_Y*n/190, v@DEPTH))
    def triangle(v, color, additive=False, alpha=1):
        p = project(v)
        x0=max(0, int(np.floor(p[:,0].min())))
        x1=min(n-1, int(np.ceil(p[:,0].max())))
        y0=max(0, int(np.floor(p[:,1].min())))
        y1=min(n-1, int(np.ceil(p[:,1].max())))
        if x0>x1 or y0>y1:
            return
        a,b,c=p
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-8:
            return
        xx,yy=np.meshgrid(np.arange(x0,x1+1)+.5, np.arange(y0,y1+1)+.5)
        w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
        w2=1-w0-w1
        z=w0*a[2]+w1*b[2]+w2*c[2]
        zb=zbuffer[y0:y1+1,x0:x1+1]
        visible=(w0>=-1e-7)&(w1>=-1e-7)&(w2>=-1e-7)&(z>=zb-1e-5)
        region=pixels[y0:y1+1,x0:x1+1]
        if additive:
            region[visible]=np.minimum(255, region[visible]+np.asarray(color)*alpha)
        else:
            region[visible]=color
            zb[visible]=z[visible]
    if host:
        # A muted 12-sided taper with no art resembling a native game tower.
        v=[]
        for z,radius in [(0,26),(145,21)]:
            for i in range(12):
                a=i*math.tau/12
                v.append([radius*math.cos(a),radius*math.sin(a),z])
        for i in range(12):
            j=(i+1)%12
            col=np.array([55,65,68])*(.82+.14*math.sin(i*math.tau/12+1))
            triangle([v[i],v[j],v[12+j]],col)
            triangle([v[i],v[12+j],v[12+i]],col)
        for i in range(1,11):
            triangle([v[12],v[12+i],v[12+i+1]], [76,86,90])
    for gi,g in enumerate(m['geometry']):
        if frame['alpha'][gi]<=0:
            continue
        raw=np.asarray(g['vertices']).reshape((-1,3))
        matrix=np.asarray(frame['matrices'][g['bone']]).reshape((4,4))
        vs=(np.column_stack((raw,np.ones(len(raw))))@matrix)[:,:3]
        rgb=np.asarray(g['rgb'])*np.asarray(D['textureSampleRGBA'][:3])
        for indices in np.asarray(g['faces']).reshape((-1,3)):
            triangle(vs[indices],rgb,True,frame['alpha'][gi])
    return Image.fromarray(pixels.astype(np.uint8)).resize((size,size),Image.Resampling.LANCZOS)


def find_frame(m, time):
    if time=='Death':
        return next(f for f in m['frames'] if f['sequence']=='Death')
    return next(f for f in m['frames'] if f['sequence']=='Stand' and f['time']==time)


models={m['name']:m for m in D['models']}
names=['TDPetBuffFrenzyOrbit','TDPetBuffChargeSeal']
labels=['FRENZY / red fast counter-orbit','CHARGE / gold slow rune seals']
# A compact keyframe sheet: eight frames per effect including 50 ms and Death.
sheet=Image.new('RGB',(1160,1364),(12,18,22))
draw=ImageDraw.Draw(sheet)
draw.text((18,13),'EXPORTED MDX800 / REPARSED ANIMATED TRIANGLES',font=FONT,fill=(231,237,240))
draw.text((18,39),'Offline software blend and depth test. Gray 145-unit host is a neutral proxy, not a Warcraft model.',
          font=SMALL,fill=(164,182,192))
for mi,name in enumerate(names):
    m=models[name]
    times=[0,50,200,400,600,900,m['durationMs'],'Death']
    base=75+mi*638
    draw.text((18,base),f"{labels[mi]}   |   {m['triangles']} triangles   |   {m['durationMs']} ms loop",
              font=FONT,fill=(250,194,145) if mi==0 else (246,224,154))
    for k,time in enumerate(times):
        x=(k%4)*290+17
        y=base+31+(k//4)*300
        f=find_frame(m,time)
        sheet.paste(raster(m,f),(x,y))
        caption='Death / alpha 0' if time=='Death' else f'{time} ms / alpha {f["alpha"][0]:.2f}'
        draw.text((x,y+260),caption,font=SMALL,fill=(218,227,232))
draw.text((18,1340),'Loop endpoints match. Native attachment, tower fit, true Warcraft appearance and FPS are untested.',
          font=SMALL,fill=(164,182,192))
sheet.save(OUT/'frame-contact-sheet.png')

# Transparent-host-free, source-independent single keyframe previews.
for name in names:
    m=models[name]
    for host,label in [(True,'neutral-host'),(False,'effect-only')]:
        raster(m,find_frame(m,50),512,host).save(OUT/(name+'-50ms-'+label+'.png'))

# 3600 ms is the least common multiple of the 1200/1800 ms model periods.
frames=[]
for time in range(0,3600,20):
    im=Image.new('RGB',(690,360),(12,18,22))
    dr=ImageDraw.Draw(im)
    dr.text((12,10),'ACTUAL MDX LOOP TIMING / OFFLINE PREVIEW',font=FONT,fill=(231,237,240))
    for k,name in enumerate(names):
        m=models[name]
        f=find_frame(m,time%m['durationMs'])
        x=k*345+16
        im.paste(raster(m,f),(x,49))
        dr.text((x,310),labels[k],font=SMALL,fill=(241,213,170))
        dr.text((x,331),f"{time} ms elapsed | model {f['time']} ms",font=SMALL,fill=(164,182,192))
    frames.append(im)
frames[0].save(OUT/'actual-speed.gif',save_all=True,append_images=frames[1:],duration=20,
               loop=0,optimize=False)
print(OUT)
