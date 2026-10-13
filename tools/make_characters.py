"""Run with Blender 5.1: blender --background --factory-startup --python tools/make_characters.py.

Original low-poly figures, a shared 16-bone rig, and seven editable animation clips.
No downloaded meshes, textures, likeness scans, movie audio, or motion-capture data.
"""
import bpy
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public' / 'assets'
SOURCE = ROOT / 'art'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.scene.render.fps = 30
materials = {}


def material(name, color, metallic=0):
    if name in materials:
        return materials[name]
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = 0.42
    materials[name] = mat
    return mat


skin = material('Warm skin', (0.77, 0.47, 0.30))
black = material('Ink', (0.027, 0.025, 0.04))
white = material('Ivory', (0.91, 0.85, 0.73))
silver = material('Silver hair', (0.49, 0.51, 0.60), 0.2)
purple = material('IKUN purple', (0.43, 0.31, 0.86))
orange = material('Basketball orange', (0.83, 0.25, 0.04))
teal = material('Jade robe', (0.04, 0.36, 0.29))
gold = material('Antique gold', (0.72, 0.44, 0.10), 0.65)
red = material('Crimson armor', (0.58, 0.045, 0.065), 0.35)
steel = material('Steel', (0.42, 0.48, 0.54), 0.75)


def part(name, center, scale, mat, bone, shape='sphere'):
    if shape == 'box':
        bpy.ops.mesh.primitive_cube_add(size=2, location=center)
    elif shape == 'cone':
        bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=1, radius2=0.2, depth=2, location=center)
    elif shape == 'cylinder':
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=1, depth=2, location=center)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.data.materials.append(mat)
    obj.vertex_groups.new(name=bone).add(range(len(obj.data.vertices)), 1.0, 'REPLACE')
    if shape == 'box':
        bevel = obj.modifiers.new('Soft corners', 'BEVEL')
        bevel.width = 0.055
        bevel.segments = 2
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    for polygon in obj.data.polygons:
        polygon.use_smooth = shape == 'sphere'
    parts.append(obj)
    return obj


def rod(name, a, b, radius, mat, bone):
    a, b = Vector(a), Vector(b)
    obj = part(name, (a + b) / 2, (radius, radius, (b - a).length / 2), mat, bone, 'cylinder')
    # Vertices are already in world space; rotate around the segment midpoint.
    midpoint = (a + b) / 2
    q = (b - a).to_track_quat('Z', 'Y')
    for vertex in obj.data.vertices:
        vertex.co = midpoint + q @ (vertex.co - midpoint)
    return obj


def rig(character):
    data = bpy.data.armatures.new(character + '_skeleton')
    obj = bpy.data.objects.new(character + '_rig', data)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    specs = {
        'root': ((0, 0, 0), (0, 0, .35), None),
        'hips': ((0, 0, .94), (0, 0, 1.12), 'root'),
        'spine': ((0, 0, 1.12), (0, 0, 1.67), 'hips'),
        'head': ((0, 0, 1.67), (0, 0, 2.15), 'spine'),
    }
    for side, sign in [('L', 1), ('R', -1)]:
        specs.update({
            'upper.' + side: ((sign * .38, 0, 1.6), (sign * .53, 0, 1.24), 'spine'),
            'forearm.' + side: ((sign * .53, 0, 1.24), (sign * .52, -.04, .93), 'upper.' + side),
            'hand.' + side: ((sign * .52, -.04, .93), (sign * .52, -.04, .79), 'forearm.' + side),
            'thigh.' + side: ((sign * .18, 0, .99), (sign * .19, 0, .52), 'hips'),
            'shin.' + side: ((sign * .19, 0, .52), (sign * .19, 0, .12), 'thigh.' + side),
            'foot.' + side: ((sign * .19, 0, .12), (sign * .19, -.2, .06), 'shin.' + side),
        })
    for name, (head, tail, parent) in specs.items():
        bone = data.edit_bones.new(name)
        bone.head, bone.tail = head, tail
        if parent:
            bone.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
    for bone in obj.pose.bones:
        bone.rotation_mode = 'XYZ'
    return obj


