"""Blender 5.1: blender --background --factory-startup --python tools/make_characters.py.

Editable original stylized characters, a shared 16-bone rig, and seven authored clips.
Shapes, materials and poses are authored here; no downloaded likenesses or animations.
"""
import bpy
import math
from pathlib import Path
from mathutils import Vector, Matrix, Euler

ROOT = Path(__file__).resolve().parents[1]
OUT, SOURCE = ROOT / 'public' / 'assets', ROOT / 'art'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
# A 10 ms frame makes the shared 620 ms contact a real exported bone sample.
bpy.context.scene.render.fps = 100
CONTACT = 620 / 1450
materials = {}
parts = []


def material(name, color, metallic=0, roughness=.7):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    materials[name] = mat
    return mat


skin = material('Skin · warm porcelain', (.66, .37, .23), roughness=.62)
aged = material('Skin · aged peach', (.62, .37, .25), roughness=.76)
crease = material('Age lines · subtle umber', (.45, .28, .19), roughness=.88)
lip = material('Lips · muted terracotta', (.30, .105, .09), roughness=.7)
ink = material('Ink · eyelids and pupils', (.012, .011, .018), roughness=.65)
cloth = material('Charcoal jersey', (.031, .033, .052), roughness=.94)
trouser = material('Graphite tailored cloth', (.075, .082, .11), roughness=.9)
ivory = material('Ivory linen', (.73, .71, .62), roughness=.88)
silver = material('Hair · graphite silver', (.22, .24, .29), roughness=.52)
hairlight = material('Hair · silver ridges', (.38, .40, .44), roughness=.5)
orange = material('Basketball · grained orange leather', (.73, .205, .035), roughness=.94)
seam = material('Basketball · recessed black seams', (.031, .019, .015), roughness=.86)
jade = material('Court robe · deep jade', (.026, .18, .15), roughness=.89)
jadelight = material('Court robe · folded silk', (.045, .29, .24), roughness=.67)
gold = material('Antique engraved gold', (.65, .37, .075), .78, .3)
goldlight = material('Polished gold edge', (.88, .61, .18), .8, .24)
red = material('Crimson lacquer', (.31, .023, .029), .26, .35)
leather = material('Dark oxblood leather', (.095, .034, .031), roughness=.87)
steel = material('Tempered steel', (.28, .34, .39), .86, .25)
steelbright = material('Blade cutting edge', (.64, .70, .73), .92, .2)
beard = material('Beard · pearl grey', (.64, .61, .52), roughness=.94)
feather = material('Feather · warm ivory', (.84, .78, .64), roughness=.9)
featherred = material('Pheasant · garnet', (.26, .025, .027), roughness=.7)
feathergold = material('Pheasant · russet barbs', (.52, .19, .04), roughness=.75)


