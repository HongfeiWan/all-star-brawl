"""Rebuild the three v0.3 photo-face experiments from local, unmodified photos.

blender --background --factory-startup --python tools/apply_photo_faces.py -- --config work/photo-faces.json
Add --write-assets only after reviewing the preview models. No network requests.

Config is an object keyed by ikun/huaqiang/guatan. Each entry has image, face
[left, top, width, height], eyes [[x,y],[x,y]], nose [x,y], and mouth corners
[[x,y],[x,y]]. Coordinates use the original image's top-left pixel origin.
"""
import argparse
import json
import math
import struct
import sys
from pathlib import Path

import bpy

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_characters as F

ORIGINAL_MATERIALS = {name: getattr(F, name) for name in ('skin', 'aged', 'beard')}
import make_roster as R

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / 'work' / 'photo-model-preview'
IDENTIFIERS = ('ikun', 'huaqiang', 'guatan')
EXPRESSIONS = ('blink', 'angry', 'smile', 'hurt')
REMOVE_FACE = ('Integrated eye socket', 'Almond eye', 'Dark iris', 'Eye catchlight',
               'Upper eyelid', 'Lower eyelid', 'Expressive eyebrow', 'Rounded nose',
               'Nose wing', 'Nostril', 'Upper lip', 'Lower lip', 'Forehead fine crease',
               'Nasolabial fine crease', 'Under eye fine crease')


def gaussian(x, z, center, width, height):
    return math.exp(-((x - center[0]) / width) ** 2 - ((z - center[1]) / height) ** 2)


def interpolate(points, value):
    points = sorted(points)
    if value <= points[0][0]:
        return points[0][1]
    for a, b in zip(points, points[1:]):
        if value <= b[0]:
            t = (value - a[0]) / (b[0] - a[0])
            return a[1] + (b[1] - a[1]) * t
    return points[-1][1]


def expression_delta(point, landmarks, name):
    """Move the photographed features themselves; UVs remain fixed to Basis."""
    x, y, z = point
    dx = dy = dz = 0.0
    eye_width, eye_height = landmarks['eyeWidth'], landmarks['eyeHeight']
    for eye in landmarks['eyes']:
        # A broad plateau collapses the whole eye rather than only its pupil.
        eye_weight = math.exp(-((x - eye[0]) / eye_width) ** 4 - ((z - eye[1]) / eye_height) ** 4)
        close = {'blink': .985, 'angry': .20, 'smile': 0, 'hurt': .65}[name]
        dz += (eye[1] - z) * close * eye_weight
        if name in ('angry', 'hurt'):
            brow = (eye[0], eye[1] + eye_height * 2.6)
            weight = gaussian(x, z, brow, eye_width * 1.2, eye_height * .95)
            inner = max(0, min(1, 1 - abs(x) / max(abs(eye[0]) * 1.5, .04)))
            dz += (-.012 * (1 + inner) if name == 'angry' else .014 * (1 + inner)) * weight
    mouth = landmarks['mouth']
    mouth_width = max(.025, abs(mouth[1][0] - mouth[0][0]) * .53)
    center = ((mouth[0][0] + mouth[1][0]) / 2, (mouth[0][1] + mouth[1][1]) / 2)
    weight = gaussian(x, z, center, mouth_width * 1.2, .020)
    corner = min(1.2, abs(x - center[0]) / mouth_width)
    if name == 'smile':
        dz += .025 * corner ** 1.4 * weight
        dx += (x - center[0]) * .12 * weight
        dy -= .004 * weight
    elif name == 'angry':
        dz -= .006 * corner * weight
        dx -= (x - center[0]) * .05 * weight
    elif name == 'hurt':
        dz -= .012 * (1 - .4 * corner) * weight
        dx += (x - center[0]) * .035 * weight
    return dx, dy, dz


