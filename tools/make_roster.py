"""Build the expanded roster with Blender, without downloading models or animation.

blender --background --factory-startup --python tools/make_roster.py
blender --background --factory-startup --python tools/make_roster.py -- --only huaqiang --save-blend

Each fighter has its own mesh, sixteen compatible bones and four expression targets.
Four small motion libraries share the seven clips; models contain no duplicate clips.
"""
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
import make_characters as F
import refine_roster as D

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public' / 'assets' / 'roster'
OUT.mkdir(parents=True, exist_ok=True)
MOTION_OUT = ROOT / 'public' / 'assets' / 'motions'
MOTION_OUT.mkdir(parents=True, exist_ok=True)
CONTACT = .620 / 1.450
FAMILY_TYPES = {
    'knife': {'knife', 'sword', 'cleaver', 'dagger', 'blade', 'axe', 'fishfork', 'fork'},
    'orb': {'melon', 'watermelon', 'basketball', 'ball', 'fruit', 'food', 'bowl', 'soup', 'meat', 'cup', 'pot'},
    'staff': {'staff', 'polearm', 'halberd', 'spear', 'fan', 'cane', 'umbrella', 'flute', 'flag', 'baton', 'microphone', 'mic', 'guitar', 'wrench', 'hammer', 'ruler', 'keyboard', 'sax', 'racket', 'pan', 'rake'},
    'brawler': {'fist', 'fists', 'boxing', 'unarmed', 'gun', 'dualgun', 'pistol', 'rifle', 'document', 'book', 'bottle', 'phone', 'needle', 'bag', 'glove', 'coin', 'remote'},
}
ORIGINAL_FUNCTIONS = {name: getattr(F, name) for name in ('loft', 'ellipsoid', 'tube', 'curved')}


def low_loft(name, rings, mat, bone, segments=24):
    return ORIGINAL_FUNCTIONS['loft'](name, rings, mat, bone, min(segments, 40))


def low_ellipsoid(name, center, scale, mat, bone, segments=24, rings=14):
    return ORIGINAL_FUNCTIONS['ellipsoid'](name, center, scale, mat, bone, min(segments, 28), min(rings, 16))


def low_tube(name, points, radii, mat, bone, segments=10):
    return ORIGINAL_FUNCTIONS['tube'](name, points, radii, mat, bone, min(segments, 16))


def low_curved(name, control, radius, mat, bone, count=20, segments=8):
    return ORIGINAL_FUNCTIONS['curved'](name, control, radius, mat, bone, min(count, 24), min(segments, 10))


F.loft, F.ellipsoid, F.tube, F.curved = low_loft, low_ellipsoid, low_tube, low_curved


def seed_for(identifier):
    return int(hashlib.sha256(identifier.encode()).hexdigest()[:8], 16)


def rgb(value, fallback):
    if isinstance(value, (tuple, list)) and len(value) >= 3:
        return tuple(value[:3])
    if isinstance(value, str):
        try:
            h = value.lstrip('#')
            if len(h) == 3:
                h = ''.join(c * 2 for c in h)
            return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        except (ValueError, IndexError):
            pass
    return fallback


def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.shape_keys):
        for item in list(collection):
            if not item.users:
                collection.remove(item)
    F.parts = []


CORE = {
    'huaqiang': {'outfit': 'jacket', 'hair': 'buzz', 'weaponType': 'knife', 'primary': '#181c24', 'secondary': '#26303b', 'build': 'stocky', 'brow': 'hard'},
    'guatan': {'outfit': 'apron', 'hair': 'balding', 'weaponType': 'melon', 'primary': '#aaa58c', 'secondary': '#566477',
               'hairColor': '#56504a', 'build': 'heavy', 'face': 'round', 'age': 'old', 'brow': 'arched'},
    'chuanshanjia': {'outfit': 'cook', 'hair': 'short', 'headwear': 'cookcap', 'weaponType': 'soup', 'primary': '#adb193', 'secondary': '#4d5444', 'build': 'slim', 'brow': 'arched'},
    'zhugeliang': {'outfit': 'robe', 'hair': 'bun', 'headwear': 'scholar', 'beard': 'long', 'weaponType': 'fan', 'primary': '#cad2ca', 'secondary': '#557b72', 'build': 'slim'},
    'liyunlong': {'outfit': 'uniform', 'headwear': 'armycap', 'hair': 'short', 'weaponType': 'sword', 'primary': '#718164', 'secondary': '#454c36', 'build': 'stocky', 'brow': 'hard'},
    'liuxing': {'outfit': 'suspenders', 'hair': 'short', 'weaponType': 'baton', 'primary': '#d9d4c5', 'secondary': '#323a40', 'build': 'slim', 'brow': 'hard'},
    'liangfeifan': {'outfit': 'uniform', 'hair': 'short', 'headwear': 'policecap', 'weaponType': 'book', 'primary': '#4b5b4b', 'secondary': '#263a35', 'build': 'heavy', 'brow': 'hard'},
    'wuying': {'outfit': 'openjacket', 'hair': 'parted', 'weaponType': 'phone', 'primary': '#858f99', 'secondary': '#dfd8c1', 'build': 'slim', 'brow': 'arched'},
    'fahai': {'outfit': 'monk', 'hair': 'bald', 'weaponType': 'staff', 'primary': '#cb823c', 'secondary': '#8e3c28', 'build': 'athletic', 'brow': 'hard'},
    'heihuafu': {'outfit': 'tank', 'hair': 'spiky', 'beard': 'short', 'hairColor': '#a64728', 'weaponType': 'fist', 'primary': '#242634', 'secondary': '#773f31', 'build': 'athletic', 'brow': 'hard'},
    'yuanhua': {'outfit': 'school', 'hair': 'parted', 'weaponType': 'fishfork', 'primary': '#e5e0d7', 'secondary': '#305478', 'build': 'slim'},
    'madongmei': {'outfit': 'tracksuit', 'hair': 'ponytail', 'weaponType': 'spear', 'primary': '#bc4549', 'secondary': '#ebe4ca', 'build': 'stocky', 'female': True},
    'liuhaizhu': {'outfit': 'bare', 'headwear': 'strawhat', 'hair': 'short', 'weaponType': 'wrench', 'primary': '#b9a676', 'secondary': '#374659', 'build': 'slim', 'brow': 'hard'},
    'yanshuangying': {'outfit': 'coat', 'hair': 'slick', 'accessory': 'sunglasses', 'weaponType': 'dualgun', 'primary': '#222a34', 'secondary': '#414b52', 'build': 'athletic'},
    'xueyi': {'outfit': 'qipao', 'hair': 'curly', 'weaponType': 'bag', 'primary': '#713658', 'secondary': '#dfaf84', 'build': 'heavy', 'female': True},
    'rongmomo': {'outfit': 'qipao', 'hair': 'bun', 'headwear': 'palace', 'weaponType': 'needle', 'primary': '#443047', 'secondary': '#915075', 'build': 'stocky', 'female': True, 'age': 'old'},
    'liuxing_child': {'outfit': 'school', 'hair': 'short', 'weaponType': 'bag', 'primary': '#e2ddcd', 'secondary': '#336b7d', 'build': 'young'},
    'bujingyun': {'outfit': 'cape', 'hair': 'curly', 'weaponType': 'sword', 'primary': '#322d3a', 'secondary': '#a92930', 'build': 'athletic'},
    'youle': {'outfit': 'cape', 'hair': 'spiky', 'headwear': 'crown', 'weaponType': 'pistol', 'primary': '#315879', 'secondary': '#b42d40', 'build': 'slim'},
    'zhaobenshan': {'outfit': 'jacket', 'hair': 'balding', 'headwear': 'clothcap', 'accessory': 'scarf', 'age': 'old',
                    'weaponType': 'staff', 'primary': '#777b70', 'secondary': '#dddaca', 'hairColor': '#807b70', 'build': 'stocky'},
    'fanwei': {'outfit': 'sweater', 'hair': 'short', 'face': 'round', 'age': 'old', 'weaponType': 'fist',
               'primary': '#53665e', 'secondary': '#a1ad91', 'hairColor': '#514b40', 'build': 'heavy'},
    'chenglong': {'outfit': 'tracksuit', 'hair': 'parted', 'face': 'hard', 'age': 'young', 'weaponType': 'fist', 'gloves': True,
                  'primary': '#bda677', 'secondary': '#dfd2a8', 'hairColor': '#302a25', 'build': 'athletic'},
    'wujing': {'outfit': 'tracksuit', 'hair': 'buzz', 'face': 'hard', 'age': 'young', 'weaponType': 'fist', 'gloves': True,
               'primary': '#4b6858', 'secondary': '#bbc7a5', 'hairColor': '#282a24', 'build': 'athletic'},
    'wukong': {'outfit': 'armor', 'hair': 'monkeyfur', 'headwear': 'monkeyband', 'accessory': 'none', 'face': 'hard',
               'weaponType': 'staff', 'primary': '#b88b35', 'secondary': '#ce5133', 'hairColor': '#a7752e',
               'skin': '#d1ab72', 'build': 'slim'},
    'tangseng': {'outfit': 'robe', 'hair': 'bald', 'headwear': 'dharmacap', 'accessory': 'none', 'face': 'young',
                 'weaponType': 'staff', 'primary': '#b54032', 'secondary': '#d9ad4f', 'hairColor': '#382c24', 'build': 'slim'},
    'bajie': {'outfit': 'robe', 'hair': 'bald', 'headwear': 'pigcap', 'accessory': 'none', 'face': 'round',
              'weaponType': 'rake', 'primary': '#4f4a43', 'secondary': '#ba956c', 'skin': '#d7a88c', 'build': 'heavy'},
}


