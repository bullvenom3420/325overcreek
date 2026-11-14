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
FACE_GROUP = []   # build-animation group of each face (parallel to faces)
GROUP = ['ff']

def setgroup(g):
    GROUP[0] = g


def face(pts, mat):
    faces.append(([list(map(float, p)) for p in pts], mat))
    FACE_GROUP.append(GROUP[0])


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


# ------------------------------------------------------------------ hollow shells (build animation only)
INTERIOR = [False]      # True: floors are hollow shells with rooms, so the build animation can look inside
WALL_T = 0.8            # exterior wall thickness
PART_T = 0.42           # interior partition thickness


def _area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                     for i in range(len(poly)))


def inset(poly, d):
    """Inset a rectilinear polygon by d (mitered corners)."""
    ccw = _area(poly) > 0
    n = len(poly)
    lines = []
    for i in range(n):
        (xa, ya), (xb, yb) = poly[i], poly[(i + 1) % n]
        dx, dy = xb - xa, yb - ya
        L = (dx * dx + dy * dy) ** 0.5
        nx, ny = (-dy / L, dx / L) if ccw else (dy / L, -dx / L)     # inward normal
        lines.append(((xa + nx * d, ya + ny * d), (dx / L, dy / L)))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
    return out


def shell(z0, z1, poly, floor_z, bottom=False, t=None):
    """Exterior walls of thickness t around poly from z0 to z1, open on top, with a floor."""
    t = WALL_T if t is None else t
    inner = inset(poly, t)
    n = len(poly)
    for i in range(n):
        (xa, ya), (xb, yb) = poly[i], poly[(i + 1) % n]
        face([(xa, ya, z0), (xb, yb, z0), (xb, yb, z1), (xa, ya, z1)], 'wall')
        (ia, ja), (ib, jb) = inner[i], inner[(i + 1) % n]
        face([(ia, ja, floor_z), (ib, jb, floor_z), (ib, jb, z1), (ia, ja, z1)], 'wall')
        face([(xa, ya, z1), (xb, yb, z1), (ib, jb, z1), (ia, ja, z1)], 'wall')
        if bottom:
            face([(xa, ya, z0), (xb, yb, z0), (ib, jb, z0), (ia, ja, z0)], 'wall')
    face([(x, y, floor_z) for x, y in inner], 'floor')
    return inner


