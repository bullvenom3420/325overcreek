"""Write assets/mobile/model-data.js for the phone/desktop WebGL viewer (meters, Y up, front faces +Z)."""
import sys, os, json, base64
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import house, render
FT = 0.3048
CX, CY = 31.5, 34.25
def tf(p): return [(p[0] - CX) * FT, p[2] * FT, -(p[1] - CY) * FT]
COL = {'wall': [0.93, 0.92, 0.89], 'roof': [0.875, 0.865, 0.845], 'glass': [0.66, 0.67, 0.70],
       'void': [0.3, 0.3, 0.32], 'trim': [0.96, 0.955, 0.94]}
pos, nrm, col, lines, seen = [], [], [], [], set()
for pts, mat in house.geometry():
    tris, n = render.triangulate(pts)
    N = np.array([n[0], n[2], -n[1]])
    for t in tris:
        for i in t:
            pos += tf(pts[i]); nrm += list(N); col += COL[mat]
    if mat in ('glass',):
        continue
    k = len(pts)
    for i in range(k):
        a = tuple(round(v, 3) for v in tf(pts[i])); b = tuple(round(v, 3) for v in tf(pts[(i + 1) % k]))
        key = tuple(sorted([a, b]))
        if key in seen or a == b:
            continue
        seen.add(key); lines += list(a) + list(b)
pets = {}
for key, q in house.PET_QUADS.items():
    o, U, V = np.array(q['o']), np.array(q['U']), np.array(q['V'])
    pets[key] = dict(tl=tf(o + V), tr=tf(o + U + V), bl=tf(o), br=tf(o + U))
def b64(a): return base64.b64encode(np.asarray(a, np.float32).tobytes()).decode()
out = os.path.join(os.path.dirname(__file__), '..', 'assets', 'mobile', 'model-data.js')
open(out, 'w').write('window.OVERCREEK_MODEL={pos:"%s",nrm:"%s",col:"%s",lines:"%s",pets:%s};\n'
                     % (b64(pos), b64(nrm), b64(col), b64(lines), json.dumps(pets)))
print(len(pos) // 9, 'tris', len(lines) // 6, 'lines', os.path.getsize(out), 'bytes')
