"""Blender files for one house, built straight from the same model the site renders.

  python3 blendexport.py OUTDIR SLUG

Writes (meters, Z up, front of the house toward -Y):
  SLUG-whole-house.blend      every part, one object per build piece, in collections by floor
  SLUG-first-floor.blend      the first floor alone (shell, rooms, doorways, its windows, porch slab)
  SLUG-second-floor.blend     the second floor alone (and the one-story roofs that tie into it)
  SLUG-roof.blend             the roof pieces alone
  SLUG-build-animation.blend  the intro: pieces fall in with the site's exact timing and easing
                              (60 fps, 180 frames), the camera turns and eases down, the pets fade in
Materials match the white-clay look; pets are textured image planes.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
import house
import buildanim as BA

OUT, SLUG = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
FT = 0.3048
HERE = os.path.dirname(os.path.abspath(__file__))

house.INTERIOR[0] = True
GEO = house.geometry()
PETQ = {k: dict(v) for k, v in house.PET_QUADS.items()}
GROUPS = []
for (pts, mat), g in zip(GEO, house.FACE_GROUP):
    if g == 'open':
        g = 'ff' if np.mean([p[2] for p in pts]) < house.P1 else 'sf'
    GROUPS.append(BA.MERGE.get(g, g))
ORDER = [d[0] for d in BA.DROPS]
FLOOR_OF = {'ff': 'First floor', 'sf': 'Second floor'}
NICE = {'ff': 'First floor', 'sf': 'Second floor', 'gallery': 'Gallery (columns and balcony)', 'rail': 'Balcony railings',
        'beam': 'Gallery beam', 'roof': 'Main roof', 'gable': 'Gable walls', 'froof': 'Front roof', 'wroof': 'Wing roofs',
        'rroof': 'Rear roof', 'porch': 'Porch'}
COLORS = {'wall': (0.93, 0.92, 0.89), 'floor': (0.85, 0.84, 0.81), 'roof': (0.875, 0.865, 0.845),
          'glass': (0.62, 0.63, 0.66), 'void': (0.30, 0.30, 0.32), 'trim': (0.96, 0.955, 0.94), 'darkglass': (0.40, 0.41, 0.44)}
CENTER = np.array(getattr(house, 'CENTER', (31.5, 34.0, 12.0)), float)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'IMPERIAL'
    sc.unit_settings.length_unit = 'FEET'
    sc.render.fps = BA.FPS
    sc.frame_start, sc.frame_end = 1, BA.N
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1040
    w = bpy.data.worlds.new('World'); sc.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.067, 0.09, 0.075, 1)
    return sc


def material(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    c = COLORS.get(name, (0.9, 0.9, 0.9))
    b.inputs['Base Color'].default_value = (*c, 1)
    b.inputs['Roughness'].default_value = 0.85 if name != 'glass' else 0.25
    m.diffuse_color = (*c, 1)
    return m


def mesh_object(name, faces, coll):
    verts, polys, mats, mi = [], [], [], {}
    index = {}
    for pts, mat in faces:
        poly = []
        for p in pts:
            key = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
            if key not in index:
                index[key] = len(verts); verts.append((p[0] * FT, p[1] * FT, p[2] * FT))
            poly.append(index[key])
        dedup = [v for i, v in enumerate(poly) if v != poly[i - 1]]
        if len(set(dedup)) < 3:
            continue
        polys.append(dedup)
        if mat not in mi:
            mi[mat] = len(mats); mats.append(mat)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], polys)
    k = 0
    for pts, mat in faces:
        pass
    for m in mats:
        me.materials.append(material(m))
    # per-face material index, in the same order the faces were kept
    keep = []
    for pts, mat in faces:
        poly = [index[(round(p[0], 4), round(p[1], 4), round(p[2], 4))] for p in pts]
        dedup = [v for i, v in enumerate(poly) if v != poly[i - 1]]
        if len(set(dedup)) >= 3:
            keep.append(mi[mat])
    for poly, m in zip(me.polygons, keep):
        poly.material_index = m
    me.validate(); me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def pet_plane(key, coll, offset=(0, 0, 0)):
    q = PETQ[key]
    o, U, V = (np.array(q[a], float) for a in 'oUV')
    pts = [o, o + U, o + U + V, o + V]
    me = bpy.data.meshes.new('Huckleberry' if key == 'dog' else 'Cat')
    me.from_pydata([tuple((p + offset) * FT) for p in pts], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new();
    for i, c in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = c
    m = bpy.data.materials.new(me.name + ' sprite'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexImage')
    img = bpy.data.images.load(os.path.join(HERE, 'pets', q['sprite'] + '.png')); img.pack()
    tex.image = img
    nt.links.new(tex.outputs['Color'], b.inputs['Base Color'])
    mixa = nt.nodes.new('ShaderNodeMath'); mixa.operation = 'MULTIPLY'; mixa.name = 'fade'
    mixa.inputs[1].default_value = 1.0
    nt.links.new(tex.outputs['Alpha'], mixa.inputs[0]); nt.links.new(mixa.outputs[0], b.inputs['Alpha'])
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        pass
    me.materials.append(m)
    ob = bpy.data.objects.new(me.name, me); coll.objects.link(ob)
    return ob, mixa


def collections(sc):
    out = {}
    for g in ORDER:
        c = bpy.data.collections.new(NICE.get(g, g.title())); sc.collection.children.link(c); out[g] = c
    out['pets'] = bpy.data.collections.new('Huckleberry and the cat'); sc.collection.children.link(out['pets'])
    return out


def camera_rig(sc):
    cam = bpy.data.cameras.new('Camera'); cam.sensor_fit = 'VERTICAL'; cam.angle_y = math.radians(27.0)
    ob = bpy.data.objects.new('Camera', cam); sc.collection.objects.link(ob); sc.camera = ob
    sun = bpy.data.lights.new('Sun', 'SUN'); sun.energy = 3.0
    so = bpy.data.objects.new('Sun', sun); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(28), 0, math.radians(-40))
    return ob


def place_camera(ob, theta, elev):
    th, el = math.radians(theta), math.radians(elev)
    d = np.array([math.sin(th) * math.cos(el), -math.cos(th) * math.cos(el), math.sin(el)])
    eye = CENTER + d * 172.0
    ob.location = tuple(eye * FT)
    f = CENTER - eye; f /= np.linalg.norm(f)
    # Blender camera looks down its -Z with +Y up
    import mathutils
    ob.rotation_euler = mathutils.Vector(tuple(f)).to_track_quat('-Z', 'Y').to_euler()


def faces_of(groups):
    return [GEO[i] for i, g in enumerate(GROUPS) if g in groups]


def save(name):
    p = os.path.join(OUT, name)
    bpy.ops.wm.save_as_mainfile(filepath=p, compress=True)
    print('saved', p, os.path.getsize(p))


# ---- whole house and floors
for fname, groups in [('whole-house', ORDER), ('first-floor', ['ff']), ('second-floor', ['sf']),
                      ('roof', [g for g in ORDER if g not in ('ff', 'sf')])]:
    sc = reset(); cols = collections(sc)
    for g in groups:
        f = faces_of([g])
        if f:
            mesh_object(NICE.get(g, g), f, cols[g])
    if fname in ('whole-house', 'first-floor'):
        for k in PETQ:
            if GROUPS[PETQ[k]['fid'] - 1] in groups:
                pet_plane(k, cols['pets'])
    for c in list(cols.values()):
        if not c.objects:
            bpy.data.collections.remove(c)
    cam = camera_rig(sc); place_camera(cam, 0.0, 11.0 if fname == 'whole-house' else 40.0)
    save('%s-%s.blend' % (SLUG, fname))

# ---- build animation (exact site timing: baked one key per frame)
sc = reset(); cols = collections(sc)
objs = {}
for g in ORDER:
    f = faces_of([g])
    if f:
        objs[g] = mesh_object(NICE.get(g, g), f, cols[g])
pets = {}
for k in PETQ:
    g = GROUPS[PETQ[k]['fid'] - 1]
    ob, fade = pet_plane(k, cols['pets'])
    pets[k] = (ob, fade, g)
cam = camera_rig(sc)
for fr in range(BA.N):
    t = fr / BA.FPS
    sc.frame_set(fr + 1)
    for g, t0 in BA.DROPS:
        if g in objs:
            objs[g].location = (0, 0, BA.drop(t, t0) * FT); objs[g].keyframe_insert('location', index=2, frame=fr + 1)
    for k, (ob, fade, g) in pets.items():
        t0 = dict(BA.DROPS)[g]
        ob.location = (0, 0, BA.drop(t, t0) * FT); ob.keyframe_insert('location', index=2, frame=fr + 1)
        a0, a1 = BA.PET_IN[k]
        fade.inputs[1].default_value = BA.ease(min(max((t - a0) / (a1 - a0), 0.0), 1.0))
        fade.inputs[1].keyframe_insert('default_value', frame=fr + 1)
    place_camera(cam, BA.theta_at(fr), BA.elev_at(t))
    cam.keyframe_insert('location', frame=fr + 1); cam.keyframe_insert('rotation_euler', frame=fr + 1)
sc.frame_set(BA.N)
save('%s-build-animation.blend' % SLUG)