def configuration(item):
    style = item.get('appearance', item.get('style', {}))
    if isinstance(style, str):
        style = {'outfit': style}
    result = dict(style)
    result['id'] = item['id']
    result.update({out: style.get(field) for field, out in [('bodyColor', 'primary'), ('trimColor', 'secondary'),
                                                         ('skinColor', 'skin')] if style.get(field)})
    result['hair'] = {'crop': 'short', 'topknot': 'bun'}.get(result.get('hair'), result.get('hair', 'short'))
    result['build'] = {'normal': 'regular', 'broad': 'stocky'}.get(result.get('build'), result.get('build', 'regular'))
    if result.get('face') == 'aged':
        result['age'] = 'old'
    if result.get('face') == 'hard':
        result['brow'] = 'hard'
    if result.get('accessory') == 'beard':
        result['beard'] = 'long'
    if result.get('accessory') == 'moustache':
        result['beard'] = 'moustache'
    if result.get('accessory') in ('cap', 'crown'):
        result['headwear'] = result['accessory']
    for field in ('outfit', 'hair', 'headwear', 'accessory', 'beard', 'weaponType', 'build', 'body', 'primary', 'secondary', 'hairColor', 'skin', 'age', 'female'):
        if field in item:
            result[field] = item[field]
    # Source-specific named silhouettes override the broad roster taxonomy.
    result.update(CORE.get(item['id'], {}))
    if item['id'] in ('guodegang', 'yuqian'):
        result['fanStyle'] = 'folding'
    result.update(D.PROFILES[item['id']])
    result.setdefault('outfit', result.get('body', 'jacket'))
    result.setdefault('hair', 'short')
    result.setdefault('weaponType', 'fist')
    result.setdefault('build', 'regular')
    result.setdefault('pantsColor', result['primary'] if result['outfit'] in ('suit', 'uniform', 'tracksuit', 'armor', 'robe', 'coat') else '#384552')
    return result


def palette(identifier, config):
    def linear(value, fallback):
        return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb(value, fallback))
    primary = linear(config.get('primary'), (.19, .24, .32))
    secondary = linear(config.get('secondary'), (.54, .58, .61))
    skin_color = linear(config.get('skin'), (.68, .41, .28))
    hair_color = linear(config.get('hairColor'), (.025, .025, .034))
    skin = F.material(identifier + ' · face skin', skin_color, roughness=.72)
    F.skin, F.aged = skin, skin
    return {'main': F.material(identifier + ' · garment', primary, roughness=.92),
            'pants': F.material(identifier + ' · trouser fabric', linear(config['pantsColor'], (.18, .23, .28)), roughness=.94),
            'trim': F.material(identifier + ' · panels and trim', secondary, roughness=.87),
            'skin': skin, 'hair': F.material(identifier + ' · sculpted hair', hair_color, roughness=.81),
            'dark': F.cloth, 'white': F.ivory, 'metal': F.steel, 'bright': F.steelbright,
            'gold': F.gold, 'wood': F.material(identifier + ' · carved wood', (.25, .13, .055), roughness=.9)}


def visual_metadata(item):
    """Expose the authored model overrides to first-person hands and equipment."""
    config = configuration(item)
    output = {'weaponType': config['weaponType'],
              'colorSpace': 'srgb',
              'bodyColor': config.get('primary', '#303d52'),
              'trimColor': config.get('secondary', '#8a949c'),
              'hairColor': config.get('hairColor', '#060609'),
              'skinColor': config.get('skin', '#ad6947'),
              'outfit': config['outfit'], 'hair': config['hair'], 'build': config['build']}
    for field in ('headwear', 'accessory', 'beard', 'age', 'face', 'female', 'gloves', 'fanStyle', 'temperament', 'referenceCue'):
        if field in config:
            output[field] = config[field]
    return output


