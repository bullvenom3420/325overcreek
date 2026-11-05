"""Build assets/pets.js: the two sprites + their idle animation, shared by the desktop overlay and the 3D viewer."""
import re, json, os
here = os.path.dirname(__file__)
def inner(fn):
    s = open(os.path.join(here, 'pets', fn)).read()
    s = re.sub(r'<title>.*?</title>', '', s)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    s = s[s.index('>', s.index('<svg')) + 1:s.rindex('</svg>')]
    s = re.sub(r' style="transform-origin:[^"]*"', '', s)
    return re.sub(r'\s+', ' ', s).strip()
dog, cat = inner('dog.svg'), inner('cat.svg')
js = r"""/* 325 Overcreek - Huckleberry and the cat: sprite markup and idle animation (shared). */
(function () {
  function ease(u) { return 0.5 - 0.5 * Math.cos(Math.PI * Math.min(1, Math.max(0, u))); }
  function keys(p, ks) { let k = 0; while (k < ks.length - 2 && ks[k + 1][0] <= p) k++; const [t0, a0] = ks[k], [t1, a1] = ks[k + 1]; return a0 + (a1 - a0) * ease((p - t0) / (t1 - t0)); }
  function blink(t, period, off) { const q = ((t + off) % period); return q < 0.07 ? 1 - q / 0.07 * 0.88 : q < 0.16 ? 0.12 + (q - 0.07) / 0.09 * 0.88 : 1; }
  const PETS = {
    dog: { w: 60, h: 40, markup: DOGM,
      state(t) {
        const tilt = keys((t % 4.2) / 4.2, [[0, 0], [0.62, 0], [0.70, -7], [0.86, -7], [0.94, 0], [1, 0]]);
        const s = blink(t, 2.8, 1.1);
        const wag = 10 * Math.sin(t / 8.4 * 2 * Math.PI * 12);   /* 12 wags per loop, seamless */
        return { 'dog-tail': 'rotate(' + wag.toFixed(2) + ' 50 25)', 'dog-head': 'rotate(' + tilt.toFixed(2) + ' 15.5 27)', 'dog-eyes': 'translate(0 728.5) scale(1 ' + s.toFixed(3) + ') translate(0 -728.5)' };
      } },
    cat: { w: 70, h: 90, markup: CATM,
      state(t) {
        const flick = keys((t % 2.6) / 2.6, [[0, 0], [0.4, -24], [0.55, -6], [0.7, -18], [1, 0]]);
        const turn = keys((t % 5.2) / 5.2, [[0, 0], [0.45, 0], [0.55, 8], [0.8, 8], [0.9, 0], [1, 0]]);
        const s = blink(t, 10.4 / 3, 0.3);
        return { 'cat-tail': 'rotate(' + flick.toFixed(2) + ' 4 88)', 'cat-head': 'rotate(' + turn.toFixed(2) + ' 12 58)', 'cat-eyes': 'translate(0 51) scale(1 ' + s.toFixed(3) + ') translate(0 -51)' };
      } }
  };
  /* markup with the state baked in as transform attributes (used for WebGL textures) */
  PETS.render = function (key, t) {
    const P = PETS[key], st = P.state(t);
    let m = P.markup;
    for (const c in st) m = m.replace('class="' + c + '"', 'class="' + c + '" transform="' + st[c] + '"');
    return m;
  };
  /* live update of an inline <svg> copy */
  PETS.apply = function (root, key, t) {
    const st = PETS[key].state(t);
    for (const c in st) { const el = root.querySelector('.' + c); if (el) el.setAttribute('transform', st[c]); }
  };
  PETS.dog.loop = 8.4; PETS.cat.loop = 10.4;   /* seamless loop lengths (s) */
  window.OVERCREEK_PETS = PETS;
})();
""".replace('DOGM', json.dumps(dog)).replace('CATM', json.dumps(cat))
open(os.path.join(here, '..', 'assets', 'pets.js'), 'w').write(js)
print(len(js))
