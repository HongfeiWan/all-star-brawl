"""Authored appearance profiles, cloth construction and clean deformation for the roster.

Source references describe the chosen costume; backs and stylized proportions are inferred.
The 16-bone engine contract stays compatible with the four shared motion libraries.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
import make_characters as F

PROFILES = json.loads((Path(__file__).resolve().parents[1] / 'art/character-profiles.json').read_text())


def front(x, z, width=1):
    # Torso envelope shared with make_roster; seam thickness sits above its surface.
    levels = [(1.03, .255, .16), (1.18, .258, .17), (1.40, .30, .19), (1.56, .333, .19), (1.66, .30, .166)]
    for a, b in zip(levels, levels[1:]):
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            rx = (a[1] + (b[1] - a[1]) * t) * width
            ry = a[2] + (b[2] - a[2]) * t
            return .016 - ry * math.sqrt(max(.05, 1 - (x / rx) ** 2)) - .008
    return -.12


def line(name, coordinates, material, bone='spine', radius=.003):
    return F.tube(name, coordinates, radius, material, bone, 6)


def clothing(c, m, width):
    details = set(c['details'])
    outfit = c['outfit']
    bare = outfit in ('bare', 'tank', 'vest', 'monk')
    for obj in list(F.parts):
        if obj.name.startswith(('Shoulder cap.', 'Upper arm.', 'Elbow.', 'Forearm.', 'Folded collar lapel', 'Shirt pointed collar')):
            F.parts.remove(obj)
            bpy.data.objects.remove(obj, do_unlink=True)
    # Continuous ring topology replaces intersecting shoulder/elbow spheres.
    for sign, side in [(1, 'L'), (-1, 'R')]:
        F.ellipsoid('Soft sewn shoulder.' + side, (sign * .326, .019, 1.616), (.116 * width, .108, .099),
                    m['skin'] if bare else m['main'], 'upper.' + side, 24, 14)
        coordinates = [(sign * (.335 + .175 * t), .022 - .062 * t, 1.64 - .66 * t) for t in [i / 12 for i in range(13)]]
        radii = [(.112 * (1 - i / 12) + .052 * i / 12) * width for i in range(13)]
        if outfit in ('shirt', 'school', 'suspenders'):
            F.tube('Continuous short sleeve.' + side, coordinates[:7], radii[:7], m['main'], 'upper.' + side, 20)
            F.tube('Continuous exposed forearm.' + side, coordinates[6:], radii[6:], m['skin'], 'upper.' + side, 20)
        else:
            F.tube('Continuous fitted arm.' + side, coordinates, radii, m['skin'] if bare else m['main'], 'upper.' + side, 20)
    if outfit in ('shirt', 'school', 'suspenders', 'suit', 'jacket', 'openjacket', 'coat', 'uniform', 'cook') and c['id'] != 'huaqiang':
        for sign in (-1, 1):
            vertices = [(sign * .075, -.12, 1.69), (sign * .175, -.12, 1.65),
                        (sign * .16, -.185, 1.53), (sign * .057, -.177, 1.615)]
            F.mesh('Tailored flat folded collar', vertices + [(x, y + .007, z) for x, y, z in vertices],
                   [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)],
                   m['white'] if outfit in ('shirt', 'school', 'suspenders') else m['main'], 'spine', False)
    soft = F.material(c['id'] + ' · raised cloth weave', tuple(v * .87 for v in m['main'].diffuse_color[:3]), roughness=.95)
    if not bare and outfit != 'mascot':
        # A quiet hem and tension folds read as cloth without covering the garment in lines.
        coords = [(x, front(x, 1.10, width), 1.10) for x in [i * .035 * width for i in range(-6, 7)]]
        line('Garment double stitched hem', coords, soft)
        for sign, side in [(1, 'L'), (-1, 'R')]:
            for i in range(3):
                x = sign * (.17 + i * .019) * width
                z = 1.18 + i * .053
                F.curved('Waist cloth tension fold', [(x, front(x, z, width), z),
                    (x * 1.12, front(x * 1.12, z + .035, width), z + .035),
                    (x * 1.16, front(x * 1.16, z + .055, width), z + .055),
                    (x * 1.23, front(x * 1.23, z + .068, width), z + .068)], .0038, soft, 'spine', 16, 6)
            F.loft('Bound sleeve cuff.' + side, [(sign * .51, -.038, .99, .057, .055),
                                               (sign * .51, -.035, 1.025, .06, .058)], m['trim'], 'forearm.' + side)
    for sign, side in [(1, 'L'), (-1, 'R')]:
        line('Trouser outside seam.' + side, [(sign * .29, .013, .88), (sign * .283, -.005, .70),
             (sign * .278, -.010, .57)], soft, 'thigh.' + side)
        line('Boot welt stitching.' + side, [(sign * .19 - .075, -.18, .072), (sign * .19, -.248, .065),
             (sign * .19 + .075, -.18, .072)], m['trim'], 'foot.' + side)
        if 'sport' in details or 'denim' in details:
            for i in range(4):
                line('Shoe lace.' + side, [(sign * .19 - .042, -.10 - i * .023, .170),
                     (sign * .19 + .042, -.10 - i * .023, .170)], m['white'], 'foot.' + side, .0035)
        if 'muscle' in details:
            F.ellipsoid('Defined deltoid.' + side, (sign * .35, -.018, 1.56), (.131, .13, .12), m['skin'], 'upper.' + side)
            F.curved('Forearm tendon.' + side, [(sign * .502, -.086, 1.25), (sign * .513, -.093, 1.16),
                 (sign * .52, -.10, 1.08), (sign * .515, -.09, 1.025)], .0025, soft, 'forearm.' + side, 16, 6)
    if 'shirt' in details or 'tailored' in details or 'school' in details:
        if outfit == 'shirt':
            line('Shirt button placket', [(0, front(0, z, width) - .001, z) for z in (1.12, 1.3, 1.5, 1.61)], m['trim'])
            for z in (1.20, 1.30, 1.40, 1.50, 1.60):
                F.ellipsoid('Pearl shirt button', (0, front(0, z, width) - .004, z), (.0045, .003, .0045), m['white'], 'spine', 10, 6)
        for sign in (-1, 1):
            if 'tailored' in details:
                line('Tailored lapel edge', [(sign * .17, -.125, 1.68), (sign * .13, -.194, 1.57),
                     (sign * .067, -.207, 1.41)], soft)
                F.slab('Suit welt pocket', (sign * .16, front(sign * .16, 1.29, width) - .01, 1.29), (.05, .003, .008), m['trim'], 'spine', .002)
            if 'school' in details:
                F.slab('School stitched chest crest', (sign * .155, front(sign * .155, 1.48, width) - .012, 1.48),
                       (.021, .004, .025), m['trim'], 'spine', .004)
    if outfit == 'suit':
        for obj in list(F.parts):
            if obj.name.startswith('Necktie'):
                F.parts.remove(obj)
                bpy.data.objects.remove(obj, do_unlink=True)
        F.mesh('Suit inset shirt front', [(-.072, -.157, 1.65), (.072, -.157, 1.65), (.040, -.197, 1.42), (-.040, -.197, 1.42)],
               [(0, 1, 2, 3)], m['white'], 'spine', False)
        F.mesh('Flat woven tie', [(-.013, -.164, 1.62), (.013, -.164, 1.62), (.022, -.206, 1.34),
                                (0, -.207, 1.31), (-.022, -.206, 1.34)], [(0, 1, 2, 3, 4)], m['trim'], 'spine', False)
    if outfit == 'waistcoat':
        F.loft('Tailored vest lower silhouette', [(0, .016, 1.08, .26 * width, .173), (0, .012, 1.42, .304 * width, .198)], m['main'], 'spine')
        for sign in (-1, 1):
            F.leaf('Vest V collar', (sign * .18, -.125, 1.65), (0, -.207, 1.34), .038, m['main'], 'spine', .014)
    if 'zip' in details or 'leather' in details:
        line('Inset zipper', [(0, front(0, z, width) - .005, z) for z in (1.12, 1.3, 1.5, 1.61)], m['dark'], radius=.005)
        F.slab('Zipper pull tab', (0, -.2, 1.47), (.009, .005, .017), m['metal'], 'spine', .003)
        for i in range(13):
            z = 1.16 + i * .032
            line('Zipper teeth', [(-.005, front(0, z, width) - .007, z), (.005, front(0, z, width) - .007, z)], m['metal'], radius=.0015)
    if 'uniform' in details or 'workwear' in details:
        for sign, side in [(1, 'L'), (-1, 'R')]:
            F.slab('Tailored shoulder epaulette.' + side, (sign * .34, -.055, 1.68), (.056, .055, .014), m['trim'], 'upper.' + side, .007)
            F.slab('Pocket flap with stitched edge', (sign * .15, -.186, 1.49), (.062, .009, .022), m['trim'], 'spine', .004)
            F.ellipsoid('Pocket fastening button', (sign * .15, -.199, 1.49), (.006, .004, .006), m['metal'], 'spine', 10, 6)
        F.leaf('Cross body canvas belt', (-.21, -.125, 1.65), (.19, -.198, 1.12), .025, m['trim'], 'spine', .007)
    if 'apron' in details:
        F.slab('Apron sewn front pocket', (0, -.218, .94), (.12, .006, .062), m['trim'], 'hips', .006)
        for sign in (-1, 1):
            line('Apron shoulder binding', [(sign * .12, -.115, 1.68), (sign * .11, -.208, 1.58)], m['white'], radius=.009)
        line('Apron pocket lip', [(-.115, -.226, .999), (.115, -.226, .999)], soft, 'hips')
    if 'denim' in details:
        for sign in (-1, 1):
            line('Denim pocket top stitch', [(sign * .20, front(sign * .20, 1.50, width) - .01, 1.50),
                 (sign * .11, front(sign * .11, 1.49, width) - .01, 1.49)], m['trim'], radius=.002)
    if 'beads' in details:
        for i in range(23):
            a = math.tau * i / 23
            F.ellipsoid('Individual prayer bead', (.155 * math.cos(a), -.058 - .147 * math.sin(a), 1.58 - .095 * math.sin(a)),
                        (.016, .016, .016), m['wood'], 'spine', 12, 8)
    if {'embroidered', 'brocade', 'tibetan', 'mandarin', 'qipao', 'court'} & details:
        if 'mandarin' in details:
            for obj in list(F.parts):
                if obj.name.startswith('Crossed robe collar'):
                    F.parts.remove(obj)
                    bpy.data.objects.remove(obj, do_unlink=True)
        for sign in (-1, 1):
            if 'mandarin' in details:
                continue
            F.curved('Embroidered collar piping', [(sign * .14, -.125, 1.68), (sign * .117, -.184, 1.58),
                 (-sign * .048, -.207, 1.36), (-sign * .159, -.183, 1.15)], .004, m['gold'] if 'embroidered' in details else m['trim'], 'spine', 24, 6)
        for i in range(7):
            x = (i - 3) * .075 * width
            F.curved('Weighted robe pleat', [(x * .55, -.163, 1.03), (x * .77, -.211, .79),
                 (x, -.238, .47), (x * 1.1, -.239, .24)], .004, soft, 'hips', 24, 6)
        if 'mandarin' in details:
            F.loft('Mandarin standing collar', [(0, .025, 1.67, .118, .13), (0, .025, 1.76, .12, .13)], m['main'], 'spine')
            for i in range(5):
                z = 1.24 + i * .075
                line('Mandarin knotted closure', [(-.023, front(0, z, width), z), (.023, front(0, z, width), z)], m['trim'], radius=.004)
        if 'qipao' in details or 'brocade' in details:
            for x, z in [(-.14, 1.25), (.17, 1.36), (-.12, 1.52)]:
                center = Vector((x, front(x, z, width) - .008, z))
                for i in range(5):
                    a = i * math.tau / 5
                    F.leaf('Brocade petal embroidery', center, center + Vector((.025 * math.cos(a), 0, .025 * math.sin(a))),
                           .006, m['trim'], 'spine', .0015, .001)
        if 'court' in details:
            F.slab('Court embroidered chest panel', (0, -.209, 1.41), (.10, .006, .086), m['trim'], 'spine', .006)
            F.leaf('Chest panel stylized bird', (-.065, -.217, 1.38), (.065, -.217, 1.44), .022, m['gold'], 'spine', .003)
    if 'lamellar' in details:
        for row in range(3):
            for col in range(5):
                x, z = (col - 2) * .09, 1.24 + row * .09
                for sign in (-1, 1):
                    F.ellipsoid('Armor brass rivet', (x + sign * .028, -.222, z + .022), (.004, .003, .004), m['gold'], 'spine', 8, 6)
        for sign, side in [(1, 'L'), (-1, 'R')]:
            F.loft('Armored segmented bracer.' + side, [(sign * .51, -.03, 1.0, .062, .065),
                       (sign * .51, -.014, 1.15, .089, .093), (sign * .5, .005, 1.23, .085, .086)], m['main'], 'forearm.' + side)
    if 'leopard' in details:
        for row in range(5):
            for col in range(7):
                x, z = (col - 3) * .062, 1.18 + row * .09
                F.ellipsoid('Leopard fabric rosette', (x, front(x, z, width) - .004, z), (.012, .0025, .016), m['dark'], 'spine', 10, 6)
    if 'sequins' in details:
        for row in range(5):
            for col in range(7):
                x, z = (col - 3) * .057, 1.18 + row * .09
                F.slab('Stage cloth sequin', (x, front(x, z, width) - .005, z), (.005, .002, .006), m['metal'], 'spine', .001)
    if 'patches' in details:
        F.slab('Sewn cloth repair patch', (.18, front(.18, 1.22, width) - .007, 1.22), (.033, .004, .036), m['trim'], 'spine', .004)
        for z in (1.19, 1.21, 1.23, 1.25):
            line('Patch hand stitching', [(.147, -.13, z), (.151, -.13, z + .005)], soft, radius=.0015)
    if 'holster' in details:
        for sign in (-1, 1):
            F.slab('Leather belt holster', (sign * .245, -.11, 1.03), (.054, .035, .095), m['dark'], 'hips', .014)


def face_and_hair(c, m):
    p = c['faceParams']
    if c['id'] not in ('wukong', 'bajie', 'snowking'):
        shell = next(obj for obj in F.parts if obj.name.startswith('Sculpted jaw'))
        levels = []
        for z in sorted({round(v.co.z, 6) for v in shell.data.vertices}):
            row = [v.co for v in shell.data.vertices if abs(v.co.z - z) < .00001]
            levels.append((z, sum(v.y for v in row) / len(row), max(abs(v.x) for v in row), (max(v.y for v in row) - min(v.y for v in row)) / 2))
        F.parts.remove(shell)
        bpy.data.objects.remove(shell, do_unlink=True)
        # Catmull-Rom profile preserves the authored jaw while removing planar ring bands.
        profiles = []
        for i in range(49):
            z = 1.77 + .48 * i / 48
            segment = next((j for j in range(len(levels) - 1) if levels[j][0] <= z <= levels[j + 1][0]), len(levels) - 2)
            a, b = levels[segment:segment + 2]
            u = max(0, min(1, (z - a[0]) / (b[0] - a[0])))
            left, right = levels[max(0, segment - 1)], levels[min(len(levels) - 1, segment + 2)]
            values = [.5 * ((2 * a[k]) + (-left[k] + b[k]) * u + (2 * left[k] - 5 * a[k] + 4 * b[k] - right[k]) * u ** 2 +
                           (-left[k] + 3 * a[k] - 3 * b[k] + right[k]) * u ** 3) for k in (1, 2, 3)]
            profiles.append((0, values[0], z, max(.008, values[1]), max(.012, values[2])))
        face = F.loft('Sculpted jaw cheek and cranium', profiles, m['skin'], 'head', 40)
        for v in face.data.vertices:
            x, y, z = v.co
            row = profiles[v.index // 40]
            forward = max(0, (row[1] - y) / row[4]) ** 4
            nose = .048 * math.exp(-(x / (.031 * p['noseWidth'])) ** 4 - ((z - 1.975) / .025) ** 2)
            bridge = .024 * math.exp(-(x / .020) ** 2 - ((z - 2.006) / .048) ** 2)
            cheek = .010 * math.exp(-((abs(x) - .12) / .065) ** 2 - ((z - 1.968) / .045) ** 2)
            socket = .006 * math.exp(-((abs(x) - .093) / .041) ** 2 - ((z - 2.028) / .025) ** 2)
            v.co.y -= (nose + bridge + cheek - socket) * min(1, forward)
        for obj in list(F.parts):
            if obj.name.startswith(('Rounded nose', 'Nose wing', 'Nostril')):
                F.parts.remove(obj)
                bpy.data.objects.remove(obj, do_unlink=True)
    # Remove the old parallel tube fringe; sculpt tapered locks following the scalp.
    for obj in list(F.parts):
        if obj.name.startswith(('Swept hair strand', 'Glasses lens', 'Glasses bridge', 'Curled hair cluster', 'Beard shaped strand')):
            F.parts.remove(obj)
            bpy.data.objects.remove(obj, do_unlink=True)
    hair = c['hair']
    if hair in ('parted', 'slick', 'short', 'bun', 'ponytail', 'emo'):
        for sign in (-1, 1):
            for i in range(6):
                a = (sign * (.014 + i * .017), -.056 + i * .020, 2.279 - i * .003)
                b = (sign * (.16 + i * .008), -.125 + i * .023, 2.123 + i * .007)
                if hair == 'slick':
                    a, b = (sign * (.02 + i * .026), -.128, 2.15), (sign * (.03 + i * .021), .13, 2.23)
                F.leaf('Sculpted overlapping hair lock', a, b, .027 if hair != 'short' else .021, m['hair'], 'head', .010, .022)
                F.curved('Fine hair comb groove', [a, (sign * (.12 + i * .011), -.17 + i * .020, 2.27),
                     (sign * (.20 - i * .005), -.15 + i * .024, 2.19), b], .0017, m['dark'], 'head', 20, 5)
        if hair == 'emo':
            for i in range(6):
                F.leaf('Long diagonal fringe', (-.10 + i * .032, -.12, 2.275), (.05 + i * .018, -.196, 2.016 + i * .012),
                       .035, m['hair'], 'head', .011, .029)
    if hair in ('long', 'wavy', 'curly'):
        for i in range(48):
            a = i * math.pi * (3 - math.sqrt(5))
            h = (i + .5) / 48
            r = .205 * math.sqrt(1 - h * h)
            F.ellipsoid('Fitted curly hair coil', (r * math.cos(a), .053 + r * .85 * math.sin(a), 2.145 + .15 * h),
                        (.025, .024, .028), m['hair'], 'head', 16, 10)
        for sign in (-1, 1):
            for i in range(4):
                z_end = 1.71 if hair == 'long' else 1.86 if hair == 'wavy' else 2.08
                F.curved('Separated flowing hair lock', [(sign * (.18 + i * .009), .04 + i * .017, 2.19),
                     (sign * (.25 + i * .008), .05 + i * .017, 2.09),
                     (sign * (.235 + i * .009), .08 + i * .021, z_end + .08),
                     (sign * (.20 + i * .013), .085 + i * .018, z_end)], .021, m['hair'], 'head', 24, 8)
    beard = c.get('beard', 'none')
    if beard not in ('none', 'moustache', None, False):
        long = beard in ('long', 'white', 'longwhite', 'forked')
        for i in range(19):
            x = (i - 9) * .010
            end = 1.55 + abs(i - 9) * .010 if long else 1.77 + abs(i - 9) * .003
            F.curved('Fine layered beard lock', [(x, -.175, 1.853), (x * 1.09, -.205, 1.81),
                 (x * .92, -.207, end + .07), (x * .78, -.19, end)], .0078, m['hair'], 'head', 24, 6)
    if c.get('accessory') in ('glasses', 'sunglasses'):
        glass = F.material(c['id'] + ' · transparent spectacle glass', (.72, .81, .83), roughness=.10)
        if c['accessory'] == 'glasses':
            glass.node_tree.nodes.get('Principled BSDF').inputs['Alpha'].default_value = .16
            glass.surface_render_method = 'DITHERED'
        for sign in (-1, 1):
            x = sign * .093
            points = [(x + .051 * math.cos(i * math.tau / 32), -.205, 2.026 + .031 * math.sin(i * math.tau / 32)) for i in range(33)]
            line('Spectacle fitted rim', points, m['dark'], 'head', .0035)
            F.ellipsoid('Clear lens' if c['accessory'] == 'glasses' else 'Tinted lens', (x, -.203, 2.026),
                        (.047, .002, .027), glass if c['accessory'] == 'glasses' else m['dark'], 'head', 24, 10)
            line('Spectacle temple arm', [(sign * .143, -.203, 2.036), (sign * .211, -.055, 2.034),
                 (sign * .223, .025, 2.028)], m['dark'], 'head', .003)
        line('Spectacle curved bridge', [(-.041, -.207, 2.031), (0, -.225, 2.043), (.041, -.207, 2.031)], m['dark'], 'head', .0035)
    for obj in F.parts:
        if not any(g.name == 'head' for g in obj.vertex_groups):
            continue
        for v in obj.data.vertices:
            v.co.x *= p['width']
            v.co.z = 2.026 + (v.co.z - 2.026) * p['height']
            if obj.name.startswith('Sculpted jaw') and v.co.z < 1.95:
                v.co.x *= 1 + (p['jaw'] - 1) * min(1, (1.95 - v.co.z) / .13)
            if obj.name.startswith(('Rounded nose', 'Nose wing', 'Nostril')):
                v.co.x *= p['noseWidth']
                v.co.y -= (p['noseWidth'] - 1) * .014
            if obj.name.startswith(('Almond eye', 'Dark iris', 'Eye catchlight', 'Upper eyelid', 'Lower eyelid')):
                v.co.z = 2.026 + (v.co.z - 2.026) * p['eyeHeight']
            if obj.name.startswith(('Upper lip', 'Lower lip')):
                v.co.x *= p['mouthWidth']
                v.co.y -= .026
            if obj.name.startswith('Expressive eyebrow'):
                if c['temperament'] == 'stern':
                    v.co.z -= .008 * max(0, 1 - abs(v.co.x) / .17)
                if c['temperament'] == 'buoyant':
                    v.co.z += .006 * math.sin(abs(v.co.x) * 20)
    # Inner ear anatomy and lid creases use fine closed quad tubes.
    if c['id'] not in ('wukong', 'bajie', 'snowking'):
        for sign in (-1, 1):
            line('Ear antihelix fold', [(sign * .228 * p['width'], -.017, 2.035),
                 (sign * .241 * p['width'], -.024, 2.011), (sign * .228 * p['width'], -.025, 1.981)], m['skin'], 'head', .004)
    if c.get('age') == 'old' and c['id'] not in ('snowking', 'bajie'):
        # Wrinkles are low-contrast surface ribbons, not deep black facial cuts.
        wrinkle = F.material(c['id'] + ' · soft skin crease', tuple(v * .84 for v in m['skin'].diffuse_color[:3]), roughness=.86)
        for sign in (-1, 1):
            F.curved('Outer eye expression crease', [(sign * .138 * p['width'], -.128, 2.029),
                 (sign * .151 * p['width'], -.116, 2.020), (sign * .159 * p['width'], -.105, 2.015),
                 (sign * .166 * p['width'], -.095, 2.012)], .001, wrinkle, 'head', 14, 4)


def prop_details(c, m):
    grip = Vector((-.51, -.14, .93))
    kind = c['weaponType']
    if kind in ('knife', 'cleaver', 'sword', 'staff', 'polearm', 'halberd', 'rake', 'wrench'):
        for i in range(7):
            z = grip.z - .04 + i * .018
            points = [(grip.x + .025 * math.cos(j * math.tau / 20), grip.y + .025 * math.sin(j * math.tau / 20), z) for j in range(21)]
            line('Weapon bound grip winding', points, m['dark'], 'hand.R', .0025)
    if kind in ('mic', 'microphone'):
        for i in range(7):
            a = i * math.pi / 6
            points = [(grip.x + .049 * math.cos(t) * math.cos(a), grip.y + .049 * math.cos(t) * math.sin(a),
                       grip.z + .45 + .066 * math.sin(t)) for t in [-math.pi / 2 + j * math.pi / 16 for j in range(17)]]
            line('Microphone woven metal grille', points, m['dark'], 'hand.R', .0015)
        F.slab('Microphone recessed power switch', grip + Vector((0, -.024, .22)), (.009, .003, .019), m['dark'], 'hand.R', .003)
    if kind == 'bag':
        center = grip + Vector((0, -.025, .10))
        line('Bag stitched top seam', [center + Vector((-.10, -.034, .092)), center + Vector((.10, -.034, .092))], m['trim'], 'hand.R')
        if 'fertilizer' in c['details']:
            F.slab('Fertilizer bag inset label', center + Vector((0, -.035, 0)), (.087, .003, .065), m['white'], 'hand.R', .004)
            for sign in (-1, 1):
                F.leaf('Bag label crop leaf', center + Vector((0, -.04, -.04)), center + Vector((sign * .045, -.04, .035)),
                       .018, F.jade, 'hand.R', .002, .002)
    if kind in ('book', 'document'):
        center = grip + Vector((0, -.025, .10))
        for i in range(8):
            line('Book bound page layers', [center + Vector((-.093, -.038, -.125 + i * .031)),
                 center + Vector((.093, -.038, -.125 + i * .031))], m['trim'], 'hand.R', .0012)


def join_parts(name, objects):
    assert objects, name
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    result = bpy.context.object
    result.name = name
    result.data.name = name
    result.select_set(False)
    return result


def assemble(identifier, gear, facial_controls=True):
    groups = {name: [] for name in ('face', 'skin', 'cloth', 'hair', 'armor', 'props')}
    gear = set(gear)
    for obj in F.parts:
        if obj in gear:
            group = 'props'
        elif any(g.name.startswith('expression.') for g in obj.vertex_groups) or (any(g.name == 'head' for g in obj.vertex_groups) and not any(word in obj.name.lower() for word in ('hair', 'beard', 'moustache', 'cap', 'hat', 'crown', 'spectacle', 'lens', 'headphone', 'headband', 'circlet'))):
            group = 'face'
        elif any(word in obj.name.lower() for word in ('breastplate', 'pauldron', 'armor ', 'armored')):
            group = 'armor'
        elif any(g.name == 'head' for g in obj.vertex_groups):
            group = 'hair'
        elif obj.data.materials[0] == F.skin:
            group = 'skin'
        else:
            group = 'cloth'
        groups[group].append(obj)
    meshes = [join_parts(identifier + '_' + name, objects) for name, objects in groups.items() if objects]
    face = next(mesh for mesh in meshes if mesh.name.endswith('_face'))
    if not facial_controls:
        return meshes
    F.face_controls(face)
    # Subtle cheek lifting and jaw tension accompany the independent feature controls.
    for vertex in face.data.vertices:
        if any(face.vertex_groups[g.group].name.startswith('expression.') for g in vertex.groups):
            continue
        x, y, z = vertex.co
        if y >= -.095 or not 1.84 < z < 2.0:
            continue
        cheek = math.exp(-((abs(x) - .13) / .055) ** 2 - ((z - 1.962) / .045) ** 2)
        face.data.shape_keys.key_blocks['smile'].data[vertex.index].co.z += .008 * cheek
        face.data.shape_keys.key_blocks['angry'].data[vertex.index].co.y -= .003 * cheek
    return meshes


def skin_weights(mesh):
    if not mesh.name.endswith(('_cloth', '_skin')):
        return
    names = {g.index: g.name for g in mesh.vertex_groups}
    for vertex in mesh.data.vertices:
        bone = next((names[g.group] for g in vertex.groups if not names[g.group].startswith('expression.')), None)
        if not bone:
            continue
        z = vertex.co.z
        neighbour, weight = None, 0
        if bone.startswith('upper.'):
            if z > 1.56:
                neighbour, weight = 'spine', min(.72, max(0, (z - 1.56) / .16))
            elif z < 1.34:
                neighbour, weight = 'forearm.' + bone[-1], min(1, max(0, (1.34 - z) / .12))
        elif bone.startswith('forearm.') and z > 1.245:
            neighbour, weight = 'upper.' + bone[-1], min(.65, max(0, (z - 1.245) / .13))
        elif bone.startswith('thigh.') and z < .59:
            neighbour, weight = 'shin.' + bone[-1], min(.45, max(0, (.59 - z) / .12))
        elif bone.startswith('shin.') and z > .485:
            neighbour, weight = 'thigh.' + bone[-1], min(.65, max(0, (z - .485) / .13))
        if neighbour and weight > 0:
            mesh.vertex_groups[bone].add([vertex.index], 1 - weight, 'REPLACE')
            group = mesh.vertex_groups.get(neighbour) or mesh.vertex_groups.new(name=neighbour)
            group.add([vertex.index], weight, 'REPLACE')