def body(config, mats, seed):
    outfit = config['outfit'].lower()
    build = config['build']
    width = {'slim': .88, 'heavy': 1.20, 'stocky': 1.12, 'athletic': 1.08, 'young': .86}.get(build, 1)
    width *= .975 + .05 * ((seed >> 3) % 19) / 18
    bare = outfit in ('bare', 'tank', 'vest', 'monk', 'singlet', 'sleeveless')
    top = mats['skin'] if outfit == 'bare' else mats['main']
    F.loft('Torso · shaped chest and waist', [(0, .022, 1.03, .255 * width, .16), (0, .013, 1.18, .258 * width, .17),
                                           (0, .007, 1.40, .30 * width, .19), (0, .014, 1.56, .333 * width, .19),
                                           (0, .021, 1.66, .30 * width, .166), (0, .02, 1.69, .205 * width, .12)], top, 'spine')
    F.loft('Waistband', [(0, .015, .96, .24 * width, .16), (0, .012, 1.11, .25 * width, .165)], mats['pants'], 'hips')
    for sign, side in [(1, 'L'), (-1, 'R')]:
        arm, forearm = 'upper.' + side, 'forearm.' + side
        sleeve = mats['skin'] if bare else mats['main']
        F.ellipsoid('Shoulder cap.' + side, (sign * .338, .022, 1.604), (.13 * width, .14, .135), sleeve, arm)
        F.tube('Upper arm.' + side, [(sign * .337, .022, 1.64), (sign * .42, .021, 1.49), (sign * .494, .012, 1.30)],
               [.12 * width, .11 * width, .083 * width], sleeve, arm)
        F.ellipsoid('Elbow.' + side, (sign * .495, .009, 1.29), (.088 * width, .09, .08), sleeve, forearm)
        F.tube('Forearm.' + side, [(sign * .496, .009, 1.31), (sign * .514, -.014, 1.15), (sign * .510, -.04, .98)],
               [.083 * width, .08 * width, .054], mats['skin'] if bare or outfit in ('school', 'shirt', 'suspenders') else sleeve, forearm)
        F.hand(side, sign, 'ikun')
        F.tube('Trouser thigh.' + side, [(sign * .17, .026, 1.0), (sign * .183, .026, .80), (sign * .19, 0, .54)],
               [.14 * width, .12 * width, .094], mats['pants'], 'thigh.' + side)
        F.ellipsoid('Knee.' + side, (sign * .19, .0, .54), (.095, .097, .075), mats['pants'], 'shin.' + side)
        F.tube('Trouser shin.' + side, [(sign * .19, 0, .54), (sign * .19, .012, .35), (sign * .19, .012, .145)],
               [.095, .085, .065], mats['pants'], 'shin.' + side)
        F.ellipsoid('Toe and boot.' + side, (sign * .19, -.083, .104), (.101, .17, .085), mats['dark'], 'foot.' + side)
        F.slab('Heel and sole.' + side, (sign * .19, -.073, .043), (.103, .16, .024), mats['dark'], 'foot.' + side, .008)
        if outfit in ('uniform', 'police', 'military', 'cook'):
            F.slab('Sleeve rank.' + side, (sign * .443, -.091, 1.43), (.048, .009, .035), mats['trim'], arm, .004)
        if outfit == 'tracksuit':
            F.tube('Sport stripe.' + side, [(sign * .35, -.13, 1.62), (sign * .45, -.105, 1.40)], .015, mats['trim'], arm)
            F.tube('Trouser sport stripe.' + side, [(sign * .27, .005, .9), (sign * .27, .005, .58)], .014, mats['main'], 'thigh.' + side)
    if outfit in ('robe', 'monk', 'qipao', 'cape', 'court', 'scholar'):
        F.loft('Robe skirt · separate sculpted silhouette', [(0, .02, .20, .36 * width, .25), (0, .02, .50, .32 * width, .23),
                                                           (0, .02, .82, .29 * width, .20), (0, .02, 1.10, .252 * width, .17)], mats['main'], 'hips')
        for i in range(5):
            x = (i - 2) * .102 * width
            F.curved('Robe seam', [(x * .5, -.15, 1), (x * .8, -.21, .77), (x, -.23, .45), (x * 1.06, -.22, .23)],
                     .007, mats['trim'], 'hips', 12)
    if outfit in ('jacket', 'openjacket', 'coat', 'suit', 'uniform', 'police', 'military', 'cook'):
        for sign in (-1, 1):
            if config['id'] != 'huaqiang':
                F.leaf('Folded collar lapel', (sign * .17, -.113, 1.68), (sign * .088, -.202, 1.40), .051,
                       mats['trim'], 'spine', .012, .008)
                F.slab('Chest pocket', (sign * .16, -.194, 1.43), (.061, .012, .067), mats['main'], 'spine', .006)
            else:
                F.slab('Flat jacket pocket welt', (sign * .16, -.167, 1.43), (.046, .004, .008), mats['main'], 'spine', .003)
        if config['id'] == 'huaqiang':
            F.loft('Black standing jacket collar', [(0, .023, 1.663, .123, .127), (0, .024, 1.766, .128, .135)], mats['main'], 'spine')
            F.tube('Quiet jacket zipper seam', [(0, -.180, 1.15), (0, -.185, 1.51), (0, -.153, 1.65)], .0035, mats['dark'], 'spine', 4)
        for i in range(4):
            F.ellipsoid('Coat button', (0, -.187, 1.26 + i * .085), (.009, .009, .011), mats['metal'], 'spine', 8, 6)
        if outfit == 'coat':
            F.loft('Long coat tails', [(0, .025, .56, .30 * width, .23), (0, .025, .76, .28 * width, .21),
                                       (0, .015, 1.07, .257 * width, .17)], mats['main'], 'hips')
    if outfit in ('school', 'shirt', 'suspenders', 'suit'):
        for sign in (-1, 1):
            F.leaf('Shirt pointed collar', (sign * .08, -.108, 1.68), (sign * .14, -.186, 1.53), .045, mats['white'], 'spine', .007)
        if outfit == 'suit':
            F.leaf('Necktie', (0, -.173, 1.60), (0, -.201, 1.27), .034, mats['trim'], 'spine', .006)
        if outfit == 'suspenders':
            for sign in (-1, 1):
                F.curved('Fabric suspender', [(sign * .20, -.11, 1.68), (sign * .19, -.203, 1.50),
                                             (sign * .18, -.198, 1.29), (sign * .16, -.17, 1.1)], .019, mats['dark'], 'spine')
    if outfit == 'tank':
        F.curved('Tank neck opening', [(-.16, -.12, 1.65), (-.13, -.171, 1.47), (.13, -.171, 1.47), (.16, -.12, 1.65)],
                 .021, mats['trim'], 'spine')
    if outfit == 'sweater':
        F.loft('Sweater ribbed collar', [(0, .025, 1.66, .124, .128), (0, .025, 1.75, .127, .132)], mats['trim'], 'spine')
        for i in range(9):
            x = (i - 4) * .046
            F.curved('Sweater woven rib', [(x, -.158, 1.10), (x, -.181, 1.25), (x, -.190, 1.40), (x, -.174, 1.53)], .0025, mats['trim'], 'spine', 9, 4)
        for sign, side in [(1, 'L'), (-1, 'R')]:
            F.loft('Sweater cuff.' + side, [(sign * .51, -.035, .987, .058, .058), (sign * .51, -.030, 1.045, .061, .061)], mats['trim'], 'forearm.' + side)
    if outfit in ('robe', 'monk', 'court', 'scholar'):
        for sign in (-1, 1):
            F.curved('Crossed robe collar', [(sign * .15, -.11, 1.68), (sign * .12, -.181, 1.58),
                                            (-sign * .05, -.201, 1.35), (-sign * .17, -.174, 1.13)], .022, mats['trim'], 'spine')
    if outfit == 'qipao':
        F.loft('Standing qipao collar', [(0, .024, 1.65, .115, .12), (0, .025, 1.77, .115, .12)], mats['main'], 'spine')
        F.curved('Asymmetric qipao closure', [(0, -.12, 1.74), (.16, -.17, 1.65), (.17, -.207, 1.49), (.12, -.205, 1.36)], .010, mats['trim'], 'spine')
        for i in range(3):
            F.slab('Qipao frog knot', (.16, -.207, 1.42 + i * .08), (.025, .008, .009), mats['trim'], 'spine', .003)
    if outfit in ('cape', 'monk'):
        F.mesh('Cape · broad back silhouette', [(-.31, .13, 1.65), (.31, .13, 1.65), (.40, .26, .64), (-.40, .26, .64),
                                                (-.28, .16, 1.65), (.28, .16, 1.65), (.37, .29, .65), (-.37, .29, .65)],
               [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], mats['trim'], 'spine')
    if outfit in ('cook', 'apron'):
        F.slab('Cook apron bib', (0, -.201, 1.43), (.175, .012, .175), mats['white'], 'spine', .006)
        F.slab('Cook apron lower panel', (0, -.192, .94), (.24, .011, .22), mats['white'], 'hips', .008)
    if outfit in ('armor', 'warrior', 'samurai'):
        F.loft('Breastplate', [(0, 0, 1.16, .28, .185), (0, 0, 1.4, .315 * width, .209), (0, .02, 1.61, .32 * width, .18)], mats['metal'], 'spine')
        for sign, side in [(1, 'L'), (-1, 'R')]:
            for row in range(2):
                F.ellipsoid('Layered pauldron.' + side, (sign * (.36 + row * .025), .015, 1.64 - row * .07), (.17, .15, .07), mats['main'], 'upper.' + side)
        for row in range(3):
            for col in range(5):
                F.slab('Armor scale', ((col - 2) * .09, -.207, 1.24 + row * .09), (.041, .012, .035), mats['trim'], 'spine', .004)
    if config['id'] == 'snowking':
        F.ellipsoid('Snowman upper sphere', (0, .02, 1.40), (.39, .30, .39), mats['main'], 'spine', 20, 12)
        F.ellipsoid('Snowman lower sphere', (0, .02, .88), (.43, .31, .39), mats['main'], 'hips', 20, 12)
        for z in (1.23, 1.39, 1.54):
            F.ellipsoid('Snowman charcoal button', (0, -.29, z), (.026, .014, .028), mats['dark'], 'spine', 10, 7)
        F.mesh('Snowman red cape', [(-.35, .12, 1.62), (.35, .12, 1.62), (.43, .35, .71), (-.43, .35, .71),
                                    (-.35, .14, 1.62), (.35, .14, 1.62), (.43, .37, .71), (-.43, .37, .71)],
               [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], mats['trim'], 'spine')
    if config['id'] == 'wukong':
        F.curved('Monkey articulated tail', [(0, .15, .94), (.19, .42, .93), (.38, .51, .65), (.43, .44, .80)],
                 .034, mats['hair'], 'hips', 18)
        for sign in (-1, 1):
            for i in range(4):
                F.leaf('Tiger skirt dark stripe', (sign * (.09 + i * .049), -.186, .985),
                       (sign * (.12 + i * .061), -.217, .78), .025, mats['dark'], 'hips', .005)
    if config['id'] == 'tangseng':
        for z in (1.23, 1.35, 1.47, 1.59):
            points = [(x, .014 - .195 * math.sqrt(max(.01, 1 - (x / .33) ** 2)) - .009, z) for x in [i * .05 for i in range(-5, 6)]]
            F.tube('Kasaya golden patch seam', points, .005, mats['trim'], 'spine', 4)
        for x in (-.17, -.055, .065, .17):
            F.tube('Kasaya vertical patch seam', [(x, -.19, 1.17), (x, -.194, 1.37), (x, -.187, 1.57)], .0045, mats['trim'], 'spine', 4)
    if config['id'] == 'bajie':
        F.ellipsoid('Pig large rounded belly', (0, -.035, 1.16), (.405, .295, .33), mats['skin'], 'spine', 20, 12)
        F.curved('Pig belly waist sash', [(-.31, -.245, 1.005), (-.10, -.329, .98), (.10, -.329, .98), (.31, -.245, 1.005)],
                 .021, mats['main'], 'hips')
    if outfit == 'clown':
        for z in (1.19, 1.29, 1.39, 1.49):
            F.slab('Clown striped shirt front', (0, -.20, z), (.22, .014, .023), mats['trim'], 'spine', .008)
        for sign, side in [(1, 'L'), (-1, 'R')]:
            F.ellipsoid('Clown oversized shoe.' + side, (sign * .19, -.125, .103), (.145, .26, .088), mats['trim'], 'foot.' + side)
            F.leaf('Clown collar point', (sign * .02, -.12, 1.68), (sign * .23, -.19, 1.53), .072, mats['white'], 'spine', .01)
    D.clothing(config, mats, width)


