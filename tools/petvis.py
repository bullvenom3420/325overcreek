"""Per-frame screen data for the animated pet copies: quad corners (1600x1040 frame px),
whether the animated part is fully unobstructed, and the glass colour to back it with."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
import render, house
FR = sys.argv[1]; N = 120
W, H = 800, 520
CLIP = {'dog': 0.62, 'cat': 1.0}           # animated part: top fraction of the sprite
base = render.build_mesh(pets=False)
tri0 = base[0]
extra, ids = [], []
for k, key in enumerate(house.PET_QUADS):
    q = house.PET_QUADS[key]; o, U, V = (np.array(q[a], float) for a in 'oUV')
    c = CLIP[key]; lo = o + V * (1 - c)
    pts = [lo, lo + U, o + U + V, o + V]
    n = np.array(q['n']) * 0.004                 # a hair in front of the sprite plane
    for t in ((0, 1, 2), (0, 2, 3)):
        extra.append([pts[t[0]] + n, pts[t[1]] + n, pts[t[2]] + n]); ids.append(k + 1)
tri = np.concatenate([tri0, np.array(extra)])
tid = np.concatenate([np.zeros(len(tri0), int), np.array(ids)])
keys = list(house.PET_QUADS)
out = []
for i in range(N):
    th = 360.0 * i / N
    eye, f, r, u = render.camera(th, 11.0, 172.0)
    foc = (H / 2) / math.tan(math.radians(27.0) / 2); cx, cy = W / 2, H * 0.53
    rel = tri - eye; zc = rel @ f
    sx = cx + foc * (rel @ r) / zc; sy = cy - foc * (rel @ u) / zc
    _, ib = render.raster(sx, sy, 1.0 / zc, W, H, np.arange(len(tri)), True)
    hitid = np.where(ib >= 0, tid[np.where(ib >= 0, ib, 0)], 0)
    meta = json.load(open(os.path.join(FR, 'pets-%03d.json' % i)))
    im = np.asarray(Image.open(os.path.join(FR, 'frame-%03d.webp' % i)).convert('RGBA'))
    rec = {}
    for k, key in enumerate(keys):
        sel = np.where(tid == k + 1)[0]
        _, ib2 = render.raster(sx[sel], sy[sel], (1.0 / zc)[sel], W, H, np.arange(len(sel)), True)
        alone = (ib2 >= 0).sum(); seen = (hitid == k + 1).sum()
        q = house.PET_QUADS[key]
        facing = float(np.array(q['n']) @ (eye - np.array(q['o']))) > 0
        frac = seen / alone if alone else 0
        tl, tr, br, bl = [np.array(p) for p in meta[key]['corners']]
        su, sv = (0.08, 0.04) if key == 'dog' else (0.94, 0.04)
        p = tl + (tr - tl) * su + (bl - tl) * sv
        g = im[int(round(p[1])), int(round(p[0]))][:3].tolist()
        ok = bool(facing and alone > 30 and frac > 0.985)
        rec[key] = dict(c=[[round(v, 1) for v in pt] for pt in meta[key]['corners']], on=ok, g='#%02x%02x%02x' % tuple(g))
    out.append(rec)
json.dump(out, open(os.path.join(FR, 'pets-frames.json'), 'w'), separators=(',', ':'))
print('on dog', [i for i, r in enumerate(out) if r['dog']['on']])
print('on cat', [i for i, r in enumerate(out) if r['cat']['on']])
