"""325 Overcreek Drive - conceptual massing model.

All units are FEET.  Coordinate system:
  x : left -> right as seen from the street (0 = outer face of the one-story
      primary-suite wall; the two-story walls start at x = 2)
  y : front -> rear  (0 = front face of the gallery columns, 68.5 = alley face of garage)
  z : up (0 = grade, first finished floor 0.5)

Read from the drawing set dated June 19, 2026 (roof plan / site plan rev. Aug 17, 2026):
  sheet 1 front/rear elevations, sheet 2 side elevations, sheet 3 first floor,
  sheet 4 second floor, sheet 5 roof plan, structural S-1 slab dimensions.
Plates: first floor 10' (FF 0.5 -> 10.5); second floor plates 20'-7" (main wings)
and 21'-7" (front gallery roof and Bed 5 block); one-story roofs 10'-1".
Roofs 8:12 except the main block's rear planes (6:12), as drawn.
No chimney: the family room fireplace is a vent-free gas firebox.

geometry() returns a list of faces: (points[[x,y,z],...], material)
material in {'wall','roof','glass','void','trim'}
"""

T = 0.55          # roof thickness at the fascia
FF = 0.5          # first finished floor
P1 = 10.5         # first-floor plate
F2 = 11.6         # second finished floor
P2 = 21.6         # second-floor plate
S8 = 8.0 / 12.0
S6 = 6.0 / 12.0

faces = []
PET_QUADS = {}


def face(pts, mat):
    faces.append(([list(map(float, p)) for p in pts], mat))


# ------------------------------------------------------------------ primitives
def prism_z(z0, z1, poly, mat='wall', top=True, bottom=True):
    n = len(poly)
    if bottom:
        face([(x, y, z0) for x, y in poly], mat)
    if top:
        face([(x, y, z1) for x, y in poly], mat)
    for i in range(n):
        (xa, ya), (xb, yb) = poly[i], poly[(i + 1) % n]
        face([(xa, ya, z0), (xb, yb, z0), (xb, yb, z1), (xa, ya, z1)], mat)


def box(x0, x1, y0, y1, z0, z1, mat='wall'):
    prism_z(z0, z1, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], mat)