def base(character):
    shirt = {'ikun': black, 'wang': teal, 'lubu': red}[character]
    part('Torso', (0, 0, 1.40), (.37, .22, .32), shirt, 'spine', 'box')
    part('Belt', (0, 0, 1.06), (.30, .24, .07), gold if character != 'ikun' else black, 'hips', 'box')
    part('Head', (0, -.02, 1.94), (.31, .255, .33), skin, 'head')
    part('Nose', (0, -.279, 1.94), (.045, .062, .060), skin, 'head')
    for sign, side in [(1, 'L'), (-1, 'R')]:
        part('Ear.' + side, (sign * .30, -.01, 1.94), (.045, .075, .095), skin, 'head')
        part('Eye.' + side, (sign * .11, -.259, 1.99), (.055, .024, .04), white, 'head')
        part('Pupil.' + side, (sign * .11, -.279, 1.99), (.021, .012, .025), black, 'head')
        part('Brow.' + side, (sign * .11, -.262, 2.07), (.072, .023, .018), black, 'head', 'box')
        rod('Upper arm.' + side, (sign * .38, 0, 1.60), (sign * .53, 0, 1.24), .12, shirt, 'upper.' + side)
        rod('Sleeve.' + side, (sign * .53, 0, 1.24), (sign * .52, -.04, .97), .095 if character == 'ikun' else .15, skin if character == 'ikun' else shirt, 'forearm.' + side)
        part('Hand.' + side, (sign * .52, -.04, .87), (.10, .085, .115), skin, 'hand.' + side)
        rod('Thigh.' + side, (sign * .18, 0, .98), (sign * .19, 0, .52), .14, black if character == 'ikun' else shirt, 'thigh.' + side)
        rod('Shin.' + side, (sign * .19, 0, .52), (sign * .19, 0, .14), .11, black, 'shin.' + side)
        part('Boot.' + side, (sign * .19, -.1, .11), (.14, .22, .105), white if character == 'ikun' else black, 'foot.' + side, 'box')
    part('Smile', (0, -.260, 1.80), (.09, .02, .012), black, 'head', 'box')
    if character == 'ikun':
        for sign in [-1, 1]:
            part('Suspenders', (sign * .19, -.24, 1.40), (.035, .014, .29), white, 'spine', 'box')
            part('Parted hair', (sign * .15, -.045, 2.20), (.20, .255, .15), silver, 'head')
        part('Hair back', (0, .10, 2.05), (.30, .16, .22), silver, 'head')
        part('Basketball', (-.54, -.12, .89), (.22, .22, .22), orange, 'hand.R')
        for z in [.79, .99]:
            rod('Ball seam', (-.73, -.255, z), (-.36, -.255, z), .012, black, 'hand.R')
    elif character == 'wang':
        part('Long robe', (0, 0, .98), (.42, .28, .38), teal, 'hips', 'cone')
        part('White beard', (0, -.25, 1.65), (.14, .065, .22), white, 'head', 'cone')
        for sign in [-1, 1]:
            part('Moustache', (sign * .09, -.285, 1.82), (.12, .023, .036), white, 'head')
        part('Court hat', (0, .015, 2.24), (.28, .23, .15), black, 'head', 'box')
        part('Hat jewel', (0, -.224, 2.27), (.07, .025, .055), gold, 'head')
        rod('Hat wing', (-.57, .04, 2.27), (.57, .04, 2.27), .035, black, 'head')
        rod('Fan handle', (-.52, -.06, .78), (-.52, -.07, 1.16), .025, gold, 'hand.R')
        for i in range(7):
            angle = (i - 3) * .17
            rod('Fan feather', (-.52, -.07, 1.03), (-.52 + math.sin(angle) * .34, -.08, 1.03 + math.cos(angle) * .34), .055, white, 'hand.R')
    else:
        part('Chest gold', (0, -.225, 1.42), (.24, .025, .19), gold, 'spine', 'box')
        for sign, side in [(1, 'L'), (-1, 'R')]:
            part('Shoulder armor', (sign * .39, 0, 1.60), (.18, .22, .10), gold, 'upper.' + side, 'box')
            part('Gauntlet', (sign * .52, -.035, 1.10), (.115, .12, .15), gold, 'forearm.' + side, 'box')
        part('Helmet', (0, .015, 2.17), (.33, .27, .15), red, 'head')
        part('Helmet band', (0, -.255, 2.14), (.32, .025, .042), gold, 'head', 'box')
        for sign in [-1, 1]:
            previous = Vector((sign * .19, .05, 2.25))
            for i in range(1, 9):
                t = i / 8
                point = Vector((sign * (.19 + .30 * t), .05 + .17 * t * t, 2.25 + .65 * math.sin(t * 1.8)))
                rod('Pheasant plume', previous, point, .026 * (1 - t * .6), red, 'head')
                previous = point
        rod('Halberd shaft', (-.57, -.03, .22), (-.57, -.03, 2.19), .025, black, 'hand.R')
        part('Halberd spear', (-.57, -.03, 2.32), (.075, .032, .20), steel, 'hand.R', 'cone')
        part('Halberd crescent', (-.69, -.03, 2.04), (.13, .042, .22), steel, 'hand.R')
        part('Halberd collar', (-.57, -.03, 2.05), (.055, .055, .10), gold, 'hand.R', 'cylinder')


