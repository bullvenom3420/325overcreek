"""Phone intro: one eased turn of the baked frames on the dark green-black background."""
import sys, os, math, subprocess
import numpy as np
from PIL import Image
FR, OUT = sys.argv[1], sys.argv[2]
W, H = 1080, 780
BG = np.array([0x11, 0x17, 0x13], float)
yy, xx = np.mgrid[0:H, 0:W]
g = np.exp(-(((xx - W / 2) / (W * 0.42)) ** 2 + ((yy - H * 0.62) / (H * 0.30)) ** 2))
bg = BG[None, None] + g[..., None] * np.array([12, 17, 13])[None, None]
bgimg = Image.fromarray(bg.astype(np.uint8), 'RGB').convert('RGBA')
def frame(i):
    im = Image.open(os.path.join(FR, 'frame-%03d.webp' % (i % 120))).convert('RGBA')
    im = im.crop((80, 0, 1520, 1040)).resize((W, H), Image.LANCZOS)
    a = np.asarray(im).astype(float)
    rgb = a[..., :3]; al = a[..., 3:4] / 255
    lum = rgb.mean(-1, keepdims=True)
    al = np.where((lum < 90) & (al < 0.6), al * 0.25, al)
    out = Image.fromarray(np.dstack([rgb, al * 255]).astype(np.uint8), 'RGBA')
    b = bgimg.copy(); b.alpha_composite(out); return b.convert('RGB')
tmp = os.path.join(OUT, '_mob'); os.makedirs(tmp, exist_ok=True)
N = 240
ease = lambda t: 0.5 - 0.5 * math.cos(math.pi * t)
for k in range(N):
    t = k / (N - 1); frame(int(round(ease(t) * 120))).save(os.path.join(tmp, 'm%03d.png' % k))
frame(0).save(os.path.join(OUT, 'intro-mobile-poster.jpg'), quality=86)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '30', '-i', os.path.join(tmp, 'm%03d.png'),
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                os.path.join(OUT, 'intro-mobile.mp4')], check=True)
for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
os.rmdir(tmp)
print('ok')
