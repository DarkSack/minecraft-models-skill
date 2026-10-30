"""
Example spec: big and heavy. A greatsword and a warhammer that look huge in the hand, a bulky
armor set (HD layers, a 3D helmet on both editions, 3D pauldrons, knee guards and toe caps on
Bedrock) and a colossus about 7 blocks tall whose wide bones are split for the loaders.

    python scripts/build.py examples/titans.py --out out/titans --targets vanilla,geyser,fmm
"""
from mcmodel import *

NAMESPACE = 'titans'
TITLE = 'Titans'

steel = material('metal', ramp('#1a1e26', '#68748a', '#e6ecf6'))
edge = material('metal', ramp('#7d899c', '#dfe7f2', '#ffffff'))
plating = material('plate', ramp('#14161c', '#4a5262', '#c9d2e0'))
gold = material('trim', ramp('#3a2406', '#c68e24', '#fff0b0'))
leather = material('grip', ramp('#1e0f08', '#6a3c22'))
horn = material('bone', ramp('#3a3024', '#bfb092', '#f4ecd8'))
rune = material('energy', ramp('#3a0800', '#ff6a18', '#ffe6a0'), glow=12)
core = material('orb', ramp('#5a1000', '#ff7a18', '#fff0a0'), glow=15)
stone = material('cracked', ramp('#141216', '#4c464e', '#8a828c'), energy=ramp('#5a1000', '#ff6a10', '#ffe080'),
                 every=160)
crystal = material('crystal', ramp('#3a0a00', '#ff7a2a', '#ffe8c0'), glow=13)
MATS = {'steel': steel, 'edge': edge, 'plating': plating, 'gold': gold, 'leather': leather, 'horn': horn,
        'rune': rune, 'core': core, 'stone': stone, 'crystal': crystal}


def greatsword():
    # Built at full size, tip up (58 units): the build fits it into Java's box and hand_scale makes it
    # 1.7 times a vanilla sword in the hand.
    parts = (blade('blade', (8, 8), (8, 50), 7, 1.6, 'steel', edge='edge', segments=5)
             + [box('fuller', (8, 25, 8), (1.2, 28, 1.8), 'rune')]
             + bevel('guard', (8, 6.5, 8), (16, 3, 3.4), 'gold', edge=0.5)
             + [box('guard_tip', (0.4, 7, 8), (2.4, 2.4, 2.8), 'gold', r=(0, 0, 45)),
                box('guard_tip', (15.6, 7, 8), (2.4, 2.4, 2.8), 'gold', r=(0, 0, 45)),
                box('gem', (8, 6.5, 8), (2.4, 2.4, 3.8), 'core')]
             + tube('grip', (8, -1, 8), 11, 1.3, 'leather', axis='y')
             + bevel('pommel', (8, -7.6, 8), (3.6, 3, 3.6), 'gold', edge=0.5))
    return Item('weapons/titan_greatsword', parts, MATS, style='handheld', base='netherite_sword',
                hand_scale=1.7, name='Titan Greatsword')


def warhammer():
    parts = (tube('handle', (8, 12, 8), 34, 1.1, 'leather', axis='y')
             + bevel('head', (8, 31, 8), (20, 9, 9), 'plating', edge=1.0)
             + bevel('face', (-2.6, 31, 8), (2, 10.4, 10.4), 'steel', edge=0.6)
             + bevel('face', (18.6, 31, 8), (2, 10.4, 10.4), 'steel', edge=0.6)
             + [box('band', (8, 31, 8), (20.2, 2, 9.4), 'rune'),
                box('spike', (8, 37, 8), (2.4, 4, 2.4), 'steel'),
                box('spike_tip', (8, 39.4, 8), (1.6, 1.6, 1.6), 'steel', r=(0, 0, 45))]
             + rivets('rivet', (1, 34.6, 3.4), (15, 34.6, 3.4), 5, 'gold', size=0.7)
             + rivets('rivet', (1, 27.4, 3.4), (15, 27.4, 3.4), 5, 'gold', size=0.7))
    for y in (-2, 2, 6):
        parts += tube('wrap', (8, y, 8), 1, 1.4, 'gold', axis='y')
    parts += bevel('pommel', (8, -5.8, 8), (3.4, 2.6, 3.4), 'gold', edge=0.5)
    return Item('weapons/titan_warhammer', parts, MATS, style='handheld', base='netherite_axe',
                hand_scale=1.6, density=3, name='Titan Warhammer')