def head(config, mats, seed):
    aged = config.get('age') in ('old', 'elder', 'aged') or config.get('beard') in ('white', 'longwhite')
    F.beard = mats['hair']
    face_type = 'wang' if aged else 'lubu' if config['build'] in ('athletic', 'heavy', 'stocky') or config.get('face') == 'hard' or config.get('brow') == 'hard' else 'ikun'
    if config['id'] == 'snowking':
        F.ellipsoid('Snowman round head', (0, .025, 2.015), (.305, .25, .30), mats['main'], 'head', 20, 12)
        for sign in (-1, 1):
            F.ellipsoid('Almond eye · snowman', (sign * .096, -.218, 2.026), (.021, .013, .030), mats['dark'], 'head', 12, 8)
            F.curved('Expressive eyebrow · snowman', [(sign * .145, -.209, 2.105), (sign * .117, -.225, 2.115),
                                                     (sign * .075, -.231, 2.116), (sign * .053, -.213, 2.109)], .007, mats['dark'], 'head')
        F.curved('Upper lip · snowman smile', [(-.065, -.218, 1.935), (-.037, -.238, 1.902),
                                             (.037, -.238, 1.902), (.065, -.218, 1.935)], .009, mats['dark'], 'head')
        F.ellipsoid('Snowman carrot nose', (0, -.232, 1.976), (.021, .044, .025), F.orange, 'head')
    else:
        F.face(face_type)
    if config['id'] in ('wukong', 'bajie'):
        for obj in list(F.parts):
            if obj.name.startswith(('Ear helix', 'Ear concha', 'Rounded nose', 'Nose wing', 'Nostril')):
                F.parts.remove(obj)
                bpy.data.objects.remove(obj, do_unlink=True)
        if config['id'] == 'wukong':
            F.ellipsoid('Monkey soft muzzle', (0, -.18, 1.928), (.105, .066, .064), mats['skin'], 'head')
            F.ellipsoid('Monkey rounded dark nose', (0, -.257, 1.978), (.029, .016, .018), mats['hair'], 'head', 12, 8)
            for obj in F.parts:
                if obj.name.startswith(('Upper lip', 'Lower lip')):
                    for v in obj.data.vertices:
                        v.co.y -= .075
            for sign in (-1, 1):
                F.ellipsoid('Monkey round outer ear', (sign * .251, .028, 2.003), (.065, .040, .074), mats['hair'], 'head')
                F.ellipsoid('Monkey ear inner cup', (sign * .268, -.007, 2.002), (.043, .013, .052), mats['skin'], 'head', 12, 8)
                for i in range(5):
                    z = 1.84 + i * .065
                    F.leaf('Monkey golden cheek fur', (sign * .192, .022, z + .025),
                           (sign * (.27 + .012 * (i % 2)), -.012, z - .045), .046, mats['hair'], 'head', .016, .006)
        else:
            F.ellipsoid('Pig protruding snout', (0, -.228, 1.962), (.083, .067, .051), mats['skin'], 'head')
            for sign in (-1, 1):
                F.ellipsoid('Pig snout nostril', (sign * .027, -.291, 1.966), (.013, .007, .015), F.lip, 'head', 10, 7)
                F.leaf('Pig large drooping ear', (sign * .217, .020, 2.106), (sign * .365, -.010, 1.852),
                       .071, mats['skin'], 'head', .030, .006)
                F.leaf('Pig ear inner fold', (sign * .233, -.003, 2.087), (sign * .352, -.030, 1.866),
                       .046, F.lip, 'head', .005, .005)
            for obj in F.parts:
                if obj.name.startswith(('Upper lip', 'Lower lip')):
                    for v in obj.data.vertices:
                        v.co.x *= 1.27
    # Coherent individual proportions alter the cranium and all attached features.
    # Stable authored anatomy replaces hash-based likeness variation.
    x_scale, z_scale, nose_scale = 1, 1, 1
    for obj in F.parts:
        if any(g.name == 'head' for g in obj.vertex_groups):
            for v in obj.data.vertices:
                v.co.x *= x_scale
                v.co.z = 2.026 + (v.co.z - 2.026) * z_scale
                if obj.name.startswith(('Rounded nose', 'Nose wing', 'Nostril')):
                    v.co.x *= nose_scale
                if obj.name.startswith('Expressive eyebrow') and config.get('brow') == 'arched':
                    v.co.z += .014 * abs(v.co.x) / .14
                if config['id'] == 'guatan' and obj.name.startswith('Sculpted jaw') and v.co.z < 2:
                    v.co.x *= 1.04 + (2 - v.co.z) * .10
    if config['outfit'] == 'clown':
        F.ellipsoid('Clown round red nose', (0, -.251, 1.986), (.047, .042, .047), mats['trim'], 'head')
        for sign in (-1, 1):
            F.ellipsoid('Clown cheek painted dot', (sign * .125, -.167, 1.96), (.024, .008, .024), mats['trim'], 'head')
    hair = config.get('hair', 'short').lower()
    if hair not in ('bald', 'none'):
        z0 = 2.115 if hair in ('buzz', 'short', 'slick') else 2.055
        if hair != 'balding':
            F.loft('Hair crown · ' + hair, [(0, .047, z0, .205 * x_scale, .18), (0, .049, 2.20, .192 * x_scale, .18),
                                          (0, .051, 2.275, .126 * x_scale, .117), (0, .052, 2.29, .014, .015)], mats['hair'], 'head')
        if hair == 'balding':
            # A genuine open crown: sparse hair exists only around the ears/back.
            # Moving a full hair cap higher still looked like a young buzz cut.
            for sign in (-1, 1):
                F.curved('Sparse temple hair', [(sign * .218, .01, 2.040), (sign * .223, .04, 2.115),
                                               (sign * .205, .10, 2.16), (sign * .177, .13, 2.18)], .015, mats['hair'], 'head')
                F.curved('Sparse temple silver strand', [(sign * .224, .016, 2.047), (sign * .227, .046, 2.112),
                                                        (sign * .213, .10, 2.15), (sign * .183, .132, 2.17)], .0035, F.beard, 'head')
            points = [(.20 * math.cos(i * math.pi / 18), .04 + .17 * math.sin(i * math.pi / 18), 2.154) for i in range(19)]
            F.tube('Receding back hair fringe', points, .022, mats['hair'], 'head', 6)
        if hair in ('parted', 'slick', 'short', 'ponytail', 'bun'):
            for i in range(6):
                x = (i - 2.5) * .062
                F.curved('Swept hair strand', [(x, -.105, 2.14), (x - .035, -.177, 2.20),
                                              (x + .023, -.10, 2.30), (x * .8, .053, 2.27)], .013, mats['hair'], 'head', 12)
        if hair == 'spiky':
            for i in range(9):
                a = i * math.tau / 9
                F.leaf('Pointed hair lock', (.12 * math.cos(a), .05 + .08 * math.sin(a), 2.23),
                       (.20 * math.cos(a), .05 + .14 * math.sin(a), 2.35 + .06 * (i % 2)), .044, mats['hair'], 'head', .025)
        if hair in ('curly', 'afro', 'long', 'wavy'):
            for i in range(12):
                a = i * math.tau / 12
                F.ellipsoid('Curled hair cluster', (.195 * math.cos(a), .06 + .17 * math.sin(a), 2.16 + .05 * (i % 3)),
                            (.058, .057, .085 if hair != 'afro' else .10), mats['hair'], 'head', 12, 7)
            if hair in ('long', 'wavy'):
                for sign in (-1, 1):
                    F.curved('Long hair fall', [(sign * .20, .02, 2.18), (sign * .24, .11, 2.01),
                                               (sign * .25, .17, 1.85), (sign * .18, .17, 1.69)], .067, mats['hair'], 'head')
        if hair in ('ponytail', 'bun'):
            F.ellipsoid('Tied hair bun', (0, .21, 2.15), (.093, .085, .081), mats['hair'], 'head')
            if hair == 'ponytail':
                F.curved('Ponytail', [(0, .22, 2.15), (.035, .31, 2.03), (.09, .26, 1.84), (.10, .24, 1.69)], .060, mats['hair'], 'head')
    beard = config.get('beard', 'none')
    if beard not in ('none', '', False, None):
        long = beard in ('long', 'white', 'longwhite', 'forked')
        for i in range(0 if beard == 'moustache' else 7 if long else 5):
            x = (i - (3 if long else 2)) * .027
            F.curved('Beard shaped strand', [(x, -.151, 1.84), (x * 1.06, -.196, 1.78),
                                            (x * .86, -.19, 1.68 if long else 1.81),
                                            (x * .77, -.178, 1.55 + abs(i - 3) * .02 if long else 1.775)],
                     .020, mats['hair'], 'head')
        for sign in (-1, 1):
            F.curved('Moustache', [(sign * .006, -.204, 1.917), (sign * .04, -.219, 1.92),
                                  (sign * .074, -.198, 1.91), (sign * .095, -.173, 1.89)], .016, mats['hair'], 'head')
    hat = config.get('headwear', 'none').lower()
    if hat in ('armycap', 'policecap', 'cap', 'cookcap', 'baseball', 'beret', 'clothcap'):
        F.loft('Cap crown · ' + hat, [(0, .04, 2.16, .215, .187), (0, .04, 2.25, .224, .193),
                                     (0, .055, 2.31, .178, .151)], mats['main'] if hat != 'cookcap' else mats['white'], 'head')
        F.slab('Cap visor', (0, -.17, 2.17), (.175, .070 if hat == 'clothcap' else .103, .017), mats['main'] if hat == 'clothcap' else mats['dark'], 'head', .012)
        if hat != 'clothcap':
            F.ellipsoid('Cap emblem', (0, -.158, 2.26), (.027, .011, .031), mats['trim'], 'head', 12, 8)
    elif hat in ('strawhat', 'farmer'):
        F.loft('Straw hat dome', [(0, .04, 2.18, .223, .18), (0, .04, 2.28, .18, .145), (0, .04, 2.36, .064, .053)], mats['wood'], 'head')
        F.loft('Broad straw brim', [(0, .04, 2.18, .36, .31), (0, .04, 2.204, .355, .305)], mats['trim'], 'head')
        for i in range(10):
            a = i * math.tau / 10
            F.tube('Hat straw seam', [(.22 * math.cos(a), .04 + .18 * math.sin(a), 2.225),
                                    (.34 * math.cos(a), .04 + .29 * math.sin(a), 2.214)], .003, mats['wood'], 'head', 4)
    elif hat in ('scholar', 'court', 'official', 'qing', 'palace', 'crown', 'helmet', 'pharaoh', 'wizard', 'cowboy'):
        F.loft('Authored headwear · ' + hat, [(0, .04, 2.16, .216, .18), (0, .04, 2.26, .219, .18),
                                           (0, .06, 2.38 if hat != 'helmet' else 2.32, .155, .133)], mats['dark'] if hat != 'crown' else mats['gold'], 'head')
        if hat == 'scholar':
            for sign in (-1, 1):
                F.slab('Scholar crown folded panel', (sign * .067, .015, 2.39), (.045, .11, .07), mats['trim'], 'head', .010)
        if hat in ('court', 'official', 'palace'):
            for sign in (-1, 1):
                F.slab('Court headwear wing', (sign * .33, .045, 2.24), (.16, .032, .022), mats['dark'], 'head', .013)
        if hat == 'qing':
            F.loft('Qing red silk crown', [(0, .04, 2.25, .207, .17), (0, .04, 2.40, .017, .015)], mats['trim'], 'head')
            F.curved('Long braided queue', [(0, .21, 2.11), (0, .24, 1.98), (.025, .24, 1.75), (.015, .23, 1.44)], .024, mats['hair'], 'head')
        if hat == 'crown':
            for i in range(5):
                F.leaf('Crown point', ((i - 2) * .07, -.14, 2.30), ((i - 2) * .07, -.12, 2.45 + .03 * (i % 2)), .037, mats['gold'], 'head', .011)
        if hat == 'wizard':
            F.loft('Wizard pointed hat', [(0, .04, 2.28, .25, .22), (0, .055, 2.55, .12, .11), (.09, .10, 2.82, .005, .005)], mats['main'], 'head')
    if hat == 'monkeyband':
        points = [(.224 * math.cos(i * math.tau / 36), .04 + .192 * math.sin(i * math.tau / 36), 2.135) for i in range(37)]
        F.tube('Monkey golden circlet', points, .013, mats['gold'], 'head', 6)
        for sign in (-1, 1):
            F.curved('Monkey circlet front curl', [(sign * .065, -.157, 2.14), (sign * .016, -.175, 2.162),
                                                  (sign * .008, -.174, 2.112), (sign * .036, -.164, 2.119)], .010, mats['gold'], 'head')
    if hat == 'dharmacap':
        F.loft('Dharmic red hat band', [(0, .04, 2.165, .219, .184), (0, .055, 2.27, .215, .18)], mats['main'], 'head')
        for i in range(5):
            x = (i - 2) * .079
            F.leaf('Dharmic five-panel crown', (x, -.126, 2.22), (x * 1.05, -.083, 2.44 - abs(i - 2) * .023),
                   .047, mats['gold'], 'head', .011, .009)
            F.ellipsoid('Dharmic crown red inset', (x, -.127, 2.309), (.024, .007, .036), mats['main'], 'head', 12, 8)
        for sign in (-1, 1):
            F.leaf('Dharmic hat trailing ribbon', (sign * .18, .12, 2.21), (sign * .15, .19, 1.81), .034, mats['trim'], 'head', .006)
    if hat == 'pigcap':
        F.loft('Pig soft cloth cap', [(0, .07, 2.18, .225, .175), (0, .085, 2.28, .18, .145), (0, .09, 2.33, .07, .064)], mats['main'], 'head')
        for sign in (-1, 1):
            F.leaf('Pig headscarf side tie', (sign * .203, .06, 2.20), (sign * .26, .12, 2.07), .025, mats['trim'], 'head', .007)
    accessory = config.get('accessory', 'none').lower()
    if accessory in ('glasses', 'sunglasses', 'goggles'):
        for sign in (-1, 1):
            F.slab('Glasses lens', (sign * .093, -.199, 2.026), (.051, .006, .029), mats['dark'] if accessory != 'glasses' else mats['metal'], 'head', .013)
        F.tube('Glasses bridge', [(-.043, -.20, 2.033), (.043, -.20, 2.033)], .005, mats['metal'], 'head')
    if accessory in ('headphones', 'headset'):
        for sign in (-1, 1):
            F.ellipsoid('Headphone earcup', (sign * .24, .025, 2.027), (.045, .055, .080), mats['dark'], 'head')
        F.curved('Headphone headband', [(-.24, .035, 2.08), (-.23, .035, 2.36), (.23, .035, 2.36), (.24, .035, 2.08)], .025, mats['trim'], 'head')
    if accessory == 'headband':
        F.loft('Fabric headband', [(0, .04, 2.12, .216, .187), (0, .04, 2.159, .216, .187)], mats['trim'], 'head')
    if accessory == 'scarf':
        F.loft('Neck scarf folds', [(0, .026, 1.685, .128, .132), (0, .026, 1.759, .13, .137)], mats['trim'], 'spine')
        F.leaf('Scarf hanging panel', (.064, -.131, 1.714), (.15, -.205, 1.36), .063, mats['trim'], 'spine', .012)
    D.face_and_hair(config, mats)