def validate_reference(spec, image):
    width, height = image.size
    assert width > 0 and height > 0, 'Photo could not be decoded'
    face = spec['face']
    assert len(face) == 4 and all(math.isfinite(float(v)) for v in face)
    left, top, w, h = face
    assert w > 0 and h > 0 and 0 <= left < left + w <= width and 0 <= top < top + h <= height, 'Face box is outside the original image'
    points = [*spec['eyes'], spec['nose'], *spec['mouth']]
    assert len(spec['eyes']) == len(spec['mouth']) == 2
    for point in points:
        assert len(point) == 2 and all(math.isfinite(float(v)) for v in point)
        assert left <= point[0] <= left + w and top <= point[1] <= top + h, 'Landmark is outside the face box'
    assert abs(spec['eyes'][0][0] - spec['eyes'][1][0]) > w * .1, 'Eye landmarks must be distinct'


def photo_material(identifier, image):
    material = F.material('Photo face · ' + identifier, (1, 1, 1), roughness=.86)
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Specular IOR Level'].default_value = .12
    texture = material.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = image
    vertex_color = material.node_tree.nodes.new('ShaderNodeVertexColor')
    vertex_color.layer_name = 'PhotoEdge'
    mix = material.node_tree.nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1
    material.node_tree.links.new(vertex_color.outputs['Color'], mix.inputs[1])
    material.node_tree.links.new(texture.outputs['Color'], mix.inputs[2])
    material.node_tree.links.new(mix.outputs['Color'], shader.inputs['Base Color'])
    material.node_tree.links.new(vertex_color.outputs['Alpha'], shader.inputs['Alpha'])
    material.surface_render_method = 'DITHERED'
    material.use_backface_culling = True
    image.pack()
    return material


def head_profile(shell):
    rows = {}
    for vertex in shell.data.vertices:
        p = vertex.co
        rows.setdefault(round(p.z, 6), []).append(p.copy())
    output = []
    for z, points in sorted(rows.items()):
        output.append((z, sum(p.y for p in points) / len(points),
                       max(abs(p.x) for p in points), (max(p.y for p in points) - min(p.y for p in points)) / 2))
    assert len(output) >= 5, 'Cannot locate the original volumetric head'
    return output


def profile_at(rows, z):
    for lower, upper in zip(rows, rows[1:]):
        if lower[0] <= z <= upper[0]:
            t = (z - lower[0]) / (upper[0] - lower[0])
            return tuple(lower[i] + (upper[i] - lower[i]) * t for i in range(1, 4))
    raise ValueError('Photo face outside the original head')