def column(cx, cy, r, z0, z1, n=12, mat='trim'):
    import math
    poly = [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    prism_z(z0, z1, poly, mat)
    # base and capital blocks
    box(cx - r - 0.12, cx + r + 0.12, cy - r - 0.12, cy + r + 0.12, z0, z0 + 0.6, mat)


def panel(axis, at, out, u0, u1, z0, z1, mat='glass', d=0.07):
    """Flat window / door panel just proud of a wall plane.
    axis 'y': wall plane y=at, spans x u0..u1; out=-1 faces the street.
    axis 'x': wall plane x=at, spans y u0..u1; out=+1 faces +x."""
    c = at + out * d
    if axis == 'y':
        face([(u0, c, z0), (u1, c, z0), (u1, c, z1), (u0, c, z1)], mat)
    else:
        face([(c, u0, z0), (c, u1, z0), (c, u1, z1), (c, u0, z1)], mat)


def window(axis, at, out, u0, u1, z0, z1, mat='glass', sill=True, mull=None):
    k = len(faces)
    panel(axis, at, out, u0, u1, z0, z1, mat)
    # muntin/mullion bars (thin trim strips on the glass)
    if mull:
        for u in mull:
            panel(axis, at, out, u - 0.06, u + 0.06, z0, z1, 'trim', d=0.1)
    if sill:   # rowlock sill
        if axis == 'y':
            y0, y1 = (at - 0.35, at) if out < 0 else (at, at + 0.35)
            box(u0 - 0.2, u1 + 0.2, y0, y1, z0 - 0.3, z0, 'trim')
        else:
            x0, x1 = (at - 0.35, at) if out < 0 else (at, at + 0.35)
            box(x0, x1, u0 - 0.2, u1 + 0.2, z0 - 0.3, z0, 'trim')
    return k


def shutters(axis, at, out, u0, u1, z0, z1, w=1.35):
    panel(axis, at, out, u0 - 0.15 - w, u0 - 0.15, z0, z1, 'trim', d=0.12)
    panel(axis, at, out, u1 + 0.15, u1 + 0.15 + w, z0, z1, 'trim', d=0.12)


# ------------------------------------------------------------------ hip roofs
def _clip(poly, a, b, c):
    """Keep the part of poly where a*x + b*y + c <= 0 (Sutherland-Hodgman)."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp = a * p[0] + b * p[1] + c
        fq = a * q[0] + b * q[1] + c
        if fp <= 1e-9:
            out.append(p)
        if (fp < -1e-9 and fq > 1e-9) or (fp > 1e-9 and fq < -1e-9):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def hiproof(x0, x1, y0, y1, edges, mat='roof', gable=None):
    """Hip roof over a rectangle (eave outline). edges: {'f','b','l','r': (eave_z, slope)}.
    A missing edge means that end is a gable (vertical wall face, mat 'wall').
    Each plane is z = e + s * (distance in from its eave edge)."""
    planes = {}
    if 'f' in edges:
        e, s = edges['f']; planes['f'] = (0.0, s, e - s * y0)
    if 'b' in edges:
        e, s = edges['b']; planes['b'] = (0.0, -s, e + s * y1)
    if 'l' in edges:
        e, s = edges['l']; planes['l'] = (s, 0.0, e - s * x0)
    if 'r' in edges:
        e, s = edges['r']; planes['r'] = (-s, 0.0, e + s * x1)
    rect = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    zt = lambda x, y: min(a * x + b * y + c for a, b, c in planes.values())
    for k, (a, b, c) in planes.items():
        poly = rect
        for k2, (a2, b2, c2) in planes.items():
            if k2 == k:
                continue
            poly = _clip(poly, a - a2, b - b2, c - c2)
            if len(poly) < 3:
                break
        if len(poly) >= 3:
            face([(x, y, a * x + b * y + c) for x, y in poly], mat)
    # fascia + soffit
    zmin = min(e for e, s in edges.values()) - T
    corners = rect
    for i in range(4):
        (xa, ya), (xb, yb) = corners[i], corners[(i + 1) % 4]
        side = ['f', 'r', 'b', 'l'][i]
        if side not in edges:
            # gable end: wall triangle following the roof profile
            n = 24
            pts = [(xa + (xb - xa) * t / n, ya + (yb - ya) * t / n) for t in range(n + 1)]
            prof = [(x, y, zt(x, y)) for x, y in pts]
            face([(xa, ya, zmin)] + prof + [(xb, yb, zmin)], 'wall')
            continue
        za, zb = zt(xa, ya), zt(xb, yb)
        face([(xa, ya, zmin), (xb, yb, zmin), (xb, yb, zb), (xa, ya, za)], mat)
    face([(x, y, zmin) for x, y in rect], mat)


# ------------------------------------------------------------------ the house
def build():
    faces.clear()
    PET_QUADS.clear()
    F, R = -1, 1

    # ---- first floor envelope (brick)
    ff = [(2, 10.67), (10.67, 10.67), (10.67, 5), (27.17, 5), (27.17, 6.17), (36.17, 6.17),
          (36.17, 5), (52.67, 5), (52.67, 10.67), (61, 10.67), (61, 68.5), (38, 68.5),
          (38, 42.25), (22.5, 42.25), (22.5, 54.5), (17, 54.5), (17, 59.67), (0, 59.67),
          (0, 35.83), (2, 35.83)]
    prism_z(0, P1, ff)
    # ---- second floor envelope (brick; Bed 5 block is siding)
    sf = [(2, 10.67), (10.67, 10.67), (10.67, 5), (52.67, 5), (52.67, 10.67), (61, 10.67),
          (61, 42.25), (39, 42.25), (39, 54.5), (16, 54.5), (16, 42.25), (2, 42.25)]
    prism_z(P1, P2, sf, bottom=False)
    # ceiling of the rear outdoor living porch (underside of Bed 5)
    face([(22.5, 42.25, P1), (38, 42.25, P1), (38, 54.5, P1), (22.5, 54.5, P1)], 'wall')
    box(22.5, 38, 54.1, 54.5, P1 - 0.9, P1, 'trim')          # beam at the open rear edge

    # ---- front gallery: porch slab, balcony floor, columns, beams, X railings
    box(10.67, 52.67, -0.1, 5, 0, 0.4, 'trim')                # porch slab + step
    box(10.67, 52.67, -0.1, 5, P1 - 0.2, F2 + 0.3, 'trim')    # balcony floor / trim band
    box(10.67, 52.67, -0.1, 1.0, P2 - 1.2, P2 - 0.2, 'trim')   # top beam
    for cx in (11.3, 27.0, 36.33, 52.03):
        column(cx, 0.55, 0.5, 0.4, P2 - 1.2)
    rail_z0, rail_z1 = F2 + 0.3, F2 + 3.8
    for a, b in ((11.8, 26.5), (27.5, 35.83), (36.83, 51.53)):
        ry0, ry1 = 0.45, 0.65
        box(a, b, ry0, ry1, rail_z1 - 0.3, rail_z1, 'trim')      # top rail
        box(a, b, ry0, ry1, rail_z0, rail_z0 + 0.25, 'trim')     # bottom rail
        n = max(1, round((b - a) / 3.0))
        w = (b - a) / n
        lo, hi = rail_z0 + 0.25, rail_z1 - 0.3
        for k in range(n):
            u0, u1 = a + k * w, a + (k + 1) * w
            if k > 0:
                box(u0 - 0.1, u0 + 0.1, ry0, ry1, lo, hi, 'trim')
            for (p0, q0), (p1, q1) in (((u0, lo), (u1, hi)), ((u0, hi), (u1, lo))):
                d = 0.13
                face([(p0, ry0, q0 - d), (p1, ry0, q1 - d), (p1, ry0, q1 + d), (p0, ry0, q0 + d)], 'trim')
                face([(p0, ry1, q0 - d), (p1, ry1, q1 - d), (p1, ry1, q1 + d), (p0, ry1, q0 + d)], 'trim')

    # ---- openings: front (y = 5, under the gallery)
    for u0, u1 in ((16.5, 21.5), (41.83, 46.83)):                 # study / dining French doors
        window('y', 5, F, u0, u1, FF, FF + 8.3, sill=False, mull=[(u0 + u1) / 2])
        shutters('y', 5, F, u0, u1, FF, FF + 8.3)
        window('y', 5, F, u0, u1, F2, F2 + 6.67, sill=False, mull=[(u0 + u1) / 2])  # loft / Bed 3
        shutters('y', 5, F, u0, u1, F2, F2 + 6.67)
    window('y', 6.17, F, 29.17, 34.17, FF, FF + 8.3, sill=False, mull=[30.4, 32.94])  # front door + sidelights
    gd = window('y', 5, F, 30.17, 33.17, F2 + 2.0, F2 + 7.0)            # 3050 above entry (bench seat)
    shutters('y', 5, F, 30.17, 33.17, F2 + 2.0, F2 + 7.0, w=1.2)
    # wings (y = 10.67)
    for c in (6.33, 56.83):
        window('y', 10.67, F, c - 1, c + 1, FF + 4.0, FF + 8.0)        # 2040 fxd
        window('y', 10.67, F, c - 1, c + 1, F2 + 4.0, F2 + 7.0)        # 2030 fxd

    # ---- left side (x = 2 two-story wall)
    window('x', 2, F, 27.9, 32.9, FF + 3.3, FF + 7.5, mull=[30.4])      # primary bath 5040
    window('x', 2, F, 23.9, 25.9, FF + 3.3, FF + 7.5)                  # 2040
    gc = window('x', 2, F, 29.2, 32.7, F2 + 0.9, F2 + 5.4)              # Bed 4 (egress)
    window('x', 2, F, 20.4, 24.0, F2 + 5.0, F2 + 6.6)                  # Bath 4 transom
    # ---- right side (x = 61)
    window('x', 61, R, 22.8, 24.8, FF + 4.0, FF + 8.0)                 # scullery side 2040
    window('x', 61, R, 30.5, 35.0, FF + 4.0, FF + 8.0, mull=[32.75])   # laundry 2-2040
    window('x', 61, R, 39.3, 41.3, FF + 4.0, FF + 8.0)                 # mud 2040
    window('x', 61, R, 32.6, 37.3, F2 + 3.4, F2 + 7.0, mull=[34.95])    # Bed 2 (egress)
    window('x', 61, R, 17.2, 21.0, F2 + 5.4, F2 + 7.0)                 # Bath 3 transom

    # ---- rear
    for c in (4.0, 7.67, 11.33):                                        # primary bedroom 3060s
        window('y', 59.67, R, c - 1.5, c + 1.5, FF + 2.0, FF + 8.0)
    gs = window('y', 42.25, R, 24.25, 36.25, FF, FF + 8.0, sill=False, mull=[27.25, 30.25, 33.25])  # slider
    window('x', 38, F, 49.5, 52.5, FF, FF + 8.0, sill=False)            # garage side door
    window('y', 68.5, R, 40.4, 58.6, 0.15, FF + 7.5, sill=False,
           mull=[44.95, 49.5, 54.05])                                    # 18' garage door
    window('y', 54.5, R, 29.6, 34.6, F2 + 3.0, F2 + 7.0, mull=[32.1])    # Bed 5 5040
    window('y', 54.5, R, 17.85, 20.85, F2 + 6.0, F2 + 8.0)              # Bath 5 3020

    # ---- roofs (eave outlines from the roof plan; overhangs 2'-0" main, 1'-6" gallery)
    eA = P2 - 0.2
    sA = 0.69
    hiproof(9.17, 54.17, -1.5, 36.1, {'f': (eA, sA), 'b': (eA, sA), 'l': (eA, sA), 'r': (eA, sA)})
    hiproof(0, 63, 8.67, 44.25, {'f': (20.3, S8), 'l': (20.3, S8), 'r': (20.3, S8), 'b': (20.6, S6)})
    eC = P2 - 1.0 * S8
    hiproof(15.0, 40.0, 22.0, 55.5, {'f': (eC, 3.0), 'b': (eC, S8), 'l': (eC, S8), 'r': (eC, S8)})
    eD = 10.08 - 1.2 * S8
    hiproof(-1.1, 17.9, 34.9, 60.8, {'b': (eD, S8), 'l': (eD, S8), 'r': (eD, S8)})
    eE = 10.08 - 1.3 * S8
    hiproof(36.8, 62.3, 42.4, 69.8, {'b': (eE, S8), 'l': (eE, S8), 'r': (eE, S8)})

    # ---- pet quads (sprites drawn behind the glass, baked into the frames)
    # Huckleberry: lying down side-on just inside the family room's sliding door, head turned
    # to look out at the covered outdoor living area (rear, ground floor). Seen from outside, so
    # the sprite's left edge sits at the larger x.
    PET_QUADS['dog'] = dict(o=(33.17, 42.25 + 0.085, FF), U=(-2.84, 0, 0), V=(0, 0, 1.893), n=(0, 1, 0),
                            fid=gs + 1, sprite='dog')
    # the cat: peeking around the jamb of the Bed 4 window, left side (seen only as the house turns)
    PET_QUADS['cat'] = dict(o=(2 - 0.085, 32.7, F2 + 0.9), U=(0, -3.5, 0), V=(0, 0, 4.5), n=(-1, 0, 0),
                            fid=gc + 1, sprite='cat')
    return list(faces)


def geometry():
    return build()


if __name__ == '__main__':
    g = geometry()
    print(len(g), 'faces')
