"""
Example spec: laser weapons that spend laser cells. A pistol (one shot per click), a beam rifle
(a sustained beam while right click is held), a huge plasma cannon that fires a projectile
model, the ammo and the projectile.

    python scripts/build.py examples/lasers.py --out out/lasers --targets rpgroll

`shot=` is written as an RPGRoll-Items SHOOT action (target `rpgroll`); other loaders ignore it.
"""
from mcmodel import *

NAMESPACE = 'lasers'
TITLE = 'Laser Armory'

plating = material('plate', ramp('#161b24', '#4f5d72', '#d5dfec'))
steel = material('metal', ramp('#20242c', '#6c7584', '#e8edf5'))
rubber = material('grip', ramp('#121214', '#3c3c44'))
brass = material('trim', ramp('#3a2606', '#c08a2a', '#fff0b8'))
red = material('energy', ramp('#3a0004', '#ff2a2a', '#ffd0c8'), glow=15)
cyan = material('energy', ramp('#002a3a', '#30c8ff', '#e0fbff'), glow=15)
plasma = material('energy', ramp('#0c3a00', '#7cff4a', '#f0ffd8'), glow=15, cycles=3)
MATS = {'plating': plating, 'steel': steel, 'rubber': rubber, 'brass': brass, 'red': red, 'cyan': cyan,
        'plasma': plasma}

CELL = 'ammo/laser_cell'


def laser_cell():
    return Item(CELL, tube('cell', (8, 8, 8), 8, 2.2, 'cyan', axis='y')
                + tube('cap', (8, 3.6, 8), 1.4, 2.6, 'steel', axis='y')
                + tube('cap', (8, 12.4, 8), 1.4, 2.6, 'steel', axis='y')
                + [box('contact', (8, 13.6, 8), (1.4, 1, 1.4), 'brass')],
                MATS, style='object', name='Laser Cell')


def laser_pistol():
    # Side profile, barrel toward +x; grip = where the hand holds it.
    parts = (bevel('body', (10, 9.4, 8), (10, 3.4, 2.6), 'plating', edge=0.4)
             + tube('barrel', (17, 9.8, 8), 4, 1.0, 'steel')
             + [box('lens', (19.2, 9.8, 8), (0.5, 1.4, 1.4), 'red'),
                box('coil', (10, 9.4, 8), (6, 0.8, 2.8), 'red'),
                box('grip', (6.4, 5.6, 8), (2.2, 4.6, 2.0), 'rubber', r=(0, 0, 22.5)),
                box('trigger_guard', (9, 6.9, 8), (2.8, 0.5, 1.2), 'brass'),
                box('trigger_guard', (10.2, 7.3, 8), (0.5, 1.0, 1.2), 'brass')]
             + rivets('rivet', (7, 10.8, 6.6), (13, 10.8, 6.6), 3, 'brass', size=0.5))
    return Item('weapons/laser_pistol', parts, MATS, style='gun', grip=(6.4, 4.8), name='Laser Pistol', shot={
        'amount': 7, 'range': 40, 'particle': 'DUST', 'color': '#FF2A2A', 'particle2': 'END_ROD',
        'sound': 'BLOCK_BEACON_DEACTIVATE', 'pitch': 1.8, 'ammo': CELL,
        'no-ammo-message': '<red>Out of laser cells'})


