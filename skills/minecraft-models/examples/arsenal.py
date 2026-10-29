"""
Example spec: one of each item style plus a full armor set.

    python scripts/build.py examples/arsenal.py --out out/arsenal --targets all
"""
from mcmodel import *

NAMESPACE = 'demo'
TITLE = 'Demo Arsenal'

# Ramps go dark -> light. Pick 2-3 stops; 8 colors are interpolated.
steel = material('metal', ramp('#262c3a', '#7d8aa3', '#eef3ff'))
ember = material('energy', ramp('#3a0a00', '#ff5a1a', '#ffe08a'), glow=12)
leather = material('grip', ramp('#24130a', '#7a4a2a'))
gold = material('trim', ramp('#4a2c05', '#d9a520', '#fff1a8'))
ruby = material('gem', ramp('#3a0010', '#e0204a', '#ffc0d0'), pulse=True, glow=10)
oak = material('wood', ramp('#3b2414', '#a0703f'))
glass = material('orb', ramp('#5a1800', '#ff8a2a', '#fff2b0'), glow=15)
cushion = material('cloth', ramp('#3a0a14', '#a8243c'))
MATS = {'steel': steel, 'ember': ember, 'leather': leather, 'gold': gold, 'ruby': ruby, 'oak': oak,
        'glass': glass, 'cushion': cushion}


def ember_sword():
    # Built standing up: tip toward +y, pommel at the bottom. 'handheld' tilts it like a vanilla sword.
    return Item('weapons/ember_sword', [
        box('blade', (8, 17, 8), (2.6, 16, 1.0), 'steel'),
        box('core', (8, 17, 8), (0.8, 14.5, 1.2), 'ember'),
        box('tip', (8, 25.2, 8), (1.84, 1.84, 1.0), 'steel', r=(0, 0, 45)),
        box('guard', (8, 8.4, 8), (8, 1.6, 2), 'gold'),
        box('ruby', (8, 8.4, 8), (1.6, 1.6, 2.4), 'ruby'),
        box('grip', (8, 4.8, 8), (1.6, 5.6, 1.6), 'leather'),
        box('pommel', (8, 1.4, 8), (2.4, 1.8, 2.4), 'gold'),
    ], MATS, style='handheld', base='diamond_sword', name='Ember Sword')


def ember_pickaxe():
    head = (curve('head', arc((8, 20), 7.5, 90, 18, 4), [3.0, 1.4], 1.8, 'steel')
            + curve('head', arc((8, 20), 7.5, 90, 162, 4), [3.0, 1.4], 1.8, 'steel'))
    return Item('tools/ember_pickaxe', head + [
        box('shaft', (8, 13, 8), (1.6, 24, 1.6), 'oak'),
        box('collar', (8, 26.6, 8), (2.6, 2.4, 2.6), 'gold'),
        box('core', (8, 27.4, 8), (1.2, 1.2, 2.8), 'ember'),
    ], MATS, style='handheld', base='diamond_pickaxe', name='Ember Pickaxe')


def ember_pistol():
    # Side profile, barrel toward +x; grip=(x, y) is where the hand holds it.
    return Item('weapons/ember_pistol', [
        box('slide', (9.5, 9.2, 8), (11, 3, 2.4), 'steel'),
        box('barrel', (16.5, 9.6, 8), (3.4, 1.6, 1.6), 'steel'),
        box('coil', (10, 9.2, 8), (6, 1.0, 2.6), 'ember'),
        box('grip', (5, 5, 8), (2.6, 6, 2.2), 'leather', r=(0, 0, 22.5)),
        box('trigger_guard', (7.6, 6.6, 8), (2.4, 0.6, 1.2), 'gold'),
    ], MATS, style='gun', grip=(5, 4), base='iron_horse_armor', name='Ember Pistol')