def animate(armature, character):
    durations = {'idle': 60, 'attack': 42, 'heavy': 42, 'guard': 42, 'special': 42, 'hurt': 24, 'victory': 60}
    armature.animation_data_create()
    for name, frames in durations.items():
        action = bpy.data.actions.new(name)
        armature.animation_data.action = action
        for frame in range(1, frames + 1, 3):
            t = (frame - 1) / (frames - 1)
            wave = math.sin(t * 2 * math.pi)
            hit = math.exp(-((t - .42) / .13) ** 2)
            prepare = math.exp(-((t - .19) / .12) ** 2)
            for bone in armature.pose.bones:
                bone.rotation_euler = (0, 0, 0)
                bone.location = (0, 0, 0)
            p = armature.pose.bones
            p['spine'].rotation_euler.x = .025 * wave
            p['root'].location.z = .012 * (1 - math.cos(t * 2 * math.pi))
            p['upper.L'].rotation_euler.x = -.16
            p['upper.R'].rotation_euler.x = -.16
            p['forearm.L'].rotation_euler.x = -.10
            p['forearm.R'].rotation_euler.x = -.10
            if name in ('attack', 'heavy', 'special'):
                power = 1.25 if name != 'attack' else 1
                p['upper.R'].rotation_euler.x = -.16 + .45 * prepare - 1.5 * hit * power
                p['forearm.R'].rotation_euler.x = -.10 - .8 * prepare + .12 * hit
                p['spine'].rotation_euler.x = -.08 * prepare + .30 * hit
                p['spine'].rotation_euler.y = -.18 * prepare + .25 * hit
                p['upper.L'].rotation_euler.x = -.25 - .42 * hit
                p['root'].location.y = -.25 * hit
                if name == 'special' and character == 'ikun':
                    p['root'].location.z += .28 * math.sin(t * math.pi) ** 2
                    p['upper.L'].rotation_euler.x = -1.8 * hit
                    p['upper.R'].rotation_euler.x = -2.5 * prepare - 1.2 * hit
                if name == 'special' and character == 'wang':
                    p['head'].rotation_euler.z = .16 * math.sin(t * math.pi * 4)
                    p['upper.L'].rotation_euler.x = -1.4 * hit
                if name == 'special' and character == 'lubu':
                    p['spine'].rotation_euler.z = -.7 * prepare + .8 * hit
                    p['upper.R'].rotation_euler.z = .5 * hit
            elif name == 'guard':
                envelope = math.sin(t * math.pi) ** .5
                for side in ['L', 'R']:
                    p['upper.' + side].rotation_euler.x = -1.0 * envelope
                    p['forearm.' + side].rotation_euler.x = -1.1 * envelope
                p['spine'].rotation_euler.x = -.10 * envelope
            elif name == 'hurt':
                p['spine'].rotation_euler.x = -.28 * hit
                p['head'].rotation_euler.x = -.16 * hit
                p['root'].location.y = .16 * hit
            elif name == 'victory':
                p['upper.L'].rotation_euler.x = -2.5 + .2 * wave
                p['upper.R'].rotation_euler.x = -2.5 - .2 * wave
                p['spine'].rotation_euler.z = .09 * wave
                p['root'].location.z = .04 * (1 - math.cos(t * 4 * math.pi))
            for bone in p:
                bone.keyframe_insert('rotation_euler', frame=frame, group=bone.name)
                bone.keyframe_insert('location', frame=frame, group=bone.name)
        track = armature.animation_data.nla_tracks.new()
        track.name = name
        strip = track.strips.new(name, 1, action)
        strip.action_frame_start, strip.action_frame_end = 1, frames
        track.mute = True
    armature.animation_data.action = None


for character in ['ikun', 'wang', 'lubu']:
    parts = []
    base(character)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    mesh = bpy.context.object
    mesh.name = character + '_body'
    mesh.select_set(False)
    armature = rig(character)
    modifier = mesh.modifiers.new('Skeleton', 'ARMATURE')
    modifier.object = armature
    mesh.parent = armature
    animate(armature, character)
    bpy.context.scene.frame_set(1)
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(filepath=str(OUT / (character + '.glb')), export_format='GLB', use_selection=True,
                              export_animations=True, export_animation_mode='NLA_TRACKS', export_skins=True,
                              export_force_sampling=True, export_nla_strips=True)
    armature.location.x = {'ikun': -2.4, 'wang': 0, 'lubu': 2.4}[character]

bpy.ops.object.select_all(action='DESELECT')
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 60
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE / 'all-stars.blend'))
print('Created 3 editable characters, 16 bones each, 7 animation clips each.')