def armor():
    """HD worn layers + 3D pieces (Bedrock). The helmet is a 3D model on both editions instead."""
    pauldron = (bevel('pauldron', (6.4, 23.6, 0), (6.6, 3.2, 7), 'plating', edge=0.5)
                + [box('pauldron_lip', (7.6, 21.4, 0), (4.4, 1.6, 6.4), 'plating'),
                   box('spike', (6.6, 26.4, 0), (1.4, 2.8, 1.4), 'gold'),
                   box('spike', (6.6, 26.4, -2.4), (1.2, 2.2, 1.2), 'gold'),
                   box('spike', (6.6, 26.4, 2.4), (1.2, 2.2, 1.2), 'gold')]
                + rivets('rivet', (8.6, 22.2, -3.2), (8.6, 22.2, 3.2), 3, 'gold', size=0.5))
    chest = (bevel('breastplate', (0, 19, -3.2), (9, 9, 1.4), 'plating', edge=0.4)
             + [box('core', (0, 20, -4.1), (2.4, 2.4, 0.8), 'core')]
             + tube('vent', (2.4, 20, 3.4), 6, 0.8, 'steel', axis='y')
             + tube('vent', (-2.4, 20, 3.4), 6, 0.8, 'steel', axis='y'))
    knee = bevel('knee', (2, 6.8, -2.8), (4.6, 3.4, 1.4), 'plating', edge=0.4) + [
        box('tasset', (2.2, 10.6, -2.6), (4.4, 3, 0.8), 'plating')]
    toe = bevel('toe', (2, 1.2, -2.6), (4.8, 2.4, 3), 'plating', edge=0.4) + [
        box('heel_spur', (2, 1.6, 2.6), (1, 1, 1.6), 'gold')]
    worn = ArmorSet('titan', ramp('#14161c', '#4a5262', '#c9d2e0'), accent=ramp('#5a1000', '#ff7a18', '#fff0a0'),
                    detail=2, mats=MATS, extras={
                        'chestplate': {'body': chest, 'right_arm': pauldron,
                                       'left_arm': [mirror(p) for p in pauldron]},
                        'leggings': {'right_leg': knee, 'left_leg': [mirror(p) for p in knee]},
                        'boots': {'right_leg': toe, 'left_leg': [mirror(p) for p in toe]}})
    # Worn on the head as a 3D model (style 'helmet', no wears): center (8, 8, 8) = head center, front -z.
    helm = (bevel('shell', (8, 9, 8), (14.4, 14.4, 14.4), 'plating', edge=1.0)
            + [box('visor', (8, 8.4, 0.5), (9, 1.2, 0.6), 'core'),
               box('crest', (8, 17, 8), (1.6, 2.4, 12), 'rune'),
               bar('horn', (1.2, 12), (-3.4, 16.6), 2.4, 2.4, 'horn'),
               bar('horn', (-3.4, 16.6), (-4.2, 21), 1.5, 1.5, 'horn'),
               bar('horn', (14.8, 12), (19.4, 16.6), 2.4, 2.4, 'horn'),
               bar('horn', (19.4, 16.6), (20.2, 21), 1.5, 1.5, 'horn')]
            + rivets('rivet', (2, 3, 0.6), (14, 3, 0.6), 4, 'gold', size=0.6))
    pieces = [Item('armor/titan_helmet', helm, MATS, style='helmet', base='netherite_helmet', density=3,
                   name='Titan Helm')]
    inventory = {
        'chestplate': bevel('torso', (8, 8, 8), (10, 10, 5), 'plating', edge=0.6)
        + [box('core', (8, 9, 5.3), (2.4, 2.4, 0.6), 'core')]
        + bevel('pauldron', (2.4, 12.6, 8), (4.4, 3, 6), 'plating', edge=0.4)
        + bevel('pauldron', (13.6, 12.6, 8), (4.4, 3, 6), 'plating', edge=0.4),
        'leggings': [box('belt', (8, 13, 8), (9.6, 2, 5), 'gold'), box('leg', (5.6, 7, 8), (4, 10, 4.4), 'plating'),
                     box('leg', (10.4, 7, 8), (4, 10, 4.4), 'plating'), box('knee', (5.6, 7, 5.6), (3.6, 3, 0.8), 'steel'),
                     box('knee', (10.4, 7, 5.6), (3.6, 3, 0.8), 'steel')],
        'boots': bevel('boot', (5, 5, 8), (4.4, 5, 5), 'plating', edge=0.4)
        + bevel('boot', (11, 5, 8), (4.4, 5, 5), 'plating', edge=0.4)
        + [box('toe', (5, 3.2, 5.2), (4.4, 1.6, 1.6), 'gold'), box('toe', (11, 3.2, 5.2), (4.4, 1.6, 1.6), 'gold')],
    }
    pieces += [Item('armor/titan_%s' % piece, parts, MATS, style='object', wears=('titan', piece),
                    base='netherite_' + piece, name='Titan %s' % piece.title()) for piece, parts in inventory.items()]
    return [worn] + pieces