def crown():
    # Worn on the head: center (8, 8, 8) is the head center; the head is about 12.8 units wide; front is -z.
    parts = [box('band_front', (8, 15.2, 1.4), (13.6, 2.4, 0.8), 'gold'),
             box('band_back', (8, 15.2, 14.6), (13.6, 2.4, 0.8), 'gold'),
             box('band_left', (1.4, 15.2, 8), (0.8, 2.4, 12.4), 'gold'),
             box('band_right', (14.6, 15.2, 8), (0.8, 2.4, 12.4), 'gold'),
             box('gem', (8, 15.2, 0.9), (2, 2, 0.6), 'ruby')]
    for x in (3.5, 8, 12.5):
        parts += [box('point', (x, 17.2, 1.4), (1.3, 1.3, 0.8), 'gold', r=(0, 0, 45)),
                  box('point', (x, 17.2, 14.6), (1.3, 1.3, 0.8), 'gold', r=(0, 0, 45))]
    return Item('wearables/ember_crown', parts, MATS, style='helmet', base='golden_helmet', name='Ember Crown')


def lantern():
    parts = [box('cap', (8, 13, 8), (6, 1.4, 6), 'steel'), box('base', (8, 3, 8), (6, 1.4, 6), 'steel'),
             box('flame', (8, 8, 8), (3.4, 5.6, 3.4), 'glass'),
             box('handle', (8, 15.4, 8), (4, 0.8, 0.8), 'gold'),
             box('handle', (6.4, 14.4, 8), (0.8, 2, 0.8), 'gold'), box('handle', (9.6, 14.4, 8), (0.8, 2, 0.8), 'gold')]
    for x in (5.6, 10.4):
        for z in (5.6, 10.4):
            parts.append(box('post', (x, 8, z), (0.8, 9, 0.8), 'steel'))
    return Item('decor/ember_lantern', parts, MATS, style='object', base='paper', name='Ember Lantern')


def chair():
    # Furniture is drawn exactly as built on an ItemDisplay: the block spans 0..16, floor at y = 0.
    parts = [box('seat', (8, 7.6, 8), (12, 1.6, 12), 'oak'), box('cushion', (8, 8.8, 8.6), (10.8, 0.9, 10), 'cushion'),
             box('back', (8, 14.6, 2.8), (12, 11, 1.4), 'oak'), box('back_cushion', (8, 14.6, 3.7), (9.6, 8, 0.6), 'cushion')]
    for x in (3, 13):
        for z in (3, 13):
            parts.append(box('leg', (x, 3.4, z), (1.6, 6.8, 1.6), 'oak'))
    return Item('furniture/ember_chair', parts, MATS, style='furniture', base='paper', name='Ember Chair')


def armor():
    """The worn look (ArmorSet) plus four inventory pieces that point at it with wears=."""
    worn = ArmorSet('ember', ramp('#1c1f2a', '#6b7894', '#f0f4ff'), accent=ramp('#5a1800', '#ff8a2a', '#fff2b0'))
    pieces = {
        'helmet': [box('shell', (8, 9, 8), (9, 7, 9), 'steel'), box('crest', (8, 13.2, 8), (1.4, 2.4, 8), 'ember')],
        'chestplate': [box('torso', (8, 8, 8), (9, 10, 4.5), 'steel'), box('core', (8, 9, 5.6), (2, 2, 0.6), 'ember'),
                       box('shoulder', (3.2, 12, 8), (3.4, 2.6, 5), 'steel'),
                       box('shoulder', (12.8, 12, 8), (3.4, 2.6, 5), 'steel')],
        'leggings': [box('belt', (8, 13, 8), (9, 2, 4.5), 'gold'), box('leg', (5.7, 7, 8), (3.8, 10, 4), 'steel'),
                     box('leg', (10.3, 7, 8), (3.8, 10, 4), 'steel')],
        'boots': [box('boot', (5.2, 5, 8), (4, 5, 4.6), 'steel'), box('boot', (10.8, 5, 8), (4, 5, 4.6), 'steel'),
                  box('toe', (5.2, 3.2, 5.4), (4, 1.6, 1.6), 'gold'), box('toe', (10.8, 3.2, 5.4), (4, 1.6, 1.6), 'gold')],
    }
    items = [Item('armor/ember_%s' % piece, parts, MATS, style='object', wears=('ember', piece),
                  name='Ember %s' % piece.title()) for piece, parts in pieces.items()]
    return [worn] + items


MODELS = [ember_sword(), ember_pickaxe(), ember_pistol(), crown(), lantern(), chair()] + armor()