def partitions(walls, inner, z0, z1, t=None, door_top=None):
    """Interior walls given as centerlines ('h', y, x0, x1) / ('v', x, y0, y1).
    Ends within 1.6 ft of an exterior wall's inner face or another partition snap to it exactly,
    so nothing overlaps (no coplanar tops to flicker)."""
    t = PART_T if t is None else t
    door_top = z0 + 8.0 if door_top is None else door_top
    n = len(inner)
    def stops(kind, at):
        c = []
        for i in range(n):
            (xa, ya), (xb, yb) = inner[i], inner[(i + 1) % n]
            if kind == 'h' and abs(xa - xb) < 1e-6 and min(ya, yb) <= at <= max(ya, yb):
                c.append((xa, 0.0))
            if kind == 'v' and abs(ya - yb) < 1e-6 and min(xa, xb) <= at <= max(xa, xb):
                c.append((ya, 0.0))
        for w2 in walls:
            k2, at2, a2, b2 = w2[:4]
            if k2 != kind and min(a2, b2) - 0.5 <= at <= max(a2, b2) + 0.5:
                c.append((at2, t / 2))
        return c
    def snap(v, cands, lo_end):
        best = None
        for c, half in cands:
            target = c + half if lo_end else c - half
            if abs(target - v) < 1.6 + half and (best is None or abs(target - v) < abs(best - v)):
                best = target
        return v if best is None else best
    def piece(kind, at, u0, u1, za, zb):
        if u1 - u0 < 1e-3:
            return
        if kind == 'h':
            box(u0, u1, at - t / 2, at + t / 2, za, zb)
        else:
            box(at - t / 2, at + t / 2, u0, u1, za, zb)
    for w in walls:
        kind, at, a, b = w[:4]
        doors = sorted(w[4]) if len(w) > 4 else []
        a, b = min(a, b), max(a, b)
        cands = stops(kind, at)
        a2, b2 = snap(a, cands, True), snap(b, cands, False)
        u = a2
        for c, wd in doors:                       # door openings: wall stops, header spans above
            d0, d1 = max(c - wd / 2, a2), min(c + wd / 2, b2)
            piece(kind, at, u, d0, z0, z1)
            piece(kind, at, d0, d1, door_top, z1)
            u = d1
        piece(kind, at, u, b2, z0, z1)


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
    FACE_GROUP.clear()
    PET_QUADS.clear()
    setgroup('ff')
    F, R = -1, 1

    # ---- first floor envelope (brick)
    ff = [(2, 10.67), (10.67, 10.67), (10.67, 5), (27.17, 5), (27.17, 6.17), (36.17, 6.17),
          (36.17, 5), (52.67, 5), (52.67, 10.67), (61, 10.67), (61, 68.5), (38, 68.5),
          (38, 42.25), (22.5, 42.25), (22.5, 54.5), (17, 54.5), (17, 59.67), (0, 59.67),
          (0, 35.83), (2, 35.83)]
    if INTERIOR[0]:
        inner = shell(0, P1, ff, FF)
        partitions([                                   # first floor, traced from the plan; (center, width) doors
            ('h', 42.0, 0, 16.6, [(9.4, 4.0), (15.2, 2.8)]),      # primary bedroom | bath, hall
            ('v', 16.6, 42.0, 54.5),                              # primary bedroom | powder, hall
            ('v', 14.4, 21.2, 42.0),                              # primary bath, closets | family
            ('h', 21.2, 2, 14.4, [(5.2, 2.5)]),                   # bath | closet
            ('v', 10.9, 11.5, 21.2),                              # closet | study
            ('h', 16.4, 10.9, 26.0),                              # study back
            ('v', 26.0, 7.0, 16.4, [(13.3, 4.0)]),                # study | foyer (French doors)
            ('v', 37.25, 7.0, 20.4, [(12.5, 5.0)]),               # foyer | dining (cased opening)
            ('h', 20.4, 37.25, 52.08, [(44.5, 6.0)]),             # dining | kitchen (cased opening)
            ('v', 52.08, 11.5, 20.4),                             # dining | scullery
            ('v', 50.3, 20.4, 43.5, [(22.6, 2.8), (31.5, 2.8), (41.0, 2.8)]),   # kitchen | scullery, laundry, mud
            ('h', 25.0, 50.3, 61, [(56.0, 2.8)]),                 # scullery | laundry
            ('h', 37.5, 50.3, 61, [(55.5, 2.8)]),                 # laundry | mud
            ('h', 43.5, 38, 61, [(55.8, 2.8)]),                   # mud | garage
        ], inner, FF, P1)
        setgroup('gceil')
        box(38 + WALL_T, 61 - WALL_T, 43.5 + PART_T / 2, 68.5 - WALL_T, P1 - 0.25, P1)   # garage ceiling
        setgroup('ff')
    else:
        prism_z(0, P1, ff)
    setgroup('sf')
    # ---- second floor envelope (brick; Bed 5 block is siding)
    sf = [(2, 10.67), (10.67, 10.67), (10.67, 5), (52.67, 5), (52.67, 10.67), (61, 10.67),
          (61, 42.25), (39, 42.25), (39, 54.5), (16, 54.5), (16, 42.25), (2, 42.25)]
    if INTERIOR[0]:
        inner = shell(P1, P2, sf, F2, bottom=True)
        face([(x, y, P1) for x, y in inner], 'wall')   # underside of the second floor deck
        partitions([                                   # second floor, traced from the plan; (center, width) doors
            ('h', 27.75, 2, 16.7, [(6.8, 2.5)]),                  # Bed 4 | Bath 4
            ('v', 16.7, 27.75, 42.25, [(29.8, 2.8)]),             # Bed 4 | hall
            ('v', 10.0, 10.5, 27.75, [(16.0, 2.5)]),              # Bath 4, closet | loft
            ('v', 19.1, 21.75, 39.75, [(37.0, 3.0)]),             # game room left
            ('v', 36.4, 21.75, 39.75, [(30.5, 2.8)]),             # game room right
            ('h', 21.75, 19.1, 36.4, [(27.75, 9.0)]),             # game room | stair (wide opening)
            ('h', 39.75, 16.7, 36.4, [(20.8, 2.8)]),              # game room | hall to Bed 5
            ('v', 47.0, 27.75, 42.25, [(30.5, 2.8)]),             # attic storage | Bed 2
            ('h', 27.75, 36.4, 61, [(52.0, 2.5)]),                # Bed 2 | baths
            ('h', 20.5, 36.4, 61, [(44.0, 2.5)]),                 # baths, closets | Bed 3
            ('v', 47.2, 20.5, 27.75, [(24.0, 2.5)]),              # Bath 2 | closet
            ('v', 37.6, 5, 20.5, [(9.5, 2.8)]),                   # loft | Bed 3
            ('v', 52.08, 11.5, 20.5, [(16.0, 2.5)]),              # Bed 3 | Bath 3
            ('v', 26.0, 43.5, 54.5, [(50.5, 2.5)]),               # Bath 5, closet | Bed 5
            ('h', 43.5, 16, 39, [(21.0, 2.5), (28.0, 2.8)]),      # hall | Bath 5, closet, Bed 5
        ], inner, F2, P2, door_top=F2 + 7.0)
    else:
        prism_z(P1, P2, sf, bottom=False)
        # ceiling of the rear outdoor living porch (underside of Bed 5)
        face([(22.5, 42.25, P1), (38, 42.25, P1), (38, 54.5, P1), (22.5, 54.5, P1)], 'wall')
    box(22.5, 38, 54.1, 54.5, P1 - 0.9, P1, 'trim')          # beam at the open rear edge

    setgroup('ff')
    # ---- front gallery: porch slab, balcony floor, columns, beams, X railings
    box(10.67, 52.67, -0.1, 5, 0, 0.4, 'trim')                # porch slab + step
    setgroup('gallery')
    box(10.67, 52.67, -0.1, 5, P1 - 0.2, F2 + 0.3, 'trim')    # balcony floor / trim band
    setgroup('beam')
    box(10.67, 52.67, -0.1, 1.0, P2 - 1.2, P2 - 0.2, 'trim')   # top beam
    setgroup('gallery')
    for cx in (11.3, 27.0, 36.33, 52.03):
        column(cx, 0.55, 0.5, 0.4, P2 - 1.2)
    setgroup('rail')
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

    setgroup('open')
    # ---- openings: front (y = 5, under the gallery)
    for u0, u1 in ((16.5, 21.5), (41.83, 46.83)):                 # study / dining French doors
        k_ = window('y', 5, F, u0, u1, FF, FF + 8.3, sill=False, mull=[(u0 + u1) / 2])
        if u0 > 40:
            gdin = k_
        shutters('y', 5, F, u0, u1, FF, FF + 8.3)
        window('y', 5, F, u0, u1, F2, F2 + 6.67, sill=False, mull=[(u0 + u1) / 2])  # loft / Bed 3
        shutters('y', 5, F, u0, u1, F2, F2 + 6.67)
    gfd = window('y', 6.17, F, 29.17, 34.17, FF, FF + 8.3, sill=False, mull=[30.4, 32.94])  # front door + sidelights
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

    setgroup('roof')
    # ---- roofs (eave outlines from the roof plan; overhangs 2'-0" main, 1'-6" gallery)
    eA = P2 - 0.2
    sA = 0.69
    hiproof(9.17, 54.17, -1.5, 36.1, {'f': (eA, sA), 'b': (eA, sA), 'l': (eA, sA), 'r': (eA, sA)})
    hiproof(0, 63, 8.67, 44.25, {'f': (20.3, S8), 'l': (20.3, S8), 'r': (20.3, S8), 'b': (20.6, S6)})
    eC = P2 - 1.0 * S8
    hiproof(15.0, 40.0, 22.0, 55.5, {'f': (eC, 3.0), 'b': (eC, S8), 'l': (eC, S8), 'r': (eC, S8)})
    setgroup('roofD')
    eD = 10.08 - 1.2 * S8
    hiproof(-1.1, 17.9, 34.9, 60.8, {'b': (eD, S8), 'l': (eD, S8), 'r': (eD, S8)})
    setgroup('roofE')
    eE = 10.08 - 1.3 * S8
    hiproof(36.8, 62.3, 42.4, 69.8, {'b': (eE, S8), 'l': (eE, S8), 'r': (eE, S8)})

    # ---- pet quads (sprites drawn just inside the glass, baked into the frames)
    # Huckleberry lies behind the front door's center glass; the cat peeks around the jamb of the
    # dining room's French doors. Both are seen from the street, where the intro ends.
    # True to life: Huckleberry is a 70 lb sheepadoodle (lying, about 3.3 ft long and 1.8 ft tall with his
    # head up); the cat is a 12 lb Russian Blue (sitting, about 1 ft tall). The door's bars cross in front of him.
    PET_QUADS['dog'] = dict(o=(29.97, 6.17 - 0.085, FF), U=(3.4, 0, 0), V=(0, 0, 3.4 * 600 / 900), n=(0, -1, 0),
                            fid=gfd + 1, sprite='dog')
    PET_QUADS['cat'] = dict(o=(41.83, 5 - 0.085, FF), U=(1.65 * 700 / 900, 0, 0), V=(0, 0, 1.65), n=(0, -1, 0),
                            fid=gdin + 1, sprite='cat')
    return list(faces)


def geometry():
    return build()


if __name__ == '__main__':
    g = geometry()
    print(len(g), 'faces')
