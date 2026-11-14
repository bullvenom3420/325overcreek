"""Intro: the house falls together from above while it turns (3 s, 60 fps, 180 frames).

  python3 buildanim.py render OUTDIR shard nshards   -> OUTDIR/b%03d.png  (1600x1040 RGBA, straight alpha)
  python3 buildanim.py export OUTDIR ASSETDIR        -> desktop frames (ASSETDIR/build/build-%03d.webp),
                                                        phone video + poster (ASSETDIR/mobile/)

Rules that keep it from looking glitchy:
  * parts that overlap in the finished house fall as one rigid piece, so nothing passes through anything;
  * every piece starts above the top of the frame (nothing fades or pops in);
  * floors are solid shells with wall thickness, floors and doorways (house.INTERIOR), never paper walls;
  * falling pieces get motion blur (sub-frames blended); the spin itself is never blurred;
  * the pets fade in only after the last piece has landed.
"""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image

FPS, DUR = 60, 3.0
N = int(FPS * DUR)
W, H = 1600, 1040                                # desktop frame size (same framing as the spin frames)

DROPS = [('ff', 0.00), ('sf', 0.38), ('gallery', 0.80), ('rail', 1.10), ('beam', 1.32), ('roof', 1.58)]
MERGE = {'roofD': 'sf', 'roofE': 'sf', 'gceil': 'ff'}           # one-story roofs die into the second floor: fall with it
FALL = 0.57                                      # seconds per drop
LIFT = 78.0                                      # start height above landing (above the frame top)
SHUTTER = 0.4                                    # fraction of a frame the shutter is open
SUB_PX = 3.5                                     # max on-screen gap between blur sub-frames (px)
SUB_MAX = 10
PX_PER_FT = 12.6                                 # rough screen scale of the 1600x1040 frame
SHADOW_H = 34.0                                  # a falling piece's shadow fades in below this height
PET_IN = {'dog': (2.40, 2.70), 'cat': (2.55, 2.85)}
ELEV0, ELEV1 = 30.0, 11.0                        # camera starts looking down into the rooms

ease = lambda t: 0.5 - 0.5 * math.cos(math.pi * t)


def drop(t, t0):
    s = min(max((t - t0) / FALL, 0.0), 1.0)
    return LIFT * (1 - s) ** 3                   # arrives fast from above, eases firmly into place


def elev_at(t):
    s = min(max(t / 2.55, 0.0), 1.0)
    return ELEV1 + (ELEV0 - ELEV1) * (1 - ease(s))


def theta_at(k):
    return ease(k / (N - 1)) * 360.0


class Scene:
    def __init__(self):
        import render, house
        self.render, self.house = render, house
        house.INTERIOR[0] = True
        geo = house.geometry()
        fgroup = []
        for (pts, mat), g in zip(geo, house.FACE_GROUP):
            if g == 'open':
                g = 'ff' if np.mean([p[2] for p in pts]) < house.P1 else 'sf'
            fgroup.append(MERGE.get(g, g))
        house.geometry = lambda: geo             # build_mesh must not rebuild (would reset pet quads)
        self.mesh = render.build_mesh()
        self.names = [d[0] for d in DROPS]
        self.tg = np.array([self.names.index(fgroup[f - 1]) for f in self.mesh[1]])
        self.pet_o = {k: tuple(q['o']) for k, q in house.PET_QUADS.items()}
        self.pet_g = {k: self.names.index(fgroup[q['fid'] - 1]) for k, q in house.PET_QUADS.items()}

    def shot(self, theta, t):
        """premultiplied RGBA float image (H, W, 4), 0..255"""
        off = {g: drop(t, t0) for g, t0 in DROPS}
        if all(v > 60 for v in off.values()):
            return np.zeros((H, W, 4))
        wts = [min(1.0, max(0.0, 1 - off[n] / SHADOW_H)) ** 1.5 for n in self.names]
        dz = np.array([off[n] for n in self.names])[self.tg]
        m = list(self.mesh); tt = self.mesh[0].copy(); tt[..., 2] += dz[:, None]; m[0] = tt
        for k, q in self.house.PET_QUADS.items():
            o = self.pet_o[k]; q['o'] = (o[0], o[1], o[2] + off[self.names[self.pet_g[k]]])
        for k, (a0, a1) in PET_IN.items():
            self.render.PET_FADE[k] = ease(min(max((t - a0) / (a1 - a0), 0.0), 1.0))
        im = self.render.render(theta, W, H, elev=elev_at(t), mesh=m, shadow_classes=(self.tg, wts))
        a = np.asarray(im).astype(float); al = a[..., 3:4] / 255
        return np.dstack([a[..., :3] * al, al * 255])

    @staticmethod
    def subframes(t):
        """enough sub-frames that a falling piece never shows as separate copies"""
        spread = 0.0
        for _, t0 in DROPS:
            s = (t - t0) / FALL
            if 0 < s < 1 + 1.0 / (FALL * FPS) and drop(t, t0) < 66:
                v = 3 * LIFT * (1 - min(s, 1.0)) ** 2 / FALL          # ft/s
                spread = max(spread, v / FPS * SHUTTER * PX_PER_FT)
        return 1 if spread < 0.6 else int(min(SUB_MAX, max(3, math.ceil(spread / SUB_PX) + 1)))

    def frame(self, k):
        t = k / FPS
        n = self.subframes(t)
        ts = [t + (j / (n - 1) - 0.5) * SHUTTER / FPS for j in range(n)] if n > 1 else [t]
        acc = sum(self.shot(theta_at(k), x) for x in ts) / len(ts)
        al = acc[..., 3:4]; rgb = np.where(al > 0, acc[..., :3] / np.maximum(al / 255, 1e-6), 0)
        return Image.fromarray(np.dstack([rgb, al]).clip(0, 255).astype(np.uint8), 'RGBA')


