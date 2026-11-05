"""python3 frames.py OUTDIR N W H shard nshards  -> frame-XXX.webp + pets-XXX.json"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import render
out, N, W, H, k, m = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
os.makedirs(out, exist_ok=True)
mesh = render.build_mesh()
for i in range(k, N, m):
    fn = os.path.join(out, 'frame-%03d.webp' % i)
    if os.path.exists(fn):
        continue
    im = render.render(360.0 * i / N, W, H, mesh=mesh)
    json.dump(render.LAST_PETS, open(os.path.join(out, 'pets-%03d.json' % i), 'w'))
    im.save(fn, 'WEBP', quality=84, method=6, alpha_quality=90)
    print(i, flush=True)
