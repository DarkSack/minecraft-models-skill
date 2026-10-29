"""
Example spec: a mob and a boss for FreeMinecraftModels / ModelEngine / BetterModel.

    python scripts/build.py examples/bestiary.py --out out/bestiary --targets fmm,modelengine,bettermodel

Creatures face -z (north), feet at y = 0, 16 units = 1 block. The creature's right side is +x.
Animation values use Blockbench's convention: arm forward = negative x rotation, lean forward
= positive x, position z = -2 moves forward.
"""
from mcmodel import *

NAMESPACE = 'demo'
TITLE = 'Demo Bestiary'

iron = material('metal', ramp('#1c2029', '#6c7790', '#dfe6f5'))
tabard = material('cloth', ramp('#2a0a10', '#8a1f2e'), hem=ramp('#4a2c05', '#d9a520'))
eyes = material('eye', ramp('#300000', '#ff3a1a', '#ffe0a0'), glow=15)
rock = material('cracked', ramp('#121012', '#4a4044', '#7a7078'), energy=ramp('#5a1000', '#ff6a10', '#ffe080'),
                every=160)    # fewer cracks: big faces would turn into lava
core = material('orb', ramp('#5a1000', '#ff7a18', '#fff0a0'), glow=15)


def knight():
    head = Bone('h_head', (0, 24, 0), [                       # h_ = follows where the mob looks
        cube('helm', (0, 28, 0), (8, 8, 8), 'iron'),
        cube('crest', (0, 32.8, 0.5), (1, 1.6, 7), 'tabard'),
        cube('eye', (1.8, 28.4, -4.05), (1.6, 0.8, 0.2), 'eyes'),
        cube('eye', (-1.8, 28.4, -4.05), (1.6, 0.8, 0.2), 'eyes')])
    arm_r, arm_l = pair('arm', (6, 22, 0), [cube('arm', (6, 16, 0), (4, 12, 4), 'iron')])
    arm_r.parts.append(cube('blade', (6, 11, -7), (0.8, 1.6, 13), 'iron'))     # sword in the right hand only
    body = Bone('body', (0, 12, 0), [cube('torso', (0, 18, 0), (8, 12, 4), 'iron'),
                                     cube('tabard', (0, 15, -2.2), (6, 9, 0.4), 'tabard')],
                [head, arm_r, arm_l, Bone('tag_name', (0, 35, 0))])                # empty bone: nametag anchor
    leg_r, leg_l = pair('leg', (2, 12, 0), [cube('leg', (2, 6, 0), (4, 12, 4), 'iron')])
    root = Bone('root', (0, 0, 0), [], [body, leg_r, leg_l])                       # lets death/spawn move it all

    anims = {
        'idle': Anim(2.0, tracks={'body': {'pos': wave(2.0, (0, 0.3, 0))},
                                  'arm_r': {'rot': wave(2.0, (3, 0, 0))}, 'arm_l': {'rot': wave(2.0, (3, 0, 0), phase=0.5)},
                                  'h_head': {'rot': wave(2.0, (0, 8, 0))}}),
        'walk': Anim(1.0, tracks={'leg_r': {'rot': wave(1.0, (30, 0, 0))}, 'leg_l': {'rot': wave(1.0, (30, 0, 0), phase=0.5)},
                                  'arm_r': {'rot': wave(1.0, (25, 0, 0), phase=0.5)}, 'arm_l': {'rot': wave(1.0, (25, 0, 0))},
                                  'body': {'pos': wave(1.0, (0, 0.5, 0), times=2)}}),
        'attack': Anim(0.6, 'once', {'arm_r': {'rot': [(0, (0, 0, 0)), (0.2, (-120, 0, 0)), (0.35, (-30, 0, 0)), (0.6, (0, 0, 0))]},
                                     'body': {'rot': [(0, (0, 0, 0)), (0.25, (0, -15, 0)), (0.6, (0, 0, 0))]}}),
        'death': Anim(1.2, 'hold', {'root': {'rot': [(0, (0, 0, 0)), (0.9, (-90, 0, 0))],
                                             'pos': [(0, (0, 0, 0)), (0.9, (0, 2, 0))]}}),
        'spawn': Anim(1.0, 'once', {'root': {'pos': [(0, (0, -32, 0)), (1.0, (0, 0, 0))]}}),
    }
    return Creature('ember_knight', [root], {'iron': iron, 'tabard': tabard, 'eyes': eyes},
                    hitbox=(0.6, 1.95), anims=anims)