def phone_bg(w, h):
    BG = np.array([0x11, 0x17, 0x13], float)
    yy, xx = np.mgrid[0:h, 0:w]
    g = np.exp(-(((xx - w / 2) / (w * 0.42)) ** 2 + ((yy - h * 0.62) / (h * 0.30)) ** 2)) * np.sin(np.pi * yy / h) ** 2 * np.sin(np.pi * xx / w) ** 1.5
    return Image.fromarray((BG[None, None] + g[..., None] * np.array([12, 17, 13])[None, None]).astype(np.uint8), 'RGB').convert('RGBA')


def to_phone(im, bg):
    """1600x1040 RGBA -> 1080x780 phone frame on the dark intro background (same crop as before)."""
    im = im.resize((1200, 780), Image.LANCZOS).crop((60, 0, 1140, 780))
    a = np.asarray(im).astype(float); rgb = a[..., :3]; al = a[..., 3:4] / 255
    lum = rgb.mean(-1, keepdims=True); al = np.where((lum < 90) & (al < 0.6), al * 0.25, al)
    out = Image.fromarray(np.dstack([rgb, al * 255]).astype(np.uint8), 'RGBA')
    b = bg.copy(); b.alpha_composite(out); return b.convert('RGB')


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'render':
        out, k0, step = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
        os.makedirs(out, exist_ok=True)
        sc = Scene()
        for k in range(k0, N, step):
            fn = os.path.join(out, 'b%03d.png' % k)
            if os.path.exists(fn):
                continue
            sc.frame(k).save(fn + '.tmp.png'); os.replace(fn + '.tmp.png', fn)
            print(k, flush=True)
    elif mode == 'export':
        src, assets = sys.argv[2], sys.argv[3]
        dd = os.path.join(assets, 'build'); os.makedirs(dd, exist_ok=True)
        tmp = os.path.join(src, 'phone'); os.makedirs(tmp, exist_ok=True)
        bg = phone_bg(1080, 780)
        for k in range(N):
            im = Image.open(os.path.join(src, 'b%03d.png' % k)).convert('RGBA')
            im.save(os.path.join(dd, 'build-%03d.webp' % k), 'WEBP', quality=82, method=6, alpha_quality=88)
            to_phone(im, bg).save(os.path.join(tmp, 'm%03d.png' % k))
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, 'm%03d.png'),
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an',
                        os.path.join(assets, 'mobile', 'intro-mobile.mp4')], check=True)
        Image.open(os.path.join(tmp, 'm%03d.png' % (N - 1))).save(os.path.join(assets, 'mobile', 'intro-mobile-poster.jpg'), quality=86)
        print('exported')
