"""Crop the drawing sheets for the site: no title blocks, seals, stamps or city mark-ups."""
import sys, numpy as np
from PIL import Image
P = '/home/claude/ov/pages/'
OUT = '/home/claude/325overcreek/assets/'
def clean(im):
    a = np.asarray(im.convert('RGB')).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    colored = ((r - np.minimum(g, b)) > 38) | ((b - np.minimum(r, g)) > 38)   # red ink, blue stamp
    a[colored] = 255
    # lift paper to white, keep line weight
    lum = a.mean(-1, keepdims=True)
    a = np.where(lum > 205, 255, a)
    return Image.fromarray(a.astype(np.uint8))
def unframe(im):
    a = np.asarray(im.convert('L')).copy()
    dark = a < 160
    rows = dark.mean(1) > 0.55
    cols = dark.mean(0) > 0.55
    a2 = np.asarray(im.convert('RGB')).copy()
    for y in np.where(rows)[0]:
        a2[max(0, y - 3):y + 4] = 255
    for x in np.where(cols)[0]:
        a2[:, max(0, x - 3):x + 4] = 255
    return Image.fromarray(a2)
def trim(im, pad=30):
    im = unframe(im)
    a = np.asarray(im.convert('L'))
    ys, xs = np.where(a < 200)
    return im.crop((max(0, xs.min() - pad), max(0, ys.min() - pad), min(im.size[0], xs.max() + pad), min(im.size[1], ys.max() + pad)))
jobs = {
  'front_elevation': ('hie-04.png', (600, 1860, 3440, 3130)),
  'rear_elevation':  ('hie-04.png', (1000, 400, 3450, 1600)),
  'left_elevation':  ('hie-05.png', (850, 420, 3700, 1610)),
  'right_elevation': ('hie-05.png', (800, 1860, 3540, 3080)),
  'first_plan':      ('hi-06.png', (820, 110, 3560, 3160)),
  'second_plan':     ('hi-07.png', (900, 580, 3470, 3040)),
}
for name, (src, box) in jobs.items():
    im = trim(clean(Image.open(P + src).crop(box)))
    w, h = im.size
    big = 2300 if 'elev' in name else 1600
    im2 = im.resize((big, round(h * big / w)), Image.LANCZOS)
    if 'elev' in name:
        im2.save(OUT + name + '.jpg', quality=86)
        im.resize((1200, round(h * 1200 / w)), Image.LANCZOS).save(OUT + name + '-1200.webp', quality=86)
    else:
        im2.save(OUT + name + '.webp', quality=88)
        im.resize((1000, round(h * 1000 / w)), Image.LANCZOS).save(OUT + name + '-1000.webp', quality=86)
    print(name, im2.size)