def beam_rifle():
    # Sustained beam: `sustain` keeps it on and following the aim while right click is held.
    parts = (bevel('body', (12, 9.2, 8), (12, 4, 3), 'plating', edge=0.5)
             + bevel('stock', (3, 8.6, 8), (6, 3.4, 2.4), 'plating', edge=0.4)
             + tube('shroud', (22, 9.6, 8), 8, 1.4, 'steel')
             + tube('emitter', (27, 9.6, 8), 2, 1.9, 'steel')
             + tube('scope', (12, 12.4, 8), 6, 0.8, 'steel')
             + tube('cell', (15, 6.4, 8), 3, 0.9, 'cyan', axis='y')
             + [box('lens', (28.2, 9.6, 8), (0.5, 2.2, 2.2), 'cyan'),
                box('coil', (12, 9.2, 8), (8, 1.0, 3.2), 'cyan'),
                box('mount', (10, 11.4, 8), (1, 1.2, 1), 'steel'), box('mount', (14, 11.4, 8), (1, 1.2, 1), 'steel'),
                box('grip', (8, 5.2, 8), (2.4, 5, 2.2), 'rubber', r=(0, 0, 22.5))]
             + rivets('rivet', (7, 10.8, 6.4), (17, 10.8, 6.4), 5, 'brass', size=0.5)
             + rivets('rivet', (7, 10.8, 9.6), (17, 10.8, 9.6), 5, 'brass', size=0.5))
    return Item('weapons/beam_rifle', parts, MATS, style='gun', grip=(8, 4.4), hand_scale=1.15,
                name='Beam Rifle', shot={
                    'amount': 2, 'range': 24, 'sustain': 6, 'particle': 'DUST', 'color': '#30C8FF',
                    'size': 1.4, 'particle2': 'ELECTRIC_SPARK', 'spiral': 0.25,
                    'sound': 'BLOCK_BEACON_AMBIENT', 'pitch': 2.0, 'ammo': CELL,
                    'no-ammo-message': '<red>Out of laser cells'})


def plasma_cannon():
    # Built at full size (x 3..40 is past Java's 32): the build shrinks it into the box and
    # hand_scale makes it huge in the hand again.
    parts = (bevel('body', (16, 9, 8), (20, 6, 5), 'plating', edge=0.6)
             + tube('barrel', (32, 10, 8), 14, 2.2, 'steel')
             + tube('muzzle', (39.5, 10, 8), 1.5, 2.9, 'steel')
             + tube('canister', (5, 11, 8), 6, 2.0, 'plasma')
             + [box('handle', (17, 13.6, 8), (8, 1, 1.2), 'steel'), box('post', (13.6, 12.6, 8), (1, 1.6, 1), 'steel'),
                box('post', (20.4, 12.6, 8), (1, 1.6, 1), 'steel'),
                box('grip', (14, 4.4, 8), (2.6, 6, 2.4), 'rubber', r=(0, 0, 22.5)),
                box('vent', (16, 9, 5.3), (14, 1.2, 0.6), 'plasma'), box('vent', (16, 9, 10.7), (14, 1.2, 0.6), 'plasma')])
    for x in (27, 30.5, 34):
        parts += tube('coil', (x, 10, 8), 0.8, 2.5, 'plasma')
    parts += rivets('rivet', (8, 12.2, 5.4), (24, 12.2, 5.4), 6, 'brass', size=0.6)
    return Item('weapons/plasma_cannon', parts, MATS, style='gun', grip=(14, 3.6), hand_scale=1.5,
                name='Plasma Cannon', shot={
                    'amount': 14, 'range': 60, 'speed': 1.4, 'model': 'projectiles/plasma_bolt',
                    'particle': 'DUST', 'color': '#7CFF4A', 'size': 1.6, 'particle2': 'END_ROD',
                    'explosion': 2.5, 'sound': 'ENTITY_BLAZE_SHOOT', 'pitch': 0.6, 'ammo': CELL,
                    'ammo-amount': 3})


def plasma_bolt():
    # Projectile: nose toward +z around (8, 8, 8); the ItemDisplay turns +z to where it flies.
    return Item('projectiles/plasma_bolt', orb('core', (8, 8, 10), 2.2, 'plasma')
                + tube('tail', (8, 8, 5.5), 5, 1.1, 'plasma', axis='z'),
                MATS, style='projectile', name='Plasma Bolt')


MODELS = [laser_cell(), laser_pistol(), beam_rifle(), plasma_cannon(), plasma_bolt()]