def add_photo_face(identifier, spec, image):
    shell = next(obj for obj in F.parts if obj.name.startswith('Sculpted jaw cheek and cranium'))
    rows = head_profile(shell)
    bottom, top = max(rows[0][0] + .018, 1.79), min(rows[-1][0] - .023, 2.205)
    half_width = max(row[2] for row in rows)
    left, photo_top, pixel_width, pixel_height = spec['face']
    image_width, image_height = image.size

    # Normalize photographed landmarks onto the authored face. This also corrects
    # the off-center eyes of a three-quarter photograph instead of stretching it.
    landmarks = {'eyes': [(-.093, 2.026), (.093, 2.026)],
                 'mouth': [(-.050, 1.898), (.050, 1.898)],
                 'eyeWidth': .042, 'eyeHeight': .020}
    nose, mouth = (0, 1.970), (0, 1.898)
    middle = left + pixel_width / 2
    eye_y = sum(p[1] for p in spec['eyes']) / 2
    mouth_y = sum(p[1] for p in spec['mouth']) / 2
    def edges(height, name):
        extent = profile_at(rows, height)[1] * .994
        pixels = spec.get('outline', {}).get(name, (left, left + pixel_width))
        return [(-extent, pixels[0]), (extent, pixels[1])]
    image_rows = [
        (bottom, edges(bottom, 'chin'), photo_top + pixel_height),
        (1.898, [*edges(1.898, 'mouth'), (-.050, spec['mouth'][0][0]), (0, sum(p[0] for p in spec['mouth']) / 2), (.050, spec['mouth'][1][0])], mouth_y),
        (1.970, [*edges(1.970, 'nose'), (0, spec['nose'][0])], spec['nose'][1]),
        (2.026, [*edges(2.026, 'eyes'), (-.093, spec['eyes'][0][0]), (0, sum(p[0] for p in spec['eyes']) / 2), (.093, spec['eyes'][1][0])], eye_y),
        (top, edges(top, 'forehead'), photo_top),
    ]

    def photograph_pixel(x, z):
        horizontal = [(height, interpolate(points, x)) for height, points, _ in image_rows]
        return interpolate(horizontal, z), interpolate([(height, y) for height, _, y in image_rows], z)
    for obj in list(F.parts):
        if obj.name.startswith(REMOVE_FACE):
            F.parts.remove(obj)
            bpy.data.objects.remove(obj, do_unlink=True)

    vertices, uv_coordinates, opacity, faces = [], [], [], []
    columns, count = 72, 84
    for row in range(count + 1):
        z = bottom + (top - bottom) * row / count
        center_y, rx, ry = profile_at(rows, z)
        for column in range(columns + 1):
            angle = (column / columns - .5) * math.pi
            x = rx * .994 * math.sin(angle)
            y = center_y - ry * math.sqrt(max(.001, 1 - (x / rx) ** 2)) - .025
            y -= .024 * gaussian(x, z, nose, .026, .025)
            y -= .010 * gaussian(x, z, (nose[0], nose[1] + .041), .020, .045)
            y -= .004 * gaussian(x, z, mouth, .064, .026)
            vertices.append((x, y, z))
            px, py = photograph_pixel(x, z)
            u, v = px / image_width, 1 - py / image_height
            uv_coordinates.append((u, v))
            edge = min(column / columns, 1 - column / columns, row / count, 1 - row / count)
            fade = min(1, edge / .085)
            opacity.append(fade * fade * (3 - 2 * fade))
            if row < count and column < columns:
                a = row * (columns + 1) + column
                faces.append((a, a + 1, a + columns + 2, a + columns + 1))
    obj = F.mesh('Curved photo face · ' + identifier, vertices, faces, photo_material(identifier, image), 'head')
    obj.vertex_groups.new(name='expression.photo').add(range(len(vertices)), 1, 'REPLACE')
    uv = obj.data.uv_layers.new(name='UVMap')
    colors = obj.data.color_attributes.new(name='PhotoEdge', type='FLOAT_COLOR', domain='CORNER')
    for loop in obj.data.loops:
        uv.data[loop.index].uv = uv_coordinates[loop.vertex_index]
        colors.data[loop.index].color = (1, 1, 1, opacity[loop.vertex_index])
    obj['photoFace'] = identifier
    return landmarks


def add_expressions(body, landmarks):
    basis = body.shape_key_add(name='Basis', from_mix=False)
    group = body.vertex_groups['expression.photo'].index
    photo_vertices = [vertex.index for vertex in body.data.vertices if any(g.group == group for g in vertex.groups)]
    assert photo_vertices, 'Photo face disappeared when joining the body'
    samples = []
    for name in EXPRESSIONS:
        key = body.shape_key_add(name=name, from_mix=False)
        key.relative_key = basis
        deltas = []
        for vertex in body.data.vertices:
            key.data[vertex.index].co = basis.data[vertex.index].co
        for index in photo_vertices:
            p = basis.data[index].co
            delta = expression_delta(p, landmarks, name)
            key.data[index].co = (p.x + delta[0], p.y + delta[1], p.z + delta[2])
            deltas.append(delta)
        assert any(max(abs(v) for v in delta) > .0001 for delta in deltas), name + ' is empty'
        samples.append(deltas)
    for i in range(len(samples)):
        for j in range(i):
            assert any(max(abs(a - b) for a, b in zip(first, second)) > .0001 for first, second in zip(samples[i], samples[j])), 'Photo expressions are identical'