def weapon(config, mats):
    kind = config['weaponType'].lower()
    grip = Vector((-.51, -.14, .93))
    bone = 'hand.R'
    tip = grip + Vector((0, -.03, .20))
    if kind in ('knife', 'cleaver', 'sword', 'dagger', 'blade', 'axe', 'fishfork', 'fork'):
        F.tube('Weapon grip', [grip + Vector((0, 0, -.08)), grip + Vector((0, 0, .13))], .024, mats['wood'], bone)
        F.slab('Blade guard', grip + Vector((0, 0, .13)), (.09 if kind == 'sword' else .042, .016, .017), mats['metal'], bone, .006)
        length = .76 if kind == 'sword' else .38
        tip = grip + Vector((0, 0, .15 + length))
        if kind in ('cleaver', 'axe'):
            F.slab('Broad cleaver blade', grip + Vector((-.075, 0, .33)), (.10, .016, .18), mats['bright'], bone, .012)
            tip = grip + Vector((-.17, 0, .49))
        elif kind in ('fishfork', 'fork'):
            for i in range(3):
                F.tube('Fishfork prong', [grip + Vector(((i - 1) * .08, 0, .13)), grip + Vector(((i - 1) * .08, 0, .61))], [.015, .004], mats['metal'], bone)
            F.tube('Fishfork crosspiece', [grip + Vector((-.08, 0, .21)), grip + Vector((.08, 0, .21))], .018, mats['metal'], bone)
            tip = grip + Vector((0, 0, .61))
        else:
            F.leaf('Pointed blade · beveled ridge', grip + Vector((0, 0, .13)), tip, .052 if kind == 'sword' else .064, mats['bright'], bone, .018, .005)
    elif kind in ('melon', 'watermelon', 'ball', 'basketball', 'fruit', 'food', 'meat'):
        radius = .187 if kind not in ('melon', 'watermelon') else .23
        center = grip + Vector((0, -.053, 0))
        fruit = F.material('Watermelon dark skin', (.052, .27, .09), roughness=.91) if kind in ('melon', 'watermelon') else F.orange
        F.ellipsoid('Held round fruit or ball', center, (radius, radius, radius), fruit, bone, 20, 12)
        stripe = F.material('Watermelon bright rind stripes', (.19, .43, .11), roughness=.9) if kind in ('melon', 'watermelon') else F.seam
        for i in range(6):
            a = i * math.tau / 6
            points = []
            for j in range(21):
                t = -.5 * math.pi + j * math.pi / 20
                points.append(center + Vector((math.cos(t) * math.cos(a), math.cos(t) * math.sin(a), math.sin(t))) * radius * 1.008)
            F.tube('Round object curved seam', points, .005 if kind in ('melon', 'watermelon') else .003, stripe, bone, 4)
        tip = center + Vector((0, -radius, 0))
    elif kind in ('bowl', 'soup', 'pot', 'cup'):
        center = grip + Vector((0, -.13, .04))
        r = .22 if kind in ('soup', 'pot') else .14
        F.loft('Soup bowl outer shell', [(center.x, center.y, center.z - .1, r * .65, r * .65),
                                       (center.x, center.y, center.z + .055, r, r),
                                       (center.x, center.y, center.z + .075, r, r)], mats['metal'] if kind == 'pot' else mats['white'], bone)
        broth = F.material('Soup warm amber', (.64, .31, .08), roughness=.3)
        F.loft('Visible soup surface', [(center.x, center.y, center.z + .06, r * .93, r * .93),
                                       (center.x, center.y, center.z + .063, r * .93, r * .93)], broth, bone)
        for i in range(3):
            F.ellipsoid('Soup ingredient', (center.x + (i - 1) * .07, center.y - .03, center.z + .072), (.025, .016, .010), F.jade, bone, 8, 5)
        F.tube('Soup ladle', [grip + Vector((.07, 0, .07)), grip + Vector((.10, 0, .43))], .009, mats['metal'], bone)
        tip = center + Vector((0, -r, .07))
    elif kind in ('staff', 'polearm', 'halberd', 'spear', 'cane', 'umbrella', 'flag', 'baton', 'flute', 'ruler', 'microphone', 'mic', 'sax'):
        length = 1.15 if kind in ('staff', 'polearm', 'halberd', 'spear', 'flag') else .45
        F.tube('Long weapon shaft', [grip + Vector((0, 0, -.30)), grip + Vector((0, 0, length))], [.021, .018], mats['wood'] if kind not in ('mic', 'microphone', 'sax', 'ruler') else mats['metal'], bone)
        tip = grip + Vector((0, 0, length))
        if kind in ('polearm', 'halberd', 'spear'):
            F.leaf('Spear cutting head', tip - Vector((0, 0, .06)), tip + Vector((0, 0, .26)), .057, mats['bright'], bone, .014)
            tip += Vector((0, 0, .26))
        if kind == 'halberd':
            F.crescent('Halberd crescent', tip - Vector((0, 0, .15)), .20, .08, mats['metal'], bone)
        if kind == 'staff':
            if config['id'] == 'wukong':
                for offset in (-.29, 1.13):
                    F.loft('Golden staff end ferrule', [(grip.x, grip.y, grip.z + offset - .044, .031, .031),
                                                      (grip.x, grip.y, grip.z + offset + .044, .031, .031)], mats['gold'], bone)
                tip += Vector((0, 0, .024))
            elif config['id'] == 'tangseng':
                crown = tip + Vector((0, 0, .025))
                outer = [crown + Vector((.13 * math.cos(i * math.tau / 32), 0, .15 * math.sin(i * math.tau / 32))) for i in range(33)]
                F.tube('Nine-ring staff open crown', outer, .013, mats['gold'], bone, 6)
                for i in range(9):
                    a = i * math.tau / 9
                    center = crown + Vector((.143 * math.cos(a), -.013, .16 * math.sin(a)))
                    points = [center + Vector((.035 * math.cos(j * math.tau / 18), 0, .040 * math.sin(j * math.tau / 18))) for j in range(19)]
                    F.tube('Staff hollow hanging ring %d' % (i + 1), points, .006, mats['gold'], bone, 6)
                tip = crown + Vector((0, 0, .204))
            else:
                F.ellipsoid('Staff finial', tip, (.073, .035, .11), mats['gold'], bone)
                for i in range(3):
                    F.ellipsoid('Staff hanging ring', tip + Vector(((i - 1) * .085, 0, -.04)), (.04, .015, .042), mats['gold'], bone, 12, 7)
        if kind == 'flag':
            F.slab('Patrol flag cloth', grip + Vector((.15, 0, length - .18)), (.15, .01, .19), mats['main'], bone, .005)
        if kind in ('mic', 'microphone'):
            F.ellipsoid('Microphone grille', tip, (.049, .049, .066), mats['metal'], bone)
            for j in range(4):
                F.tube('Microphone grille stripe', [tip + Vector((-.039, -.04, (j - 1.5) * .019)), tip + Vector((.039, -.04, (j - 1.5) * .019))], .003, mats['dark'], bone, 4)
        if kind == 'flute':
            for j in range(5):
                F.ellipsoid('Flute finger hole', grip + Vector((0, -.021, .12 + j * .05)), (.007, .003, .007), mats['dark'], bone, 8, 5)
    elif kind == 'rake':
        top = grip + Vector((0, 0, 1.03))
        F.tube('Nine-tooth rake wooden shaft', [grip - Vector((0, 0, .43)), top], [.025, .020], mats['wood'], bone)
        F.tube('Nine-tooth rake crossbar', [top + Vector((-.335, 0, 0)), top + Vector((.335, 0, 0))], .024, mats['metal'], bone)
        for i in range(9):
            x = (i - 4) * .079
            F.tube('Rake forged hooked tooth %d' % (i + 1), [top + Vector((x, 0, 0)), top + Vector((x, 0, .15)),
                                                          top + Vector((x, -.024, .238)), top + Vector((x, -.052, .248))],
                   [.015, .013, .009, .004], mats['bright'], bone, 6)
        tip = top + Vector((0, -.052, .248))
    elif kind == 'fan':
        F.tube('Fan carved handle', [grip + Vector((0, 0, -.10)), grip + Vector((0, 0, .25))], .018, mats['wood'], bone)
        if config['id'] in ('guodegang', 'yuqian'):
            for i in range(9):
                a, b = (i - 4.5) * .15, (i - 3.5) * .15
                vertices = []
                for depth in (-.008, .006):
                    vertices.extend([tuple(grip + Vector((r * math.sin(angle), depth + (-.006 if i % 2 else .006), .19 + r * math.cos(angle))))
                                     for angle, r in ((a, .035), (a, .40), (b, .40), (b, .035))])
                F.mesh('Folding fan paper pleat', vertices, [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
                                                            (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], mats['white'], bone, False)
                F.tube('Folding fan bamboo rib', [grip + Vector((.035 * math.sin(a), -.016, .19 + .035 * math.cos(a))),
                                                grip + Vector((.40 * math.sin(a), -.016, .19 + .40 * math.cos(a)))], .004, mats['wood'], bone, 4)
        else:
            for i in range(9):
                a = (i - 4) * .15
                start = grip + Vector((.03 * math.sin(a), 0, .19))
                end = grip + Vector((.44 * math.sin(a), -.012, .19 + .40 * math.cos(a)))
                F.leaf('Fan feather', start, end, .038, mats['white'], bone, .005, .015)
        tip = grip + Vector((0, 0, .59))
    elif kind in ('gun', 'dualgun', 'pistol', 'rifle'):
        sides = [('R', -1)] if kind != 'dualgun' else [('R', -1), ('L', 1)]
        for side, sign in sides:
            g = Vector((sign * .51, -.14, .93))
            F.slab('Pistol handle.' + side, g, (.021, .027, .072), mats['dark'], 'hand.' + side, .008)
            F.slab('Pistol slide.' + side, g + Vector((0, -.067, .066)), (.034, .099, .024), mats['metal'], 'hand.' + side, .006)
            F.tube('Pistol barrel.' + side, [g + Vector((0, -.02, .06)), g + Vector((0, -.27 if kind == 'rifle' else -.18, .06))], .016, mats['dark'], 'hand.' + side)
        tip = grip + Vector((0, -.27 if kind == 'rifle' else -.18, .06))
    elif kind in ('book', 'document', 'keyboard', 'phone', 'bag', 'remote'):
        is_book = kind in ('book', 'document')
        center = grip + Vector((0, -.025, .10))
        w, h = (.115, .15) if is_book else (.060, .17) if kind == 'phone' else (.12, .11) if kind == 'bag' else (.27, .10)
        F.slab('Held prop · ' + kind, center, (w, .03, h), mats['main'] if is_book or kind == 'bag' else mats['dark'], bone, .014)
        if is_book:
            F.slab('Book pages', center + Vector((0, -.033, 0)), (w * .88, .009, h * .90), mats['white'], bone, .003)
            for i in range(4):
                F.slab('Book page rule', center + Vector((0, -.043, (i - 1.5) * .043)), (w * .63, .003, .002), mats['trim'], bone, 0)
        if kind == 'phone':
            F.tube('Phone antenna', [center + Vector((.035, 0, h)), center + Vector((.035, 0, h + .18))], .005, mats['dark'], bone)
            for i in range(3):
                F.slab('Phone dial key', center + Vector((0, -.033, (i - 1) * .039)), (.018, .006, .011), mats['trim'], bone, .003)
        if kind == 'bag':
            F.curved('Bag handle', [center + Vector((-.065, 0, h)), center + Vector((-.09, 0, h + .11)),
                                  center + Vector((.09, 0, h + .11)), center + Vector((.065, 0, h))], .014, mats['trim'], bone)
        if kind == 'keyboard':
            for row in range(3):
                for col in range(9):
                    F.slab('Keyboard sculpted key', center + Vector(((col - 4) * .047, -.035, (row - 1) * .047)),
                           (.018, .007, .017), mats['white'] if (col + row) % 3 else mats['trim'], bone, .004)
            F.slab('Keyboard space key', center + Vector((0, -.034, -.077)), (.11, .006, .010), mats['trim'], bone, .003)
        tip = center + Vector((0, -.03, h))
        if kind == 'keyboard':
            tip = center + Vector((-.27, -.036, .10))
    elif kind == 'needle':
        F.tube('Oversized sewing needle', [grip + Vector((0, 0, -.08)), grip + Vector((0, 0, .40))], [.009, .002], mats['bright'], bone)
        F.ellipsoid('Needle cushion', grip + Vector((0, 0, -.025)), (.066, .045, .065), mats['trim'], bone)
        tip = grip + Vector((0, 0, .40))
    elif kind == 'bottle':
        F.loft('Energy bottle', [(grip.x, grip.y, .86, .055, .055), (grip.x, grip.y, 1.07, .057, .057),
                               (grip.x, grip.y, 1.10, .026, .026), (grip.x, grip.y, 1.17, .025, .025)], mats['trim'], bone)
        F.slab('Energy bottle label', (grip.x, grip.y - .057, .983), (.037, .003, .042), mats['main'], bone, .004)
        tip = Vector((grip.x, grip.y, 1.17))
    elif kind in ('wrench', 'hammer', 'guitar'):
        F.tube('Tool handle', [grip - Vector((0, 0, .10)), grip + Vector((0, 0, .49))], .022, mats['wood'], bone)
        tip = grip + Vector((0, 0, .52))
        F.slab('Tool head', tip, (.13 if kind == 'hammer' else .075, .035, .044), mats['metal'], bone, .010)
        if kind == 'wrench':
            for sign in (-1, 1):
                F.tube('Open wrench jaw', [tip + Vector((sign * .04, 0, 0)), tip + Vector((sign * .08, 0, .065))], .023, mats['metal'], bone)
            tip += Vector((0, 0, .065))
        if kind == 'guitar':
            F.ellipsoid('Guitar resonator', grip + Vector((0, 0, -.03)), (.17, .048, .19), mats['wood'], bone)
            F.ellipsoid('Guitar sound hole', grip + Vector((0, -.05, .025)), (.039, .008, .039), mats['dark'], bone)
    elif kind in ('racket', 'pan'):
        F.tube('Racket or pan handle', [grip - Vector((0, 0, .07)), grip + Vector((0, 0, .28))], .023, mats['wood'], bone)
        center = grip + Vector((0, 0, .42))
        rim_points = [center + Vector((.17 * math.cos(i * math.tau / 28), 0, .21 * math.sin(i * math.tau / 28))) for i in range(29)]
        F.tube('Racket or pan rim', rim_points, .015 if kind == 'racket' else .023, mats['metal'], bone)
        if kind == 'pan':
            F.ellipsoid('Pan cooking surface', center, (.17, .025, .21), mats['dark'], bone)
        else:
            for i in range(-3, 4):
                x, z = i * .039, i * .048
                max_z = .21 * math.sqrt(max(0, 1 - (x / .17) ** 2))
                max_x = .17 * math.sqrt(max(0, 1 - (z / .21) ** 2))
                F.tube('Racket vertical string', [center + Vector((x, 0, -max_z)), center + Vector((x, 0, max_z))], .002, mats['white'], bone, 4)
                F.tube('Racket horizontal string', [center + Vector((-max_x, 0, z)), center + Vector((max_x, 0, z))], .002, mats['white'], bone, 4)
        tip = center + Vector((0, 0, .21))
    else:
        # Hand wraps give unarmed fighters a visible authored fist silhouette.
        for side, sign in [('R', -1), ('L', 1)]:
            F.loft('Wrist wrap.' + side, [(sign * .51, -.041, .982, .058, .048), (sign * .51, -.039, 1.035, .059, .049)], mats['trim'], 'hand.' + side)
        tip = Vector((-.51, -.13, .895))
        if config.get('gloves'):
            for side, sign in [('R', -1), ('L', 1)]:
                F.ellipsoid('Foam training glove.' + side, (sign * .51, -.085, .91), (.081, .068, .092), mats['trim'], 'hand.' + side)
                F.loft('Training glove cuff.' + side, [(sign * .51, -.04, .977, .069, .063), (sign * .51, -.04, 1.052, .069, .063)], mats['main'], 'hand.' + side)
            tip = Vector((-.51, -.085, .818))
    return bone, tip


REST = {'root': (0, 0, 0), 'crouch': .018, 'hip_yaw': -.035,
        'torso': (.015, 0, .04), 'head': (0, 0, -.020),
        'wrist.L': (.49, -.20, 1.10), 'wrist.R': (-.50, -.16, 1.07),
        'fingers.L': (0, -.2, -1), 'fingers.R': (0, -.08, -1)}


def action_knots(family, name):
    # At 620 ms all strikes reach their designed contact. The preceding stillness
    # and weight shift differ by family; contact is never an arbitrary frame guess.
    if family == 'knife':
        data = {
            'attack': ({'wrist.R': (-.52, .05, 1.40), 'torso': (-.04, 0, -.29), 'crouch': .045},
                       {'wrist.R': (-.13, -.54, 1.40), 'fingers.R': (.14, .92, -.38), 'torso': (.12, -.02, .33), 'wrist.L': (.30, -.19, 1.35)}),
            'heavy': ({'wrist.R': (-.23, -.03, 1.96), 'fingers.R': (0, -.5, -.85), 'torso': (-.13, 0, -.14), 'crouch': .07},
                      {'wrist.R': (-.19, -.53, 1.40), 'fingers.R': (0, .86, -.5), 'torso': (.21, 0, .13), 'crouch': .11}),
            'special': ({'wrist.R': (.11, -.02, 1.42), 'fingers.R': (.8, .30, -.45), 'wrist.L': (.28, -.31, 1.20), 'torso': (.03, 0, .48)},
                        {'wrist.R': (-.36, -.49, 1.40), 'fingers.R': (-.58, .77, -.26), 'torso': (.10, -.02, -.45), 'hip_yaw': -.12})}
    elif family == 'orb':
        data = {
            'attack': ({'wrist.R': (-.47, .04, 1.15), 'torso': (-.05, 0, -.24), 'crouch': .06},
                       {'wrist.R': (-.20, -.57, 1.48), 'fingers.R': (0, -.76, -.52), 'torso': (.13, 0, .24), 'wrist.L': (.27, -.27, 1.40)}),
            'heavy': ({'wrist.R': (-.31, -.07, 1.86), 'wrist.L': (.26, -.09, 1.80), 'torso': (-.09, 0, -.11), 'crouch': .06},
                      {'wrist.R': (-.12, -.54, 1.50), 'wrist.L': (.23, -.41, 1.45), 'fingers.R': (0, -.35, -1), 'torso': (.23, 0, .08), 'crouch': .11}),
            'special': ({'wrist.R': (-.33, .07, 1.55), 'wrist.L': (.25, -.10, 1.68), 'fingers.R': (0, .2, -1), 'torso': (-.08, 0, -.38)},
                        {'wrist.R': (-.14, -.58, 1.53), 'wrist.L': (.30, -.37, 1.40), 'fingers.R': (0, -.9, -.2), 'torso': (.15, 0, .34), 'crouch': .08})}
    elif family == 'staff':
        data = {
            'attack': ({'wrist.R': (-.50, .05, 1.41), 'fingers.R': (-.2, -.15, -1), 'torso': (-.06, 0, -.30)},
                       {'wrist.R': (-.11, -.53, 1.41), 'fingers.R': (.12, .91, -.40), 'wrist.L': (.21, -.35, 1.30), 'torso': (.12, -.04, .30)}),
            'heavy': ({'wrist.R': (-.20, -.10, 1.99), 'wrist.L': (.19, -.12, 1.88), 'torso': (-.14, 0, -.11)},
                      {'wrist.R': (-.17, -.51, 1.41), 'fingers.R': (0, .83, -.55), 'wrist.L': (.16, -.40, 1.34), 'torso': (.21, 0, .13), 'crouch': .10}),
            'special': ({'wrist.R': (.05, -.05, 1.44), 'fingers.R': (.84, .22, -.43), 'wrist.L': (.42, -.14, 1.43), 'torso': (0, 0, .49)},
                        {'wrist.R': (-.43, -.43, 1.43), 'fingers.R': (-.70, .63, -.27), 'wrist.L': (.28, -.27, 1.34), 'torso': (.13, -.07, -.52), 'hip_yaw': -.14})}
    else:
        data = {
            'attack': ({'wrist.R': (-.45, -.06, 1.37), 'wrist.L': (.32, -.18, 1.55), 'torso': (-.02, 0, -.20)},
                       {'wrist.R': (-.14, -.60, 1.52), 'wrist.L': (.26, -.27, 1.52), 'fingers.R': (0, -.97, -.15), 'torso': (.12, 0, .23)}),
            'heavy': ({'wrist.R': (-.45, .06, 1.05), 'wrist.L': (.26, -.19, 1.49), 'crouch': .12, 'torso': (.12, -.03, -.34)},
                      {'wrist.R': (-.09, -.53, 1.65), 'wrist.L': (.26, -.23, 1.45), 'fingers.R': (0, -.9, -.25), 'torso': (-.04, 0, .40), 'crouch': .04}),
            'special': ({'wrist.R': (-.28, -.06, 1.56), 'wrist.L': (.30, -.08, 1.55), 'torso': (-.11, 0, -.09), 'crouch': .085},
                        {'wrist.R': (-.18, -.56, 1.58), 'wrist.L': (.18, -.55, 1.57), 'fingers.R': (0, -.95, -.14), 'fingers.L': (0, -.95, -.14), 'torso': (.20, 0, .08), 'crouch': .11})}
    windup, contact = [REST | value for value in data[name]]
    contact['root'] = (0, -.04 if name == 'attack' else -.065, 0)
    follow = dict(contact)
    follow['wrist.R'] = (contact['wrist.R'][0] + .035, contact['wrist.R'][1] + .03, contact['wrist.R'][2] - .055)
    return [(0, REST), (.20, windup), (.32, windup), (CONTACT, contact), (.50, follow), (.68, F.mix_pose(contact, REST, .50)), (1, REST)]


def pose_at(family, name, t):
    if name in ('attack', 'heavy', 'special'):
        knots = action_knots(family, name)
        for (ta, a), (tb, b) in zip(knots, knots[1:]):
            if ta <= t <= tb:
                u = (t - ta) / (tb - ta)
                return F.mix_pose(a, b, u * u * (3 - 2 * u))
    if name == 'idle':
        return REST | {'crouch': .018 + .007 * math.sin(t * math.tau),
                       'torso': (.015 + .008 * math.sin(t * math.tau), .004 * math.sin(t * math.tau), .04),
                       'head': (.006 * math.sin(t * math.tau), 0, -.020)}
    if name == 'guard':
        target = REST | {'crouch': .10, 'torso': (.07, 0, -.09), 'head': (.075, 0, .02),
                         'wrist.L': (.22, -.35, 1.66), 'wrist.R': (-.22, -.38, 1.55)}
        return F.mix_pose(REST, target, max(0, min(1, t / .16, (1 - t) / .22)))
    if name == 'hurt':
        target = REST | {'root': (.023, .09, 0), 'crouch': .085, 'torso': (-.20, .10, -.12),
                         'head': (-.14, -.08, .08), 'wrist.L': (.54, -.05, 1.13), 'wrist.R': (-.51, .05, 1.07)}
        return F.mix_pose(REST, target, min(1, t / .11) * (1 - t) ** 1.15)
    target = REST | {'crouch': .024, 'torso': (-.025, 0, .055 * math.sin(t * math.tau)),
                     'wrist.L': (.22, -.06, 2.11), 'wrist.R': (-.42, -.08, 1.46),
                     'head': (-.04, 0, .05 * math.sin(t * math.tau)), 'fingers.L': (0, .4, -.8)}
    return F.mix_pose(REST, target, max(0, min(1, t / .17, (1 - t) / .17)))


def animate(armature, family):
    durations = {'idle': 200, 'attack': 145, 'heavy': 145, 'guard': 145, 'special': 145, 'hurt': 90, 'victory': 200}
    armature.animation_data_create()
    for name, frames in durations.items():
        action = bpy.data.actions.new('AN_shared_' + family + '_' + name)
        armature.animation_data.action = action
        times = {i / frames for i in range(frames + 1)} | {CONTACT}
        for t in sorted(times):
            F.pose(armature, pose_at(family, name, t))
            for bone in armature.pose.bones:
                bone.keyframe_insert('rotation_quaternion', frame=t * frames, group=bone.name)
                bone.keyframe_insert('location', frame=t * frames, group=bone.name)
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag = strip.channelbag(slot)
                    if bag:
                        for curve in bag.fcurves:
                            for key in curve.keyframe_points:
                                key.interpolation = 'BEZIER'
                                key.handle_left_type = key.handle_right_type = 'AUTO_CLAMPED'
        track = armature.animation_data.nla_tracks.new()
        track.name = name
        strip = track.strips.new(name, 0, action)
        strip.action_frame_start, strip.action_frame_end = 0, frames
        track.mute = True
    armature.animation_data.action = None
    for bone in armature.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)


