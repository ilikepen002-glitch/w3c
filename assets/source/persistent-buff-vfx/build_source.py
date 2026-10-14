"""Original mesh-only tower-body buff candidates. Reuses the existing atlas."""
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parent
TEXTURE = r'Textures\TDPetVfxAtlas.blp'


def model(name, duration, color, core, description):
    return dict(name=name, durationMs=duration, texture=TEXTURE, color=color,
                coreColor=core, description=description, bones=[], parts=[])


def bone(m, name, z, turns=0, phase=0, xy_pulse=.025, lift=0):
    i = len(m['bones'])
    m['bones'].append(dict(name=name, pivot=[0, 0, z], turns=turns,
                           phase=phase, xyPulse=xy_pulse, lift=lift))
    return i


def poly(m, name, points, b, core=False):
    m['parts'].append(dict(name=name, vertices=points,
                           faces=[[0, i, i+1] for i in range(1, len(points)-1)],
                           bone=b, core=core))


def annulus(m, name, b, z, radius, width, start, sweep, segments,
            tilt=0, core=False, taper=False):
    def point(r, a):
        x, y = r*math.cos(a), r*math.sin(a)
        return [x, y*math.cos(tilt), z+y*math.sin(tilt)]
    for i in range(segments):
        a = math.radians(start+sweep*i/segments)
        c = math.radians(start+sweep*(i+1)/segments)
        wa = width*(.35+.65*math.sin(math.pi*i/segments)) if taper else width
        wc = width*(.35+.65*math.sin(math.pi*(i+1)/segments)) if taper else width
        poly(m, name+str(i), [point(radius-wa, a), point(radius, a),
                             point(radius, c), point(radius-wc, c)], b, core)


def radial_polygon(m, name, b, radius, angle, z, shape, core=False):
    # Local u is tangential and v is vertical. Two-sided, thin magic strokes.
    a = math.radians(angle)
    points = [[radius*math.cos(a)-u*math.sin(a),
               radius*math.sin(a)+u*math.cos(a), z+v] for u, v in shape]
    poly(m, name, points, b, core)


m = model('TDPetBuffFrenzyOrbit', 1200, [1, .045, .015], [1, .47, .12],
          'Two counter-rotating canted broken flame arcs with sharp outward teeth. '
          'Fast 1200 ms orbit and three 400 ms red energy pulses per loop.')
for k, (z, radius, tilt, start, turns) in enumerate([
        (82, 52, .36, -30, 1), (113, 55, -.31, 145, -1)]):
    b = bone(m, 'FrenzyOrbit'+str(k), z, turns, k*.5, .022)
    annulus(m, 'red arc'+str(k), b, z, radius, 7, start, 230, 16, tilt, taper=True)
    annulus(m, 'hot edge'+str(k), b, z+.7, radius-3.8, 1.9,
            start+8, 214, 16, tilt, True, True)
    for j, a in enumerate([start+42, start+190]):
        radial_polygon(m, 'flame fang'+str(k)+str(j), b, radius-1, a, z,
                       [(-9, -6), (-2, 1), (-3, 15), (5, 9), (10, 23), (7, -6)])
    for j, a in enumerate([start+20, start+211]):
        radial_polygon(m, 'ember sigil'+str(k)+str(j), b, radius-1, a, z+14,
                       [(-3, 0), (0, 6), (3, 0), (0, -6)], True)
models = [m]

m = model('TDPetBuffChargeSeal', 1800, [1, .67, .17], [1, .96, .72],
          'Three level interrupted seals and four upright diamond runes. '
          'Slow 1800 ms warm-white/gold breathing; no frenzy orbit.')
for k, (z, radius) in enumerate([(50, 49), (91, 53), (133, 45)]):
    b = bone(m, 'ChargeSeal'+str(k), z, 0, k/6, .035, 2)
    for j in range(4):
        annulus(m, 'seal band'+str(k)+str(j), b, z, radius, 3.8,
                j*90+12, 48, 3)
        a = math.radians(j*90+78)
        tangent = [-math.sin(a), math.cos(a)]
        radial = [math.cos(a), math.sin(a)]
        p = []
        for u, v in [(0, 3.7), (3, 0), (0, -3.7), (-3, 0)]:
            p.append([radius*radial[0]+u*tangent[0]+v*radial[0],
                      radius*radial[1]+u*tangent[1]+v*radial[1], z])
        poly(m, 'seal diamond'+str(k)+str(j), p, b)
        if k == 2:
            annulus(m, 'upper white inlay'+str(j), b, z+.8, radius-1, 1.4,
                    j*90+14, 44, 3, core=True)
b = bone(m, 'ChargeUprightRunes', 99, 0, 0, .02, 1.4)
for j in range(4):
    angle = j*90+24
    # Hollow diamond frame: retains the host's visible silhouette behind it.
    outside = [(-7, 0), (0, 14), (7, 0), (0, -14)]
    inside = [(-4.5, 0), (0, 10), (4.5, 0), (0, -10)]
    for k in range(4):
        n = (k+1)%4
        radial_polygon(m, 'rune frame'+str(j)+str(k), b, 49, angle, 102,
                       [outside[k], outside[n], inside[n], inside[k]])
    radial_polygon(m, 'rune stem'+str(j), b, 49, angle, 82,
                   [(-1.6, -9), (1.6, -9), (1.6, 8), (-1.6, 8)])
    radial_polygon(m, 'rune crossbar'+str(j), b, 49, angle, 79,
                   [(-5, -1.4), (5, -1.4), (5, 1.4), (-5, 1.4)])
    radial_polygon(m, 'warm rune core'+str(j), b, 49.4, angle, 102,
                   [(-1.9, 0), (0, 5), (1.9, 0), (0, -5)], True)
models.append(m)

for m in models:
    m['triangles'] = sum(len(p['faces']) for p in m['parts'])
    assert m['triangles'] <= 200, m['triangles']
    (ROOT/(m['name']+'-source.json')).write_text(json.dumps(m, indent=2)+'\n')
    print(m['name'], m['triangles'])