def colossus():
    # Designed at ~2.3 blocks and built 3x. Keep every cube under 16 units here (48 after scale):
    # the build splits wide bones into child bones, but it cannot split a single cube.
    head = Bone('h_head', (0, 35, -2), [cube('head', (0, 38.5, -4), (9, 7, 8), 'stone'),
                                         cube('eye', (2.2, 39, -8.05), (1.8, 1, 0.2), 'core'),
                                         cube('eye', (-2.2, 39, -8.05), (1.8, 1, 0.2), 'core')])
    arm_r, arm_l = pair('arm', (13, 33, 0), [cube('shoulder', (14.5, 35, 0), (9, 5, 10), 'stone'),
                                             cube('crystal', (15, 39, 0), (3, 6, 3), 'crystal', 'z', -22.5),
                                             cube('arm', (14.5, 27, 0), (7, 12, 8), 'stone'),
                                             cube('fist', (14.5, 16, 0), (9, 9, 10), 'stone')])
    body = Bone('body', (0, 16, 0), [cube('chest', (5.5, 28, 0), (11, 14, 12), 'stone'),
                                     cube('chest', (-5.5, 28, 0), (11, 14, 12), 'stone'),
                                     cube('core', (0, 29, -6.2), (5, 5, 1), 'core'),
                                     cube('belly', (0, 19, 0), (14, 6, 9), 'stone'),
                                     cube('crystal', (4, 37, 4), (3, 7, 3), 'crystal', 'z', 22.5),
                                     cube('crystal', (-4, 37, 4), (3, 7, 3), 'crystal', 'z', -22.5),
                                     cube('crystal', (0, 38, 5), (3, 9, 3), 'crystal')],
                [head, arm_r, arm_l, Bone('tag_name', (0, 48, 0))])
    leg_r, leg_l = pair('leg', (6, 16, 0), [cube('leg', (6, 8.6, 0), (8, 14.8, 8), 'stone'),
                                            cube('foot', (6, 1.2, -1), (9, 2.4, 10), 'stone')])
    root = Bone('root', (0, 0, 0), [], [body, leg_r, leg_l])
    slam = [(0, (0, 0, 0)), (0.7, (-150, 0, 0)), (1.0, (-10, 0, 0)), (1.6, (0, 0, 0))]
    anims = {
        'idle': Anim(4.0, tracks={'body': {'rot': wave(4.0, (2, 0, 0))}, 'h_head': {'rot': wave(4.0, (0, 12, 0))}}),
        'walk': Anim(2.4, tracks={'leg_r': {'rot': wave(2.4, (18, 0, 0))}, 'leg_l': {'rot': wave(2.4, (18, 0, 0), phase=0.5)},
                                  'arm_r': {'rot': wave(2.4, (14, 0, 0), phase=0.5)}, 'arm_l': {'rot': wave(2.4, (14, 0, 0))},
                                  'body': {'rot': wave(2.4, (0, 0, 3))}}),
        'attack': Anim(1.6, 'once', {'arm_r': {'rot': slam}, 'arm_l': {'rot': slam},
                                     'body': {'rot': [(0, (0, 0, 0)), (0.7, (-8, 0, 0)), (1.0, (14, 0, 0)), (1.6, (0, 0, 0))]}}),
        'death': Anim(2.0, 'hold', {'root': {'rot': [(0, (0, 0, 0)), (1.6, (80, 0, 0))]}}),
        'spawn': Anim(2.0, 'once', {'root': {'pos': [(0, (0, -40, 0)), (2.0, (0, 0, 0))]}}),
    }
    return Creature('colossus', [root], MATS, hitbox=(0.9, 2.3), anims=anims, scale=3.0)


MODELS = [greatsword(), warhammer()] + armor() + [colossus()]
