"""Mock-up: 3-second phone intro in which the house falls together from above while it turns.
python3 buildanim.py OUTDIR shard nshards   |   python3 buildanim.py OUTDIR --encode OUT.mp4
Parts that overlap in the finished house fall as one rigid piece, so nothing ever passes
through anything else. Each piece starts above the top of the frame (nothing fades or pops in).
Falling pieces get motion blur (sub-frames blended); the spin itself is never blurred."""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
OUT = sys.argv[1]
FPS, DUR = 60, 3.0
N = int(FPS * DUR)
W, H = 1080, 780
if sys.argv[2] == '--encode':
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(OUT, 'b%03d.png'),
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an',
                    sys.argv[3]], check=True)
    sys.exit()
import render, house
house.INTERIOR[0] = True

# drop order: (group, start time s)
DROPS = [('ff', 0.00), ('sf', 0.38), ('gallery', 0.80), ('rail', 1.10), ('beam', 1.32), ('roof', 1.58)]
MERGE = {'roofD': 'sf', 'roofE': 'sf'}           # one-story roofs die into the second floor: fall with it
FALL = 0.57                                      # seconds per drop
LIFT = 78.0                                      # start height above landing (above the frame top)
SUB = 5                                          # motion-blur sub-frames while anything moves
SHUTTER = 0.5                                    # fraction of a frame the shutter is open

def drop(t, t0):
    s = min(max((t - t0) / FALL, 0.0), 1.0)
    return LIFT * (1 - s) ** 3                   # arrives fast from above, eases firmly into place

def offsets(t):
    return {g: drop(t, t0) for g, t0 in DROPS}

ease = lambda t: 0.5 - 0.5 * math.cos(math.pi * t)

# mesh with a drop group per triangle (same face order as render.build_mesh, so outlines/pets match)
geo = house.geometry()
fgroup = []
for (pts, mat), g in zip(geo, house.FACE_GROUP):
    if g == 'open':
        g = 'ff' if np.mean([p[2] for p in pts]) < house.P1 else 'sf'
    fgroup.append(MERGE.get(g, g))
mesh = render.build_mesh()
tri, fid = mesh[0], mesh[1]
names = [d[0] for d in DROPS]
tg = np.array([names.index(fgroup[f - 1]) for f in fid])      # pet quads take their window's face id
# pets for the intro: they move in once the house is finished, in ground-floor glass seen from the front
# (upstairs, the balcony railing would hide them). Huckleberry lies behind the front door's center glass;
# the cat peeks around the jamb of the dining room's French doors.
def glass_at(x0, x1, z0, y):
    for i, (pts, mat) in enumerate(geo):
        P = np.array(pts)
        if mat == 'glass' and abs(P[:, 1].mean() - y) < 0.02 and abs(P[:, 0].min() - x0) < 0.02 and abs(P[:, 0].max() - x1) < 0.02 and abs(P[:, 2].min() - z0) < 0.02:
            return i + 1
    raise SystemExit('window not found')
house.PET_QUADS['dog'] = dict(o=(30.50, 6.17 - 0.085, house.FF), U=(2.35, 0, 0), V=(0, 0, 2.35 * 600 / 900), n=(0, -1, 0),
                              fid=glass_at(29.17, 34.17, house.FF, 6.10), sprite='dog')
house.PET_QUADS['cat'] = dict(o=(41.83, 5 - 0.085, house.FF), U=(3.5, 0, 0), V=(0, 0, 4.5), n=(0, -1, 0),
                              fid=glass_at(41.83, 46.83, house.FF, 4.93), sprite='cat')
house.geometry = lambda: geo                    # keep these pet spots (a rebuild would reset them)
mesh = render.build_mesh()
tri, fid = mesh[0], mesh[1]
tg = np.array([names.index(fgroup[f - 1]) for f in fid])
PET_IN = {'dog': (2.40, 2.70), 'cat': (2.55, 2.85)}    # fade-in window (s), after the last piece lands
ELEV0, ELEV1 = 30.0, 11.0                               # camera starts looking down into the rooms
def elev_at(t):
    s = min(max(t / 2.55, 0.0), 1.0)
    return ELEV1 + (ELEV0 - ELEV1) * (1 - ease(s))
PET_O = {k: tuple(q['o']) for k, q in house.PET_QUADS.items()}
PET_G = {k: names.index(fgroup[q['fid'] - 1]) for k, q in house.PET_QUADS.items()}

BG = np.array([0x11, 0x17, 0x13], float)
yy, xx = np.mgrid[0:H, 0:W]
g = np.exp(-(((xx - W / 2) / (W * 0.42)) ** 2 + ((yy - H * 0.62) / (H * 0.30)) ** 2)) * np.sin(np.pi * yy / H) ** 2 * np.sin(np.pi * xx / W) ** 1.5
bgimg = Image.fromarray((BG[None, None] + g[..., None] * np.array([12, 17, 13])[None, None]).astype(np.uint8), 'RGB').convert('RGBA')

def shot(theta, t):
    off = offsets(t)
    dz = np.array([off[n] for n in names])[tg]
    m = list(mesh); tt = tri.copy(); tt[..., 2] += dz[:, None]; m[0] = tt
    for k in house.PET_QUADS:
        o = PET_O[k]; house.PET_QUADS[k]['o'] = (o[0], o[1], o[2] + off[names[PET_G[k]]])
    if all(v > 60 for v in off.values()):        # nothing in view yet
        return np.zeros((H, W, 4))
    for k, (a0, a1) in PET_IN.items():
        render.PET_FADE[k] = ease(min(max((t - a0) / (a1 - a0), 0.0), 1.0))
    im = render.render(theta, 1200, 780, elev=elev_at(t), mesh=m).crop((60, 0, 1140, 780))
    a = np.asarray(im).astype(float); rgb = a[..., :3]; al = a[..., 3:4] / 255
    lum = rgb.mean(-1, keepdims=True); al = np.where((lum < 90) & (al < 0.6), al * 0.25, al)
    return np.dstack([rgb * al, al])             # premultiplied

if __name__ == '__main__':
    k0, step = int(sys.argv[2]), int(sys.argv[3])
    os.makedirs(OUT, exist_ok=True)
    for k in range(k0, N, step):
        fn = os.path.join(OUT, 'b%03d.png' % k)
        if os.path.exists(fn):
            continue
        t = k / FPS
        theta = ease(k / (N - 1)) * 360.0
        moving = any(0 < (t - t0) < FALL + 1.0 / FPS for _, t0 in DROPS)
        ts = [t + (j / (SUB - 1) - 0.5) * SHUTTER / FPS for j in range(SUB)] if moving else [t]
        acc = sum(shot(theta, x) for x in ts) / len(ts)
        al = acc[..., 3:4]; rgb = np.where(al > 0, acc[..., :3] / np.maximum(al, 1e-6), 0)
        out = Image.fromarray(np.dstack([rgb, al * 255]).clip(0, 255).astype(np.uint8), 'RGBA')
        b = bgimg.copy(); b.alpha_composite(out); b.convert('RGB').save(fn)
        print(k, flush=True)
