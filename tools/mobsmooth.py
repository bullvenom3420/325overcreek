"""Phone intro without stutter: every video frame is rendered at its own eased angle,
so no frame repeats at the slow start and end. Pets are baked in like the desktop frames.
python3 mobsmooth.py OUTDIR shard nshards     (then: python3 mobsmooth.py OUTDIR --encode ASSETDIR)"""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
OUT = sys.argv[1]
N = 240
W, H = 1080, 780
BG = np.array([0x11, 0x17, 0x13], float)
yy, xx = np.mgrid[0:H, 0:W]
g = np.exp(-(((xx - W / 2) / (W * 0.42)) ** 2 + ((yy - H * 0.62) / (H * 0.30)) ** 2)) * np.sin(np.pi * yy / H) ** 2 * np.sin(np.pi * xx / W) ** 1.5
bgimg = Image.fromarray((BG[None, None] + g[..., None] * np.array([12, 17, 13])[None, None]).astype(np.uint8), 'RGB').convert('RGBA')
ease = lambda t: 0.5 - 0.5 * math.cos(math.pi * t)
if sys.argv[2] == '--encode':
    dst = sys.argv[3]
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '30', '-i', os.path.join(OUT, 'm%03d.png'),
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an',
                    os.path.join(dst, 'intro-mobile.mp4')], check=True)
    Image.open(os.path.join(OUT, 'm%03d.png' % (N - 1))).save(os.path.join(dst, 'intro-mobile-poster.jpg'), quality=86)
    sys.exit()
import render
k0, step = int(sys.argv[2]), int(sys.argv[3])
os.makedirs(OUT, exist_ok=True)
mesh = render.build_mesh()
for k in range(k0, N, step):
    fn = os.path.join(OUT, 'm%03d.png' % k)
    if os.path.exists(fn):
        continue
    th = ease(k / (N - 1)) * 360.0
    im = render.render(th, 1200, 780, mesh=mesh).crop((60, 0, 1140, 780))
    a = np.asarray(im).astype(float); rgb = a[..., :3]; al = a[..., 3:4] / 255
    lum = rgb.mean(-1, keepdims=True); al = np.where((lum < 90) & (al < 0.6), al * 0.25, al)
    out = Image.fromarray(np.dstack([rgb, al * 255]).astype(np.uint8), 'RGBA')
    b = bgimg.copy(); b.alpha_composite(out); b.convert('RGB').save(fn)
    print(k, flush=True)