def export_motion(family):
    clean_scene()
    armature = F.rig('motion_' + family)
    animate(armature, family)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(filepath=str(MOTION_OUT / (family + '.glb')), export_format='GLB', use_selection=True,
                              export_animations=True, export_animation_mode='NLA_TRACKS', export_skins=True,
                              export_force_sampling=True, export_nla_strips=True)
    print('MOTION', family, (MOTION_OUT / (family + '.glb')).stat().st_size, flush=True)


def motion_family(kind):
    for family, types in FAMILY_TYPES.items():
        if kind.lower() in types:
            return family
    return 'brawler'


def measured_contacts(armature, bone, point, family):
    local = armature.data.bones[bone].matrix_local.inverted() @ point
    result = {}
    for action, event in [('attack', 'strike'), ('heavy', 'heavy'), ('special', 'special')]:
        F.pose(armature, pose_at(family, action, CONTACT))
        bpy.context.view_layer.update()
        p = armature.pose.bones[bone].matrix @ local
        # Blender Z-up to the same glTF Y-up coordinates used by Three.js.
        result[event] = [round(p.x, 4), round(p.z, 4), round(-p.y, 4)]
    for b in armature.pose.bones:
        b.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    return result


def make_character(item, save_blend=False):
    clean_scene()
    identifier = item['id']
    config = configuration(item)
    seed = seed_for(identifier)
    mats = palette(identifier, config)
    body(config, mats, seed)
    head(config, mats, seed)
    before_weapon = set(F.parts)
    bone, point = weapon(config, mats)
    D.prop_details(config, mats)
    gear = [obj for obj in F.parts if obj not in before_weapon]
    F.tag_face_parts()
    meshes = D.assemble(identifier, gear)
    armature = F.rig(identifier)
    triangles = 0
    for mesh in meshes:
        D.skin_weights(mesh)
        modifier = mesh.modifiers.new('Skeleton', 'ARMATURE')
        modifier.object = armature
        mesh.parent = armature
        mesh.data.calc_loop_triangles()
        triangles += len(mesh.data.loop_triangles)
    assert triangles <= 65000, (identifier, triangles)
    family = motion_family(config['weaponType'])
    contacts = measured_contacts(armature, bone, point, family)
    bpy.ops.object.select_all(action='DESELECT')
    for mesh in meshes:
        mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(filepath=str(OUT / (identifier + '.glb')), export_format='GLB', use_selection=True,
                              export_animations=False, export_skins=True, export_morph=True, export_morph_normal=False)
    size = (OUT / (identifier + '.glb')).stat().st_size
    assert size <= 5 * 1024 * 1024, (identifier, size)
    if save_blend:
        # Editable character file includes its shared clips for posing and revision.
        animate(armature, family)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'art' / (identifier + '.blend')))
    print('CHARACTER', identifier, triangles, size, family, json.dumps(contacts), flush=True)
    return contacts, family


