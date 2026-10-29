"""
mcmodel: Minecraft cube models written as code, exported for Java, Bedrock (Geyser) and
the common model loaders. Pure Python 3.8+, no dependencies.

    from mcmodel import *
    steel = material('metal', ramp('#3a4150', '#c9d3e0'))
    sword = Item('ember_sword', [box('blade', (8, 15, 8), (2.4, 17, 1), 'steel')], {'steel': steel})
"""
from .geom import (FACES, Part, arc, bar, box, cube, curve, limb, matmul, mirror, move_parts, orb, ring, rot,
                   rotate_parts, spikes)
from .model import (ARMOR_PIECES, STYLES, Anim, ArmorSet, Bone, Creature, Item, pair, spin, wave)
from .paint import PAINTERS, hex_rgba, material, mix, ramp

__all__ = ['FACES', 'Part', 'arc', 'bar', 'box', 'cube', 'curve', 'limb', 'matmul', 'mirror', 'move_parts', 'orb',
           'ring', 'rot', 'rotate_parts', 'spikes', 'ARMOR_PIECES', 'STYLES', 'Anim', 'ArmorSet', 'Bone',
           'Creature', 'Item', 'pair', 'spin', 'wave', 'PAINTERS', 'hex_rgba', 'material', 'mix', 'ramp']