def build(identifier, spec, output_dir, roster):
    R.clean_scene()
    image_path = Path(spec['image']).expanduser()
    if not image_path.is_absolute():
        image_path = ROOT / image_path
    assert image_path.is_file() and image_path.suffix.lower() in ('.png', '.jpg', '.jpeg'), 'A local PNG/JPEG photo is required'
    image = bpy.data.images.load(str(image_path), check_existing=False)
    image.colorspace_settings.name = 'sRGB'
    validate_reference(spec, image)
    if identifier == 'ikun':
        for name, function in R.ORIGINAL_FUNCTIONS.items():
            setattr(F, name, function)
        for name, material in ORIGINAL_MATERIALS.items():
            setattr(F, name, material)
        F.base(identifier)
        gear = [obj for obj in F.parts if obj.name.startswith('Basketball')]
        F.loft, F.ellipsoid, F.tube, F.curved = R.low_loft, R.low_ellipsoid, R.low_tube, R.low_curved
    else:
        config = R.configuration(roster[identifier])
        mats = R.palette(identifier, config)
        R.body(config, mats, R.seed_for(identifier))
        R.head(config, mats, R.seed_for(identifier))
        before_weapon = set(F.parts)
        R.weapon(config, mats)
        R.D.prop_details(config, mats)
        gear = [obj for obj in F.parts if obj not in before_weapon]
    landmarks = add_photo_face(identifier, spec, image)
    meshes = R.D.assemble(identifier, gear, facial_controls=False)
    body = next(mesh for mesh in meshes if mesh.name.endswith('_face'))
    add_expressions(body, landmarks)
    body['photoFaceVersion'] = 'v0.4-experiment'
    armature = F.rig(identifier)
    for mesh in meshes:
        R.D.skin_weights(mesh)
        mesh.modifiers.new('Skeleton', 'ARMATURE').object = armature
        mesh.parent = armature
    if identifier == 'ikun':
        F.animate(armature, identifier)
    bpy.context.scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    for mesh in meshes:
        mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    path = output_dir / (identifier + '.glb')
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                              export_animations=identifier == 'ikun', export_animation_mode='NLA_TRACKS',
                              export_force_sampling=True, export_nla_strips=True, export_skins=True,
                              export_morph=True, export_morph_normal=False, export_extras=True)
    triangles = 0
    for mesh in meshes:
        mesh.data.calc_loop_triangles()
        triangles += len(mesh.data.loop_triangles)
    assert triangles < 80000, 'Photo face exceeded the geometry budget'
    blob = path.read_bytes()
    gltf = json.loads(blob[20:20 + struct.unpack_from('<I', blob, 12)[0]])
    assert len(blob) < 5 * 1024 * 1024, 'Photo model exceeds the LAN file budget'
    assert len(gltf['skins'][0]['joints']) == 16
    assert len(gltf.get('animations', [])) == (7 if identifier == 'ikun' else 0)
    assert len(gltf.get('images', [])) == 1 and 'bufferView' in gltf['images'][0] and 'uri' not in gltf['images'][0], 'Photo must be embedded for offline play'
    face = next(mesh for mesh in gltf['meshes'] if 'blink' in mesh.get('extras', {}).get('targetNames', []))
    assert all(name in face['extras']['targetNames'] for name in EXPRESSIONS)
    assert any('TEXCOORD_0' in primitive['attributes'] for primitive in face['primitives'])
    print('PHOTO_FACE', identifier, image.size[:], triangles, len(blob), path, flush=True)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, help='Local photo paths and measured pixel landmarks')
    parser.add_argument('--only', help='Comma-separated experiment IDs; default uses every supplied reference')
    parser.add_argument('--output-dir', default=str(PREVIEW))
    parser.add_argument('--write-assets', action='store_true', help='Copy validated previews to the three game asset paths')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    references = json.loads(Path(args.config).read_text())
    wanted = set(args.only.split(',')) if args.only else set(references)
    assert wanted and wanted <= set(IDENTIFIERS) and wanted <= set(references), 'Only the three v0.3 experiments are supported'
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    roster = {item['id']: item for item in R.read_roster()}
    generated = {identifier: build(identifier, references[identifier], output_dir, roster)
                 for identifier in IDENTIFIERS if identifier in wanted}
    if args.write_assets:
        for identifier, preview in generated.items():
            destination = ROOT / 'public' / 'assets' / (identifier + '.glb') if identifier == 'ikun' else R.OUT / (identifier + '.glb')
            if preview.resolve() != destination.resolve():
                pending = destination.with_suffix('.pending.glb')
                pending.write_bytes(preview.read_bytes())
                pending.replace(destination)
            print('UPDATED_ASSET', identifier, destination, flush=True)
    print('DONE', len(generated), 'local photo faces; original motion libraries unchanged', flush=True)


if __name__ == '__main__':
    main()
