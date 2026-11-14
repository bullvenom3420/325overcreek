"""assets/pets-frames.js for the one view the live pets appear in: the finished house facing the street
(last intro frame, desktop and phone). Corners are in 1600x1040 frame pixels. 'bars' are the front door's
bars that cross in front of Huckleberry, redrawn over his animated copy."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
import render, house
W, H = 1600, 1040
mesh = render.build_mesh()
render.render(0.0, 400, 260, mesh=mesh)           # fills LAST_PETS (corners scale with W, so redo at full size below)
eye, f, r, u = render.camera(0.0, 11.0, 172.0)
foc = (H / 2) / math.tan(math.radians(27.0) / 2); cx, cy = W / 2, H * 0.53
def proj(p):
    q = np.array(p, float) - eye; z = q @ f
    return [round(float(cx + foc * (q @ r) / z), 1), round(float(cy - foc * (q @ u) / z), 1)]
frame = np.asarray(Image.open(os.path.join(os.path.dirname(__file__), '..', 'assets', 'build', 'build-%03d.webp' % 179)).convert('RGB'))
def color(pt):
    x, y = int(round(pt[0])), int(round(pt[1])); return '#%02x%02x%02x' % tuple(frame[y, x])
out = {}
for key, q in house.PET_QUADS.items():
    o, U, V = (np.array(q[a], float) for a in 'oUV')
    c = [proj(o + V), proj(o + U + V), proj(o + U), proj(o)]       # TL TR BR BL
    gpt = proj(o + U * (0.5 if key == 'dog' else 0.3) + V * (0.94 if key == 'dog' else 0.96))
    rec = dict(c=c, on=True, g=color(gpt))
    if key == 'dog':
        bars = []
        for xm in (30.4, 32.94):                                   # front door mullions (house.py)
            y = 6.17 - 0.1
            pts = [proj((xm - 0.06, y, o[2] + V[2])), proj((xm + 0.06, y, o[2] + V[2])), proj((xm + 0.06, y, o[2])), proj((xm - 0.06, y, o[2]))]
            bars.append(dict(p=pts, f=color(proj((xm, y, o[2] + V[2] * 0.9)))))
        rec['bars'] = bars
    out[key] = rec
dst = os.path.join(os.path.dirname(__file__), '..', 'assets', 'pets-frames.js')
open(dst, 'w').write('window.OVERCREEK_PET_FRAMES=' + json.dumps([out], separators=(',', ':')) + ';\n')
print(json.dumps(out, indent=1))