def mesh(name, vertices, faces, mat, bone, smooth=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj.vertex_groups.new(name=bone).add(range(len(vertices)), 1, 'REPLACE')
    for face in data.polygons:
        face.use_smooth = smooth
    parts.append(obj)
    return obj


def loft(name, rings, mat, bone, segments=24):
    """Horizontal elliptical rings produce shaped cloth, anatomy and armor silhouettes."""
    vertices = []
    for x, y, z, rx, ry in rings:
        vertices.extend((x + rx * math.cos(i * math.tau / segments),
                         y + ry * math.sin(i * math.tau / segments), z) for i in range(segments))
    faces = [tuple(range(segments - 1, -1, -1))]
    for k in range(len(rings) - 1):
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((k * segments + i, k * segments + j, (k + 1) * segments + j, (k + 1) * segments + i))
    faces.append(tuple((len(rings) - 1) * segments + i for i in range(segments)))
    return mesh(name, vertices, faces, mat, bone)


def ellipsoid(name, center, scale, mat, bone, segments=24, rings=14):
    x, y, z = center
    rx, ry, rz = scale
    profiles = []
    for i in range(rings + 1):
        a = -.5 * math.pi + i * math.pi / rings
        profiles.append((x, y, z + rz * math.sin(a), max(.0001, rx * math.cos(a)), max(.0001, ry * math.cos(a))))
    return loft(name, profiles, mat, bone, segments)


def tube(name, points, radii, mat, bone, segments=10):
    points = list(map(Vector, points))
    if isinstance(radii, (float, int)):
        radii = [radii] * len(points)
    vertices = []
    for i, p in enumerate(points):
        tangent = points[min(i + 1, len(points) - 1)] - points[max(0, i - 1)]
        tangent.normalize()
        axis = Vector((0, 1, 0)) if abs(tangent.y) < .95 else Vector((1, 0, 0))
        u = tangent.cross(axis).normalized()
        v = tangent.cross(u).normalized()
        for j in range(segments):
            a = j * math.tau / segments
            vertices.append(tuple(p + radii[i] * (math.cos(a) * u + math.sin(a) * v)))
    faces = [tuple(range(segments - 1, -1, -1))]
    for i in range(len(points) - 1):
        for j in range(segments):
            k = (j + 1) % segments
            faces.append((i * segments + j, i * segments + k, (i + 1) * segments + k, (i + 1) * segments + j))
    faces.append(tuple((len(points) - 1) * segments + j for j in range(segments)))
    return mesh(name, vertices, faces, mat, bone)


def curved(name, control, radius, mat, bone, count=20, segments=8):
    a, b, c, d = map(Vector, control)
    points = []
    for i in range(count + 1):
        t = i / count
        points.append((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d)
    radii = [radius * (.32 + .68 * math.sin(math.pi * i / count) ** .3) for i in range(count + 1)]
    return tube(name, points, radii, mat, bone, segments)


def slab(name, center, scale, mat, bone, bevel=.015):
    x, y, z = center
    a, b, c = scale
    obj = mesh(name, [(x + a * i, y + b * j, z + c * k) for i, j, k in
                     [(-1, -1, -1), (-1, -1, 1), (-1, 1, -1), (-1, 1, 1),
                      (1, -1, -1), (1, -1, 1), (1, 1, -1), (1, 1, 1)]],
               [(0, 4, 5, 1), (4, 6, 7, 5), (6, 2, 3, 7), (2, 0, 1, 3), (1, 5, 7, 3), (2, 6, 4, 0)], mat, bone, False)
    if bevel:
        bpy.context.view_layer.objects.active = obj
        modifier = obj.modifiers.new('Rounded crafted edge', 'BEVEL')
        modifier.width, modifier.segments = bevel, 2
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def leaf(name, a, b, width, mat, bone, depth=.012, curve=.035):
    """A curved, pointed solid feather or blade with a visible raised central ridge."""
    a, b = Vector(a), Vector(b)
    direction = (b - a).normalized()
    lateral = direction.cross(Vector((0, 1, 0))).normalized()
    vertices = []
    sections = 12
    for i in range(sections + 1):
        t = i / sections
        p = a.lerp(b, t) + Vector((0, -curve * math.sin(t * math.pi), 0))
        w = width * math.sin(t * math.pi) ** .72
        vertices.extend([tuple(p - lateral * w), tuple(p + Vector((0, -depth, 0))),
                         tuple(p + lateral * w), tuple(p + Vector((0, depth, 0)))])
    faces = []
    for i in range(sections):
        for j in range(4):
            faces.append((i * 4 + j, i * 4 + (j + 1) % 4, (i + 1) * 4 + (j + 1) % 4, (i + 1) * 4 + j))
    faces.extend([(3, 2, 1, 0), tuple(sections * 4 + i for i in range(4))])
    return mesh(name, vertices, faces, mat, bone)


def face(character):
    mat = aged if character == 'wang' else skin
    jaw = {'ikun': (.045, .092, .145, .195, .212),
           'wang': (.067, .122, .184, .218, .220),
           'lubu': (.085, .143, .202, .218, .225)}[character]
    head_rings = [
        (0, -.005, 1.77, jaw[0], .085), (0, -.008, 1.79, jaw[1], .135),
        (0, .005, 1.84, jaw[2], .16), (0, .010, 1.92, jaw[3], .185),
        (0, .015, 2.00, jaw[4], .20), (0, .021, 2.09, .21, .192),
        (0, .031, 2.18, .175, .16), (0, .033, 2.23, .115, .10),
        (0, .033, 2.25, .02, .018)]
    loft('Sculpted jaw cheek and cranium', head_rings, mat, 'head', 40)
    ellipsoid('Neck', (0, .026, 1.75), (.098, .105, .13), mat, 'spine')

    def facial_plane(x, z=2.026):
        for a, b in zip(head_rings, head_rings[1:]):
            if a[2] <= z <= b[2]:
                t = (z - a[2]) / (b[2] - a[2])
                y, rx, ry = [a[i] + t * (b[i] - a[i]) for i in (1, 3, 4)]
                return y - ry * math.sqrt(max(.001, 1 - (x / rx) ** 2))
        raise ValueError('Facial detail outside the authored head')

    def bend_to_face(obj, x):
        center_y = facial_plane(x)
        for vertex in obj.data.vertices:
            vertex.co.y += facial_plane(vertex.co.x) - center_y
        return obj

    def age_line(name, control, width=.0008):
        a, b, c, d = map(Vector, control)
        vertices, faces = [], []
        for i in range(21):
            t = i / 20
            p = (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d
            p.y = facial_plane(p.x, p.z) - .0015
            w = width * math.sin(t * math.pi) ** .4
            vertices.extend([tuple(p + Vector((0, 0, -w))), tuple(p + Vector((0, 0, w)))])
            if i:
                faces.append((2 * i - 2, 2 * i, 2 * i + 1, 2 * i - 1))
        return mesh(name, vertices, faces, crease, 'head')

    # Eyes sit inside the facial silhouette, bounded by almond-shaped eyelids.
    for sign in (-1, 1):
        x = sign * .093
        bend_to_face(ellipsoid('Integrated eye socket', (x, -.163, 2.029), (.048, .012, .021), mat, 'head'), x)
        bend_to_face(ellipsoid('Almond eye', (x, -.181, 2.026), (.039, .007, .014 if character == 'wang' else .016), ivory, 'head', 24, 10), x)
        bend_to_face(ellipsoid('Dark iris', (x, -.190, 2.026), (.014, .004, .013), ink, 'head', 20, 10), x)
        bend_to_face(ellipsoid('Eye catchlight', (x - .004, -.196, 2.031), (.003, .002, .003), ivory, 'head', 8, 6), x)
        bend_to_face(curved('Upper eyelid', [(x - .040, -.178, 2.025), (x - .02, -.191, 2.047),
                                           (x + .026, -.191, 2.045), (x + .041, -.176, 2.025)], .0036, ink, 'head', 16), x)
        bend_to_face(curved('Lower eyelid', [(x - .040, -.177, 2.025), (x - .019, -.186, 2.008),
                                           (x + .022, -.186, 2.008), (x + .040, -.177, 2.025)], .003, mat, 'head', 16), x)
        brow_z = {'ikun': 2.09, 'wang': 2.084, 'lubu': 2.081}[character]
        brow_points = []
        for xx, offset, lift in [(x - .050, .012, 0), (x - .016, .016, .008),
                                 (x + .023, .016, .005), (x + .047, .012, -.008)]:
            zz = brow_z + lift
            if character == 'lubu':
                zz -= .014 * max(0, (.14 - abs(xx)) / .10)
            brow_points.append((xx, facial_plane(xx, zz) - offset, zz))
        curved('Expressive eyebrow', brow_points,
               .012 if character == 'lubu' else .009, beard if character == 'wang' else ink, 'head', 14)
        ellipsoid('Ear helix', (sign * .211, .017, 1.997), (.040, .039, .076), mat, 'head', 20, 10)
        ellipsoid('Ear concha', (sign * .233, -.009, 1.997), (.015, .018, .041), lip, 'head', 16, 8)
    # A defined nose bridge, tip and nostril wings replace the old sphere nose.
    loft('Rounded nose bridge and tip', [(0, -.19, 1.942, .020, .012), (0, -.209, 1.957, .028, .021),
                                       (0, -.211, 1.973, .030, .026), (0, -.198, 1.990, .024, .022),
                                       (0, -.183, 2.015, .017, .018), (0, -.174, 2.040, .020, .011),
                                       (0, -.166, 2.061, .028, .009)], mat, 'head', 24)
    for sign in (-1, 1):
        ellipsoid('Nose wing', (sign * .027, -.204, 1.963), (.015, .014, .011), mat, 'head', 20, 10)
        ellipsoid('Nostril', (sign * .023, -.220, 1.955), (.006, .003, .003), lip, 'head', 12, 6)
    curved('Upper lip', [(-.050, -.155, 1.898), (-.024, -.169, 1.905), (.019, -.169, 1.905),
                         (.050, -.155, 1.898)], .0055, lip, 'head', 16)
    curved('Lower lip', [(-.047, -.154, 1.894), (-.022, -.171, 1.883), (.022, -.171, 1.883),
                         (.047, -.154, 1.894)], .005, mat, 'head', 16)
    if character == 'wang':
        for z, width in [(2.118, .11), (2.138, .09)]:
            age_line('Forehead fine crease', [(-width, 0, z), (-.025, 0, z + .003),
                                             (.025, 0, z + .003), (width, 0, z)])
        for sign in (-1, 1):
            age_line('Nasolabial fine crease', [(sign * .045, 0, 1.956), (sign * .078, 0, 1.941),
                                               (sign * .082, 0, 1.916), (sign * .083, 0, 1.907)])
            age_line('Under eye fine crease', [(sign * .054, 0, 2.007), (sign * .080, 0, 1.996),
                                              (sign * .115, 0, 1.996), (sign * .135, 0, 2.005)])


def hand(side, sign, character):
    mat = aged if character == 'wang' else skin
    bone = 'hand.' + side
    x = sign * .51
    ellipsoid('Palm.' + side, (x, -.055, .938), (.060, .042, .076), mat, bone)
    # Four anatomically separate curled fingers; thumb opposes the weapon grip.
    for i in range(4):
        xx = x + (i - 1.5) * .026
        z = .938 - abs(i - 1.5) * .006
        tube('Curled finger.' + side, [(xx, -.047, z), (xx, -.070, z - .058),
                                     (xx, -.110, z - .061), (xx, -.124, z - .027)],
             [.014, .013, .012, .009], mat, bone, 10)
        ellipsoid('Knuckle.' + side, (xx, -.063, z - .035), (.015, .012, .014), mat, bone, 12, 8)
    tube('Opposing thumb.' + side, [(x - sign * .048, -.041, .965), (x - sign * .065, -.079, .944),
                                  (x - sign * .047, -.122, .942)], [.020, .017, .013], mat, bone, 12)


def base(character):
    shirt = {'ikun': cloth, 'wang': jade, 'lubu': leather}[character]
    mat = aged if character == 'wang' else skin
    loft('Tailored torso', [(0, .022, 1.03, .255, .155), (0, .013, 1.14, .27, .173),
                           (0, .007, 1.33, .29, .185), (0, .014, 1.53, .335, .195),
                           (0, .021, 1.65, .31, .169), (0, .02, 1.69, .22, .122)], shirt, 'spine', 32)
    loft('Hip and waistband', [(0, .015, .96, .24, .155), (0, .012, 1.08, .255, .16),
                              (0, .012, 1.12, .248, .155)], trouser if character == 'ikun' else leather, 'hips')
    face(character)
    for sign, side in [(1, 'L'), (-1, 'R')]:
        arm = 'upper.' + side
        forearm = 'forearm.' + side
        sleeve_radius = .106 if character == 'ikun' else .146
        ellipsoid('Shoulder transition.' + side, (sign * .338, .022, 1.604), (.138, .148, .138), shirt, arm)
        tube('Upper sleeve.' + side, [(sign * .337, .022, 1.64), (sign * .42, .021, 1.49),
                                     (sign * .494, .012, 1.30)], [.125, sleeve_radius, sleeve_radius * .84], shirt, arm, 20)
        ellipsoid('Elbow transition.' + side, (sign * .495, .009, 1.29), (.092, .10, .09), shirt, forearm)
        tube('Tapered forearm.' + side, [(sign * .496, .009, 1.31), (sign * .514, -.014, 1.15),
                                       (sign * .510, -.04, .98)],
             [.087 if character == 'ikun' else .146, .086 if character == 'ikun' else .158, .055 if character == 'ikun' else .10],
             mat if character == 'ikun' else shirt, forearm, 20)
        hand(side, sign, character)
        tube('Trouser thigh.' + side, [(sign * .17, .026, 1.0), (sign * .183, .026, .80),
                                      (sign * .19, .0, .54)], [.14, .127, .098], trouser if character == 'ikun' else leather, 'thigh.' + side, 20)
        ellipsoid('Knee transition.' + side, (sign * .19, .0, .54), (.10, .105, .105), trouser if character == 'ikun' else leather, 'shin.' + side)
        tube('Tapered shin.' + side, [(sign * .19, 0, .54), (sign * .19, .012, .35),
                                    (sign * .19, .012, .145)], [.096, .088, .067], trouser if character == 'ikun' else leather, 'shin.' + side, 20)
        ellipsoid('Shaped boot.' + side, (sign * .19, -.086, .104), (.101, .193, .088), ivory if character == 'ikun' else leather, 'foot.' + side)
        slab('Boot sole.' + side, (sign * .19, -.087, .044), (.105, .183, .025), cloth, 'foot.' + side, .019)
        if character == 'ikun':
            for j in range(4):
                tube('Sneaker lace.' + side, [(sign * .19 - .052, -.10 - j * .023, .173),
                                             (sign * .19 + .052, -.10 - j * .023, .173)], .006, cloth, 'foot.' + side, 6)
            tube('Sleeve hem.' + side, [(sign * .459, -.086, 1.39), (sign * .526, -.070, 1.325)], .008, trouser, arm)
        elif character == 'wang':
            curved('Wide sleeve silk fold.' + side, [(sign * .43, -.092, 1.43), (sign * .51, -.13, 1.21),
                                                   (sign * .52, -.138, 1.09), (sign * .53, -.106, 1.0)], .009, jadelight, forearm, 14)
        else:
            loft('Greave.' + side, [(sign * .19, -.018, .16, .080, .085),
                                   (sign * .19, -.036, .43, .105, .096), (sign * .19, -.027, .53, .101, .10)], steel, 'shin.' + side)
            tube('Greave gold spine.' + side, [(sign * .19, -.120, .19), (sign * .19, -.132, .45)], .012, gold, 'shin.' + side)
    if character == 'ikun':
        ikun_details()
    elif character == 'wang':
        wang_details()
    else:
        lubu_details()


def ikun_details():
    for sign in (-1, 1):
        # Suspender bands follow the chest contour; stitches provide a woven edge.
        curved('Woven suspender front', [(sign * .21, -.104, 1.67), (sign * .20, -.194, 1.56),
                                        (sign * .18, -.198, 1.30), (sign * .18, -.157, 1.10)], .026, ivory, 'spine', 24, 10)
        curved('Woven suspender back', [(sign * .21, .105, 1.67), (sign * .20, .194, 1.54),
                                       (sign * .18, .196, 1.30), (sign * .18, .167, 1.10)], .025, ivory, 'spine', 20, 10)
        for i in range(12):
            z = 1.14 + i * .04
            y = -.187 if z < 1.56 else -.158
            tube('Suspender woven stitch', [(sign * .18 - .015, y - .017, z),
                                           (sign * .18 + .015, y - .017, z + .010)], .0025, trouser, 'spine', 5)
        slab('Suspender buckle', (sign * .18, -.17, 1.12), (.025, .012, .032), steel, 'spine', .007)
    # A low crown under swept ribbons makes a center-parted silhouette rather than two spheres.
    loft('Hair fitted crown', [(0, .052, 2.041, .213, .18), (0, .043, 2.136, .22, .196),
                              (0, .04, 2.233, .178, .17), (0, .042, 2.284, .094, .105),
                              (0, .043, 2.295, .01, .016)], silver, 'head', 32)
    for sign in (-1, 1):
        leaf('Sculpted curtain bang', (sign * .018, -.10, 2.282), (sign * .202, -.088, 2.106),
             .076, silver, 'head', .030, .052)
        for i in range(7):
            x = .016 + i * .011
            start = (sign * x, -.075 + i * .017, 2.287 - i * .002)
            end = (sign * (.194 + .006 * math.sin(i)), -.10 + i * .024, 2.105 + i * .009)
            curved('Swept parted hair lock', [start, (sign * (.10 + i * .007), -.181 + i * .017, 2.275),
                                             (sign * (.216 - i * .003), -.157 + i * .020, 2.193), end],
                   .009 - i * .0005, silver, 'head', 20, 8)
            curved('Swept hair highlight', [start, (sign * (.10 + i * .007), -.183 + i * .017, 2.275),
                                           (sign * (.216 - i * .003), -.167 + i * .020, 2.193), end],
                   .0022, hairlight, 'head', 20, 6)
        curved('Sideburn', [(sign * .20, -.06, 2.15), (sign * .219, -.07, 2.08),
                           (sign * .218, -.034, 2.016), (sign * .205, -.035, 1.995)], .019, silver, 'head', 12)
    ball = Vector((-.51, -.17, .933))
    radius = .188
    ellipsoid('Basketball · round leather shell', ball, (radius, radius, radius), orange, 'hand.R', 36, 24)
    for axis in range(3):
        points = []
        for i in range(97):
            a = i * math.tau / 96
            p = [radius * math.cos(a), radius * math.sin(a), 0]
            if axis == 1:
                p = [p[0], 0, p[1]]
            elif axis == 2:
                p = [0, p[0], p[1]]
            points.append(ball + Vector(p) * 1.003)
        tube('Basketball · great circle channel', points, .0037, seam, 'hand.R', 6)
    for sign in (-1, 1):
        points = []
        for i in range(65):
            a = i * math.tau / 64
            p = Vector((sign * radius * .61, radius * .792 * math.cos(a), radius * .792 * math.sin(a)))
            points.append(ball + p)
        tube('Basketball · curved panel channel', points, .0033, seam, 'hand.R', 6)


def wang_details():
    loft('Draped robe skirt', [(0, .02, .22, .363, .244), (0, .02, .31, .363, .245),
                              (0, .02, .57, .331, .23), (0, .02, .78, .30, .215),
                              (0, .02, 1.02, .262, .17), (0, .02, 1.12, .252, .161)], jade, 'hips', 40)
    for i in range(9):
        x = (i - 4) * .072
        curved('Robe flowing pleat', [(x * .57, -.152, 1.01), (x * .83, -.208, .83),
                                    (x * 1.04, -.242, .52), (x * 1.12, -.223, .23)],
               .009 + .001 * (i % 2), jadelight, 'hips', 22)
    for sign in (-1, 1):
        curved('Crossed embroidered lapel', [(sign * .145, -.107, 1.685), (sign * .122, -.175, 1.61),
                                           (-sign * .06, -.199, 1.37), (-sign * .155, -.175, 1.14)], .028, ivory, 'spine', 24)
        curved('Lapel gold embroidery', [(sign * .178, -.107, 1.67), (sign * .145, -.182, 1.58),
                                        (-sign * .04, -.207, 1.35), (-sign * .125, -.184, 1.14)], .005, gold, 'spine', 24)
    loft('Court belt', [(0, .016, 1.07, .263, .179), (0, .016, 1.13, .264, .18)], leather, 'hips')
    slab('Belt jade clasp', (0, -.181, 1.10), (.061, .021, .032), gold, 'hips', .009)
    ellipsoid('Clasp jade inset', (0, -.206, 1.10), (.039, .009, .022), jadelight, 'hips')
    # Multiple tapered curved ribbons form a groomed, forked beard and moustache.
    for i in range(11):
        x = (i - 5) * .016
        tip = 1.535 + abs(i - 5) * .014
        curved('Flowing beard strand', [(x, -.157, 1.839), (x * 1.19, -.211, 1.761),
                                        (x * .81, -.207, 1.614), (x * .75, -.189, tip)],
               .022 - abs(i - 5) * .0016, beard, 'head', 22, 10)
        curved('Beard highlight groove', [(x, -.18, 1.82), (x * 1.15, -.231, 1.73),
                                         (x * .83, -.223, 1.63), (x * .75, -.194, tip)], .003, ivory, 'head', 20, 6)
    for sign in (-1, 1):
        curved('Swept moustache', [(sign * .006, -.204, 1.917), (sign * .04, -.214, 1.921),
                                  (sign * .095, -.193, 1.882), (sign * .11, -.159, 1.852)], .019, beard, 'head', 18, 10)
        curved('Temple silver hair', [(sign * .193, .015, 2.15), (sign * .213, -.005, 2.08),
                                     (sign * .204, -.014, 1.988), (sign * .192, .022, 1.95)], .025, beard, 'head', 14)
    loft('Court hat shaped crown', [(0, .04, 2.157, .208, .18), (0, .04, 2.23, .216, .174),
                                   (0, .07, 2.34, .172, .15), (0, .07, 2.38, .155, .14)], cloth, 'head')
    curved('Court hat gold piping', [(-.195, -.117, 2.21), (-.095, -.142, 2.208),
                                    (.095, -.142, 2.208), (.195, -.117, 2.21)], .009, gold, 'head', 24)
    for sign in (-1, 1):
        slab('Court hat wing', (sign * .385, .052, 2.251), (.185, .04, .027), cloth, 'head', .024)
        tube('Hat wing seam', [(sign * .24, .014, 2.26), (sign * .535, .014, 2.26)], .005, gold, 'head')
    ellipsoid('Hat jade medallion', (0, -.116, 2.258), (.042, .019, .055), gold, 'head')
    ellipsoid('Hat jade stone', (0, -.139, 2.258), (.024, .007, .034), jadelight, 'head')
    handle = Vector((-.51, -.14, .90))
    tube('Fan · carved handle', [handle + Vector((0, 0, -.12)), handle + Vector((0, 0, .27))], [.014, .022], gold, 'hand.R', 14)
    for i in range(11):
        angle = (i - 5) * .128
        a = handle + Vector((math.sin(angle) * .040, -.005, .16))
        b = handle + Vector((math.sin(angle) * .52, -.017, .15 + math.cos(angle) * .42))
        leaf('Fan · layered feather', a, b, .036, feather if i % 2 else ivory, 'hand.R', .006, .022)
        tube('Fan · visible feather rachis', [a + Vector((0, -.023, 0)), b + Vector((0, -.009, 0))], [.003, .0012], gold, 'hand.R', 6)
        for j in range(2, 7):
            t = j / 8
            p = a.lerp(b, t) + Vector((0, -.025, 0))
            lateral = Vector((math.cos(angle), 0, -math.sin(angle)))
            for sign in (-1, 1):
                tube('Fan · feather fine barb', [p, p + lateral * sign * .021 + Vector((0, -.001, -.012))], .0013, beard, 'hand.R', 4)


def crescent(name, center, radius, width, mat, bone):
    """Concave crescent is a real annular blade, not an ellipsoid substitute."""
    center = Vector(center)
    vertices, faces = [], []
    count = 32
    for i in range(count + 1):
        t = i / count
        angle = -math.pi * .60 + t * math.pi * 1.20
        for r in (radius, radius - width * math.sin(math.pi * t) ** .65):
            for y in (-.013, .013):
                vertices.append(tuple(center + Vector((-r * math.cos(angle), y, r * math.sin(angle)))))
    for i in range(count):
        a, b = i * 4, (i + 1) * 4
        faces.extend([(a, b, b + 2, a + 2), (a + 1, a + 3, b + 3, b + 1),
                      (a, a + 1, b + 1, b), (a + 2, b + 2, b + 3, a + 3)])
    faces.extend([(0, 2, 3, 1), (count * 4, count * 4 + 1, count * 4 + 3, count * 4 + 2)])
    mesh(name, vertices, faces, mat, bone)


def lubu_details():
    loft('Molded cuirass', [(0, .019, 1.13, .266, .18), (0, .008, 1.36, .311, .204),
                          (0, .018, 1.56, .345, .21), (0, .025, 1.64, .303, .172)], red, 'spine', 32)
    for sign in (-1, 1):
        curved('Cuirass gold shoulder edging', [(sign * .27, -.061, 1.65), (sign * .34, -.163, 1.56),
                                               (sign * .28, -.199, 1.39), (sign * .254, -.174, 1.16)], .012, gold, 'spine', 24)
        curved('Leather cross body strap', [(sign * .24, -.130, 1.63), (sign * .13, -.23, 1.49),
                                            (-sign * .05, -.218, 1.32), (-sign * .20, -.191, 1.16)], .027, leather, 'spine', 20)
    for row in range(4):
        z = 1.22 + row * .080
        for col in range(7):
            x = (col - 3) * .074
            y = -.201 + .095 * (abs(x) / .3) ** 2
            slab('Chest lamella scale', (x, y, z), (.032, .020, .046), gold if row == 3 else steel, 'spine', .01)
            for side in (-1, 1):
                ellipsoid('Lamella fastening rivet', (x + side * .020, y - .022, z + .026), (.0048, .0033, .0048), goldlight, 'spine', 8, 6)
    ellipsoid('Lion chest medallion', (0, -.222, 1.527), (.084, .021, .075), gold, 'spine')
    for sign in (-1, 1):
        curved('Lion medallion brow', [(sign * .007, -.246, 1.55), (sign * .023, -.258, 1.557),
                                     (sign * .051, -.251, 1.546), (sign * .055, -.24, 1.539)], .008, goldlight, 'spine', 10)
    ellipsoid('Lion medallion muzzle', (0, -.25, 1.508), (.026, .009, .026), goldlight, 'spine')
    for sign, side in [(1, 'L'), (-1, 'R')]:
        for row in range(3):
            ellipsoid('Layered shoulder pauldron.' + side, (sign * (.342 + row * .032), .015, 1.654 - row * .062),
                      (.183 - row * .015, .165 - row * .012, .08), red if row != 1 else gold, 'upper.' + side, 24, 10)
            curved('Shoulder pauldron gold lip', [(sign * (.225 + row * .015), -.097, 1.652 - row * .061),
                                               (sign * (.34 + row * .025), -.173, 1.66 - row * .061),
                                               (sign * (.46 + row * .03), -.115, 1.64 - row * .061),
                                               (sign * (.49 + row * .027), -.022, 1.64 - row * .061)], .010, gold, 'upper.' + side, 18)
        loft('Armored gauntlet.' + side, [(sign * .51, -.026, 1.0, .076, .083),
                                        (sign * .512, -.013, 1.15, .096, .105),
                                        (sign * .501, -.005, 1.28, .102, .105)], red, 'forearm.' + side)
        tube('Gauntlet gold ridge.' + side, [(sign * .512, -.126, 1.02), (sign * .501, -.114, 1.24)], .014, gold, 'forearm.' + side)
    loft('Layered waist leather skirt', [(0, .02, .69, .335, .23), (0, .02, .98, .282, .184),
                                       (0, .02, 1.09, .257, .171)], leather, 'hips', 32)
    for col in range(9):
        angle = col * math.tau / 9
        for row in range(3):
            r = .285 + row * .018
            x, y = math.cos(angle) * r, .018 + math.sin(angle) * r * .67
            z = .98 - row * .095
            obj = slab('Hanging lamellar tasset', (x, y, z), (.052, .022, .062), red if row != 1 else steel, 'hips', .014)
            rotation = Matrix.Rotation(angle + .5 * math.pi, 4, 'Z')
            midpoint = Vector((x, y, z))
            for v in obj.data.vertices:
                v.co = midpoint + rotation.to_3x3() @ (v.co - midpoint)
    loft('Armor girdle', [(0, .02, 1.043, .281, .197), (0, .02, 1.11, .273, .19)], gold, 'hips')
    ellipsoid('Girdle ornament', (0, -.187, 1.077), (.072, .021, .043), red, 'hips')
    loft('Helmet fitted crown', [(0, .027, 2.10, .219, .187), (0, .038, 2.17, .224, .198),
                                (0, .045, 2.28, .186, .166), (0, .045, 2.335, .074, .082),
                                (0, .045, 2.35, .016, .022)], red, 'head', 32)
    curved('Helmet eyebrow gold crown', [(-.213, -.091, 2.115), (-.14, -.184, 2.14),
                                        (.14, -.184, 2.14), (.213, -.091, 2.115)], .014, gold, 'head', 28)
    leaf('Helmet central crest', (0, -.142, 2.13), (0, -.126, 2.33), .055, gold, 'head', .012, .022)
    for sign in (-1, 1):
        leaf('Helmet temple guard', (sign * .205, -.032, 2.16), (sign * .213, -.003, 1.935), .041, red, 'head', .014, .015)
        control = [(sign * .128, .032, 2.305), (sign * .23, .0, 3.04),
                   (sign * .55, .14, 3.17), (sign * .64, .35, 2.72)]
        curved('Pheasant plume curved rachis', control, .013, gold, 'head', 40)
        a, b, c, d = map(Vector, control)
        for i in range(22):
            t = (i + 1) / 24
            p = (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d
            tangent = (-3 * (1 - t) ** 2 * a + (3 * (1 - t) ** 2 - 6 * t * (1 - t)) * b +
                       (6 * t * (1 - t) - 3 * t * t) * c + 3 * t * t * d).normalized()
            lateral = tangent.cross(Vector((0, 1, 0))).normalized()
            width = .028 + .048 * math.sin(t * math.pi)
            for flank in (-1, 1):
                q = p + lateral * flank * width - tangent * .054 + Vector((0, -.005, 0))
                leaf('Pheasant layered plume vane', p, q, .017, featherred if i % 3 else feathergold, 'head', .004, .008)
    shaft = Vector((-.51, -.126, .98))
    tube('Halberd · lacquer shaft', [shaft + Vector((0, 0, -.71)), shaft + Vector((0, 0, 1.37))], .020, leather, 'hand.R', 16)
    for z in (.34, .62, 1.07, 1.91, 2.21):
        loft('Halberd · engraved brass collar', [(-.51, -.126, z, .030, .030), (-.51, -.126, z + .038, .030, .030)], gold, 'hand.R', 16)
    leaf('Halberd · pointed spear blade', (-.51, -.126, 2.24), (-.51, -.126, 2.64), .069, steelbright, 'hand.R', .017, .0)
    crescent('Halberd · true crescent blade', (-.495, -.126, 2.125), .242, .087, steel, 'hand.R')
    crescent('Halberd · sharpened crescent edge', (-.495, -.127, 2.125), .245, .019, steelbright, 'hand.R')
    for z in (1.96, 2.29):
        tube('Halberd · blade support', [(-.51, -.126, z), (-.61, -.126, z)], .016, gold, 'hand.R')
    for i in range(12):
        z = .875 + i * .018
        loft('Halberd · wrapped grip', [(-.51, -.126, z, .025, .025), (-.51, -.126, z + .006, .025, .025)], cloth, 'hand.R', 12)


def rig(character):
    data = bpy.data.armatures.new(character + '_skeleton')
    obj = bpy.data.objects.new(character + '_rig', data)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    specs = {'root': ((0, 0, 0), (0, 0, .35), None),
             'hips': ((0, .02, 1.02), (0, .02, 1.16), 'root'),
             'spine': ((0, .02, 1.16), (0, .02, 1.735), 'hips'),
             'head': ((0, .025, 1.735), (0, .025, 2.22), 'spine')}
    for side, sign in [('L', 1), ('R', -1)]:
        specs.update({'upper.' + side: ((sign * .337, .022, 1.64), (sign * .496, .009, 1.30), 'spine'),
                      'forearm.' + side: ((sign * .496, .009, 1.30), (sign * .51, -.04, .98), 'upper.' + side),
                      'hand.' + side: ((sign * .51, -.04, .98), (sign * .51, -.055, .82), 'forearm.' + side),
                      'thigh.' + side: ((sign * .17, .026, 1.0), (sign * .19, 0, .54), 'hips'),
                      'shin.' + side: ((sign * .19, 0, .54), (sign * .19, .012, .145), 'thigh.' + side),
                      'foot.' + side: ((sign * .19, .012, .145), (sign * .19, -.20, .07), 'shin.' + side)})
    for name, (head, tail, parent) in specs.items():
        b = data.edit_bones.new(name)
        b.head, b.tail = head, tail
        if parent:
            b.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
    for b in obj.pose.bones:
        b.rotation_mode = 'QUATERNION'
    return obj


def two_bone(a, end, length1, length2, pole):
    axis = end - a
    distance = min(axis.length, length1 + length2 - .003)
    distance = max(distance, abs(length1 - length2) + .002)
    axis.normalize()
    end = a + axis * distance
    bend = pole - axis * pole.dot(axis)
    bend.normalize()
    projected = (length1 * length1 - length2 * length2 + distance * distance) / (2 * distance)
    height = math.sqrt(max(0, length1 * length1 - projected * projected))
    return a + axis * projected + bend * height, end


def pose(armature, settings):
    bones = armature.data.bones
    globals_ = {}
    root = Vector(settings.get('root', (0, 0, 0)))
    crouch = settings.get('crouch', 0)
    hip_rotation = Euler((0, 0, settings.get('hip_yaw', 0))).to_quaternion()
    spine_rotation = hip_rotation @ Euler(settings.get('torso', (0, 0, 0))).to_quaternion()
    head_rotation = spine_rotation @ Euler(settings.get('head', (0, 0, 0))).to_quaternion()
    hip = bones['hips'].head_local + root + Vector((0, 0, -crouch))
    spine = hip + hip_rotation @ (bones['spine'].head_local - bones['hips'].head_local)
    head = spine + spine_rotation @ (bones['head'].head_local - bones['spine'].head_local)

    def set_bone(name, point, rotation=None, direction=None):
        b = bones[name]
        if direction is not None:
            rotation = (b.tail_local - b.head_local).rotation_difference(direction.normalized())
        orientation = rotation @ b.matrix_local.to_quaternion() if rotation is not None else b.matrix_local.to_quaternion()
        world = Matrix.Translation(point) @ orientation.to_matrix().to_4x4()
        globals_[name] = world
        parent_args = {}
        if b.parent:
            parent_args = {'parent_matrix': globals_[b.parent.name], 'parent_matrix_local': b.parent.matrix_local}
        basis = b.convert_local_to_pose(world, b.matrix_local, invert=True, **parent_args)
        armature.pose.bones[name].matrix_basis = basis

    set_bone('root', root)
    set_bone('hips', hip, hip_rotation)
    set_bone('spine', spine, spine_rotation)
    set_bone('head', head, head_rotation)
    for side, sign in [('L', 1), ('R', -1)]:
        thigh = hip + hip_rotation @ (bones['thigh.' + side].head_local - bones['hips'].head_local)
        foot = bones['foot.' + side].head_local + Vector(settings.get('step.' + side, (0, 0, 0)))
        knee, foot = two_bone(thigh, foot, bones['thigh.' + side].length, bones['shin.' + side].length, Vector((0, -1, .1)))
        set_bone('thigh.' + side, thigh, direction=knee - thigh)
        set_bone('shin.' + side, knee, direction=foot - knee)
        set_bone('foot.' + side, foot)
        shoulder = spine + spine_rotation @ (bones['upper.' + side].head_local - bones['spine'].head_local)
        wrist = Vector(settings.get('wrist.' + side, (sign * .51, -.095, 1.015)))
        wrist = spine + spine_rotation @ (wrist - bones['spine'].head_local)
        pole = spine_rotation @ Vector((sign * 1, .22, .15))
        elbow, wrist = two_bone(shoulder, wrist, bones['upper.' + side].length, bones['forearm.' + side].length, pole)
        set_bone('upper.' + side, shoulder, direction=elbow - shoulder)
        set_bone('forearm.' + side, elbow, direction=wrist - elbow)
        direction = spine_rotation @ Vector(settings.get('fingers.' + side, (0, -.06, -1)))
        set_bone('hand.' + side, wrist, direction=direction)


def mix_pose(a, b, t):
    keys = a.keys() | b.keys()
    result = {}
    for key in keys:
        value_a, value_b = a.get(key, b[key] if key in b else None), b.get(key, a[key] if key in a else None)
        if isinstance(value_a, (tuple, list)):
            result[key] = tuple(x + (y - x) * t for x, y in zip(value_a, value_b))
        else:
            result[key] = value_a + (value_b - value_a) * t
    return result


def animate(armature, character):
    # Hands sit clear of the torso; feet stay planted while hips load and unwind.
    rest = {'root': (0, 0, 0), 'crouch': .018, 'hip_yaw': -.055,
            'torso': (.018, 0, .055), 'head': (0, 0, -.025),
            'wrist.L': (.49, -.20, 1.10), 'wrist.R': (-.50, -.16, 1.07),
            'fingers.L': (0, -.2, -1), 'fingers.R': (0, -.08, -1)}
    # Distinct weapon choreography: basketball thrust/hook/dunk, fan sweep/palm/point,
    # and diagonal halberd slash/overhead chop/reverse sweep. Contact is shared with FX.
    strikes = {
        'ikun': {
            'attack': ({'wrist.R': (-.44, .10, 1.28), 'torso': (-.055, 0, -.27), 'crouch': .055},
                       {'wrist.R': (-.23, -.57, 1.47), 'fingers.R': (0, -.75, -.5), 'torso': (.14, 0, .24), 'wrist.L': (.37, -.26, 1.36)}),
            'heavy': ({'wrist.R': (-.50, .08, 1.13), 'torso': (.12, -.06, -.36), 'crouch': .11},
                      {'wrist.R': (.03, -.56, 1.41), 'fingers.R': (.55, -.7, -.5), 'torso': (.09, -.04, .48), 'wrist.L': (.38, -.18, 1.47)}),
            'special': ({'wrist.R': (-.21, -.09, 2.15), 'wrist.L': (.23, -.13, 1.95), 'fingers.R': (0, .55, -.6), 'torso': (-.1, 0, -.12), 'crouch': .06},
                        {'wrist.R': (-.16, -.49, 1.80), 'wrist.L': (.19, -.47, 1.75), 'fingers.R': (0, -.3, -1), 'torso': (.23, 0, .1), 'crouch': .12})},
        'wang': {
            'attack': ({'wrist.R': (-.56, .08, 1.19), 'torso': (-.03, 0, -.23), 'crouch': .04},
                       {'wrist.R': (-.12, -.48, 1.33), 'fingers.R': (-.4, .12, -1), 'torso': (.055, 0, .34), 'wrist.L': (.32, -.24, 1.30)}),
            'heavy': ({'wrist.R': (-.30, -.09, 1.49), 'wrist.L': (.28, -.07, 1.37), 'torso': (-.07, 0, -.16), 'crouch': .06},
                      {'wrist.R': (-.25, -.55, 1.47), 'wrist.L': (.19, -.58, 1.44), 'fingers.L': (0, -.85, -.3), 'torso': (.12, 0, .12)}),
            'special': ({'wrist.R': (-.49, -.1, 1.46), 'wrist.L': (.37, -.1, 1.73), 'torso': (-.03, -.05, -.24), 'head': (0, 0, -.1)},
                        {'wrist.R': (-.33, -.42, 1.38), 'wrist.L': (.22, -.58, 1.60), 'fingers.L': (0, -.9, -.2), 'torso': (.12, 0, .15), 'head': (.07, 0, .025)})},
        'lubu': {
            'attack': ({'wrist.R': (-.48, .01, 1.49), 'fingers.R': (-.24, -.15, -1), 'torso': (-.07, 0, -.34), 'crouch': .06},
                       {'wrist.R': (-.12, -.50, 1.41), 'fingers.R': (.26, .86, -.42), 'torso': (.11, -.04, .35), 'wrist.L': (.22, -.33, 1.34)}),
            'heavy': ({'wrist.R': (-.18, -.09, 2.08), 'wrist.L': (.17, -.19, 1.93), 'fingers.R': (0, -.7, -.7), 'torso': (-.16, 0, -.12), 'crouch': .04},
                      {'wrist.R': (-.19, -.48, 1.43), 'wrist.L': (.14, -.38, 1.35), 'fingers.R': (0, .82, -.58), 'torso': (.22, 0, .12), 'crouch': .10}),
            'special': ({'wrist.R': (.03, -.05, 1.45), 'fingers.R': (.85, .25, -.45), 'wrist.L': (.43, -.13, 1.46), 'torso': (.0, 0, .54), 'crouch': .11, 'hip_yaw': .18},
                        {'wrist.R': (-.49, -.40, 1.48), 'fingers.R': (-.8, .45, -.3), 'wrist.L': (.29, -.28, 1.40), 'torso': (.12, -.07, -.58), 'hip_yaw': -.17})}}
    durations = {'idle': 200, 'attack': 145, 'heavy': 145, 'guard': 145, 'special': 145, 'hurt': 90, 'victory': 200}
    armature.animation_data_create()
    for name, frames in durations.items():
        action = bpy.data.actions.new(name)
        armature.animation_data.action = action
        times = {i / frames for i in range(frames + 1)}
        times.add(CONTACT)
        if name in strikes[character]:
            windup, hit = strikes[character][name]
            windup, hit = rest | windup, rest | hit
            hit['root'] = (0, -.04 if name == 'attack' else -.065, 0)
            follow = dict(hit)
            follow['torso'] = tuple(a * 1.07 for a in hit['torso'])
            follow['wrist.R'] = (hit['wrist.R'][0] + (.045 if character != 'lubu' else -.055),
                                 hit['wrist.R'][1] + .03, hit['wrist.R'][2] - .06)
            if character == 'lubu' and name == 'heavy':
                follow['fingers.R'] = (0, .94, -.15)
            if character == 'ikun' and name == 'special':
                follow['wrist.R'] = (-.13, -.46, 1.48)
                follow['wrist.L'] = (.16, -.46, 1.42)
            knots = [(0, rest), (.20, windup), (.32, windup), (CONTACT, hit), (.49, follow), (.65, mix_pose(hit, rest, .48)), (1, rest)]
        for t in sorted(times):
            if name in strikes[character]:
                for (ta, a), (tb, b) in zip(knots, knots[1:]):
                    if ta <= t <= tb:
                        u = (t - ta) / (tb - ta)
                        u = u * u * (3 - 2 * u)
                        settings = mix_pose(a, b, u)
                        break
            elif name == 'idle':
                settings = rest | {'crouch': .018 + .007 * math.sin(t * math.tau),
                                   'torso': (.018 + .008 * math.sin(t * math.tau), .004 * math.sin(t * math.tau), .055),
                                   'head': (.006 * math.sin(t * math.tau), 0, -.025)}
            elif name == 'guard':
                shield = rest | {'crouch': .10, 'torso': (.065, 0, -.08), 'head': (.08, 0, .04),
                                 'wrist.L': (.22, -.35, 1.68), 'wrist.R': (-.21, -.37, 1.57),
                                 'fingers.L': (0, -.12, -1), 'fingers.R': (0, -.15, -1)}
                if character == 'lubu':
                    shield['fingers.R'] = (-.87, 0, -.5)
                    shield['wrist.R'] = (-.36, -.34, 1.38)
                envelope = min(1, t / .16, (1 - t) / .22)
                settings = mix_pose(rest, shield, max(0, envelope))
                settings['torso'] = (settings['torso'][0] - .06 * math.exp(-((t - CONTACT) / .045) ** 2), *settings['torso'][1:])
            elif name == 'hurt':
                recoil = rest | {'root': (.025, .09, 0), 'crouch': .08, 'torso': (-.20, .11, -.12),
                                 'head': (-.15, -.08, .08), 'wrist.L': (.53, -.06, 1.13), 'wrist.R': (-.51, .05, 1.06)}
                envelope = min(1, t / .11) * (1 - t) ** 1.15
                settings = mix_pose(rest, recoil, envelope)
            else:
                celebratory = rest | {'crouch': .022, 'torso': (-.03, 0, .06 * math.sin(t * math.tau)),
                                      'wrist.L': (.21, -.06, 2.11), 'wrist.R': (-.43, -.05, 1.49),
                                      'head': (-.04, 0, .05 * math.sin(t * math.tau)), 'fingers.L': (0, .4, -.8)}
                if character == 'ikun':
                    celebratory['wrist.R'] = (-.19, -.13, 2.11)
                settings = mix_pose(rest, celebratory, min(1, t / .17, (1 - t) / .17))
            pose(armature, settings)
            for b in armature.pose.bones:
                b.keyframe_insert('rotation_quaternion', frame=t * frames, group=b.name)
                b.keyframe_insert('location', frame=t * frames, group=b.name)
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag = strip.channelbag(slot)
                    if bag:
                        for curve in bag.fcurves:
                            for key in curve.keyframe_points:
                                key.interpolation = 'LINEAR'
        track = armature.animation_data.nla_tracks.new()
        track.name = name
        strip = track.strips.new(name, 0, action)
        strip.action_frame_start, strip.action_frame_end = 0, frames
        track.mute = True
    armature.animation_data.action = None
    for b in armature.pose.bones:
        b.matrix_basis = Matrix.Identity(4)


def tag_face_parts():
    for obj in parts:
        tag = None
        if obj.name.startswith(('Almond eye', 'Dark iris', 'Eye catchlight')):
            tag = 'expression.eye'
        elif obj.name.startswith(('Upper eyelid', 'Lower eyelid')):
            tag = 'expression.lid'
        elif obj.name.startswith('Expressive eyebrow'):
            tag = 'expression.brow'
        elif obj.name.startswith(('Upper lip', 'Lower lip')):
            tag = 'expression.lip'
        if tag:
            obj.vertex_groups.new(name=tag).add(range(len(obj.data.vertices)), 1, 'REPLACE')


def face_controls(body):
    basis = body.shape_key_add(name='Basis', from_mix=False)
    tags = {group.index: group.name for group in body.vertex_groups if group.name.startswith('expression.')}
    for name in ('blink', 'angry', 'smile', 'hurt'):
        # Blender's mixed evaluated shape can retain the preceding expression.
        key = body.shape_key_add(name=name, from_mix=False)
        key.relative_key = basis
        key.slider_min, key.slider_max = 0, 1
        for vertex in body.data.vertices:
            key.data[vertex.index].co = basis.data[vertex.index].co
            tag = next((tags[g.group] for g in vertex.groups if g.group in tags), None)
            if not tag:
                continue
            p = key.data[vertex.index].co
            if name in ('blink', 'hurt'):
                if tag == 'expression.eye':
                    p.z = 2.024 + (p.z - 2.026) * (.035 if name == 'blink' else .27)
                    if name == 'blink':
                        p.y += .010
                elif tag == 'expression.lid':
                    p.z = 2.024 + (p.z - 2.026) * (.04 if name == 'blink' else .33)
                elif name == 'hurt' and tag == 'expression.brow':
                    p.z += .009 + max(0, .1 - abs(p.x)) * .11
                elif name == 'hurt' and tag == 'expression.lip':
                    p.z -= .008 * abs(p.x) / .055
            elif name == 'angry':
                if tag == 'expression.brow':
                    p.z -= .007 + max(0, .13 - abs(p.x)) * .22
                    p.y -= .006
                elif tag in ('expression.eye', 'expression.lid'):
                    p.z = 2.022 + (p.z - 2.026) * .74
                elif tag == 'expression.lip':
                    p.x *= .93
                    p.z -= .004 * abs(p.x) / .055
            elif name == 'smile' and tag == 'expression.lip':
                p.z += .023 * (abs(p.x) / .055) ** 1.2
                p.x *= 1.08
                p.y -= .005
        assert any((a.co - b.co).length > .0001 for a, b in zip(body.data.vertices, key.data)), name + ' facial control is empty'


for character in ['ikun', 'wang', 'lubu']:
    parts = []
    base(character)
    tag_face_parts()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = character + '_body'
    face_controls(body)
    body.select_set(False)
    armature = rig(character)
    modifier = body.modifiers.new('Skeleton', 'ARMATURE')
    modifier.object = armature
    body.parent = armature
    animate(armature, character)
    bpy.context.scene.frame_set(1)
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(filepath=str(OUT / (character + '.glb')), export_format='GLB', use_selection=True,
                              export_animations=True, export_animation_mode='NLA_TRACKS', export_skins=True,
                              export_force_sampling=True, export_nla_strips=True)
    body.data.calc_loop_triangles()
    assert len(body.data.loop_triangles) < 80000, character + ' exceeded the triangle budget'
    print(f'{character}: {len(body.data.vertices)} vertices / {len(body.data.loop_triangles)} triangles; 16 bones; 7 clips')
    armature.location.x = {'ikun': -2.4, 'wang': 0, 'lubu': 2.4}[character]

bpy.ops.object.select_all(action='DESELECT')
bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, 200
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE / 'all-stars.blend'))
print('Created 3 authored characters; contact phase', CONTACT)