def read_roster(config_path=None):
    if config_path:
        data = json.loads(Path(config_path).read_text())
    else:
        script = """import * as mod from './shared/roster.js';
        const value=mod.ROSTER??mod.roster??mod.CHARACTER_ROSTER??Object.values(mod).find(Array.isArray);
        console.log(JSON.stringify(Array.isArray(value)?value:Object.values(value??{})));"""
        node = shutil.which('node') or '/opt/homebrew/bin/node'
        data = json.loads(subprocess.check_output([node, '--input-type=module', '-e', script], cwd=ROOT, text=True))
    if isinstance(data, dict):
        data = data.get('characters', data.get('roster', list(data.values())))
    return [item for item in data if isinstance(item, dict) and item.get('id') not in ('ikun', 'wang', 'lubu')]


def write_contacts(contacts, motions, visuals):
    path = ROOT / 'shared' / 'roster-contacts.js'
    # Preserve other measured fighters when regenerating just one editable model.
    if path.exists():
        text = path.read_text()
        for name, target in [('ROSTER_CONTACT', contacts), ('ROSTER_MOTIONS', motions), ('ROSTER_VISUAL', visuals)]:
            line = next((line for line in text.splitlines() if line.startswith('export const ' + name + ' = ')), None)
            if line:
                previous = json.loads(line.split(' = ', 1)[1].rstrip(';'))
                previous.update(target)
                target.clear()
                target.update(previous)
    output = '// Generated by tools/make_roster.py; measured at exactly 620 ms.\n'
    output += 'export const ROSTER_CONTACT = ' + json.dumps(contacts, ensure_ascii=False, separators=(',', ':')) + ';\n'
    output += 'export const ROSTER_MOTIONS = ' + json.dumps(motions, ensure_ascii=False, separators=(',', ':')) + ';\n'
    output += 'export const ROSTER_VISUAL = ' + json.dumps(visuals, ensure_ascii=False, separators=(',', ':')) + ';\n'
    output += 'export const MOTION_FILES = ' + json.dumps({family: '/assets/motions/' + family + '.glb' for family in FAMILY_TYPES}, separators=(',', ':')) + ';\n'
    path.write_text(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', help='One fighter ID; comma-separated IDs are also accepted')
    parser.add_argument('--save-blend', action='store_true')
    parser.add_argument('--config', help='Optional JSON roster; default imports shared/roster.js')
    parser.add_argument('--skip-motions', action='store_true', help='Keep the existing four motion libraries')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    items = read_roster(args.config)
    if args.only:
        wanted = set(args.only.split(','))
        items = [item for item in items if item['id'] in wanted]
        assert {item['id'] for item in items} == wanted, 'Unknown roster ID'
    if not args.skip_motions:
        for family in FAMILY_TYPES:
            export_motion(family)
    contacts, motions, visuals = {}, {}, {}
    for index, item in enumerate(items, 1):
        measured, family = make_character(item, args.save_blend)
        contacts[item['id']], motions[item['id']] = measured, family
        visuals[item['id']] = visual_metadata(item)
        write_contacts(contacts, motions, visuals)
        print('PROGRESS', index, '/', len(items), flush=True)
    write_contacts(contacts, motions, visuals)
    print('DONE', len(items), 'independent fighters; four shared motion libraries', flush=True)


if __name__ == '__main__':
    main()