def magma_golem():
    head = Bone('h_head', (0, 34, -1), [cube('head', (0, 38, -2), (8, 8, 8), 'rock'),
                                         cube('eye', (2, 39, -6.05), (1.6, 1, 0.2), 'core'),
                                         cube('eye', (-2, 39, -6.05), (1.6, 1, 0.2), 'core')])
    arm_r, arm_l = pair('arm', (10, 32, 0), [cube('arm', (11.5, 23, 0), (5, 18, 6), 'rock'),
                                             cube('fist', (11.5, 11, 0), (6.5, 6, 7), 'rock')])
    body = Bone('body', (0, 14, 0), [cube('chest', (0, 26, 0), (18, 16, 10), 'rock'),
                                     cube('core', (0, 27, -5.2), (5, 5, 1), 'core'),
                                     cube('belly', (0, 17, 0), (12, 6, 8), 'rock')],
                [head, arm_r, arm_l, Bone('tag_name', (0, 46, 0))])
    leg_r, leg_l = pair('leg', (5, 14, 0), [cube('leg', (5, 7, 0), (6, 14, 6), 'rock')])
    root = Bone('root', (0, 0, 0), [], [body, leg_r, leg_l])
    anims = {
        'idle': Anim(3.0, tracks={'body': {'rot': wave(3.0, (2, 0, 0))}, 'h_head': {'rot': wave(3.0, (0, 10, 0))}}),
        'walk': Anim(1.6, tracks={'leg_r': {'rot': wave(1.6, (22, 0, 0))}, 'leg_l': {'rot': wave(1.6, (22, 0, 0), phase=0.5)},
                                  'arm_r': {'rot': wave(1.6, (18, 0, 0), phase=0.5)}, 'arm_l': {'rot': wave(1.6, (18, 0, 0))},
                                  'body': {'rot': wave(1.6, (0, 0, 4))}}),
        'attack': Anim(1.2, 'once', {
            'arm_r': {'rot': [(0, (0, 0, 0)), (0.5, (-160, 0, 0)), (0.75, (-20, 0, 0)), (1.2, (0, 0, 0))]},
            'arm_l': {'rot': [(0, (0, 0, 0)), (0.5, (-160, 0, 0)), (0.75, (-20, 0, 0)), (1.2, (0, 0, 0))]},
            'body': {'rot': [(0, (0, 0, 0)), (0.5, (-10, 0, 0)), (0.75, (15, 0, 0)), (1.2, (0, 0, 0))]}}),
        'roar': Anim(2.0, 'once', {                     # custom: played by the plugin (state / ANIMATION action)
            'h_head': {'rot': [(0, (0, 0, 0)), (0.4, (-30, 0, 0)), (1.6, (-30, 0, 0)), (2.0, (0, 0, 0))]},
            'arm_r': {'rot': [(0, (0, 0, 0)), (0.4, (0, 0, 40)), (1.6, (0, 0, 40)), (2.0, (0, 0, 0))]},
            'arm_l': {'rot': [(0, (0, 0, 0)), (0.4, (0, 0, -40)), (1.6, (0, 0, -40)), (2.0, (0, 0, 0))]}}),
        'death': Anim(1.6, 'hold', {'root': {'rot': [(0, (0, 0, 0)), (1.2, (85, 0, 0))]}}),
        'spawn': Anim(1.5, 'once', {'root': {'pos': [(0, (0, -42, 0)), (1.5, (0, 0, 0))]}}),
    }
    # Designed at iron-golem size, built twice as big: a boss.
    return Creature('magma_golem', [root], {'rock': rock, 'core': core}, hitbox=(1.4, 2.7), anims=anims, scale=2.0)


MODELS = [knight(), magma_golem()]
