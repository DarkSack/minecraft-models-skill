"""
The three things a spec can declare:

  Item      a cube model that is held, worn on the head or placed (Java item model,
            Blockbench project, Bedrock attachable + icon, Geyser mapping).
  ArmorSet  the worn look of an armor (Java equipment layers, Bedrock armor geometry).
  Creature  bones + cubes + animations for an entity loader (FreeMinecraftModels,
            ModelEngine, BetterModel) as a Blockbench "Generic Model" (.bbmodel).

The Java -> Bedrock cube conversion is Blockbench's: x mirrored, z - 8, x and y
rotations negated, z kept.
"""
import base64
import copy
import math
import random
import re
import uuid

from .geom import FACES, angles, apply, display_rot, matmul, rot
from .paint import CLEAR, PAINTERS, is_animated, mix, png_bytes, read_png

DENSITY = 4          # texture pixels per model unit (4 = the detail of a 64x64 item)
FRAMES = 16          # animation frames when a material moves
UUID_NS = uuid.UUID('6c0f7f8e-3a52-4c1e-9b5e-2f1d8c7a9b30')
ID_RE = re.compile(r'^[a-z0-9_.-]+(/[a-z0-9_.-]+)*$')


def _uuid(*parts):
    return str(uuid.uuid5(UUID_NS, '/'.join(map(str, parts))))


def _r4(v):
    return [round(x, 4) for x in v]


def _check_id(ident, what):
    if not ID_RE.match(ident):
        raise ValueError('%s id %r: use lowercase a-z 0-9 _ . - (and / for folders)' % (what, ident))


# ================================================================= base: cubes + atlas + paint

class Model:
    def __init__(self, ident, parts, mats, density=DENSITY):
        self.id = ident
        self.parts = list(parts)
        self.mats = mats
        self.density = self.density_asked = density
        self.display = None
        self.uv, self.side, self.frames = {}, 0, []
        self.frametime = 2
        self.warnings = []
        if not self.parts:
            raise ValueError('%s: no parts' % ident)
        missing = sorted({p.mat for p in self.parts} - set(mats))
        if missing:
            raise ValueError('%s: materials not defined: %s' % (ident, ', '.join(missing)))
        for m in mats.values():
            if m.get('type') not in PAINTERS:
                raise ValueError('%s: material without a known painter: %r' % (ident, m))
        for p in self.parts:
            if p.light is None:
                p.light = int(mats[p.mat].get('glow', 0))

    @property
    def animated(self):
        return len(self.frames) > 1

    @property
    def px(self):
        return self.frames[0]

    def strip(self):
        """All frames stacked vertically: Java's animated texture layout."""
        return [row for fr in self.frames for row in fr]

    def bounds(self):
        vs = [v for p in self.parts for v in p.vertices()]
        return [min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]

    def pack(self, max_side=256):
        """Give every visible face a rectangle in the atlas; lowers the density if it won't fit."""
        d = self.density
        while True:
            rects = []
            for i, p in enumerate(self.parts):
                for f in FACES:
                    if f in p.hide:
                        continue
                    w, h = p.face_size(f)
                    rects.append((max(1, int(round(w * d))), max(1, int(round(h * d))), i, f))
            rects.sort(key=lambda r: (-r[1], -r[0]))
            side = 16
            while side <= max_side:
                x = y = row = 0
                spot, ok = {}, True
                for w, h, i, f in rects:
                    if w > side:
                        ok = False
                        break
                    if x + w > side:
                        x, y, row = 0, y + row, 0
                    if y + h > side:
                        ok = False
                        break
                    spot[(i, f)] = (x, y, w, h)
                    x += w
                    row = max(row, h)
                if ok:
                    self.uv, self.side, self.density = spot, side, d
                    if d < self.density_asked:
                        self.warnings.append('texture density lowered to %.2f px/unit to fit %dx%d'
                                             % (d, max_side, max_side))
                    return self
                side *= 2
            d *= 0.85

    def paint(self, seed=None, frames=FRAMES):
        """Paint every face. One frame unless a material moves."""
        seed = sum(map(ord, self.id)) if seed is None else seed
        moving = any(is_animated(self.mats[p.mat]) for p in self.parts)
        n = frames if moving else 1
        self.frames = []
        for k in range(n):
            px = [[CLEAR] * self.side for _ in range(self.side)]
            for (i, f), (x0, y0, w, h) in sorted(self.uv.items()):
                p = self.parts[i]
                mat = self.mats[p.mat]
                rnd = random.Random(seed * 7919 + i * 31 + FACES.index(f))
                face = PAINTERS[mat['type']](mat, f, w, h, rnd, p, k / float(n), i)
                for y in range(h):
                    for x in range(w):
                        px[y0 + y][x0 + x] = face[y][x]
            self.frames.append(px)
        return self

    def finish(self, seed=None, max_side=256):
        return self.pack(max_side).paint(seed)


# ================================================================= Item

# Vanilla display presets (item/handheld, item/generated, item/handheld_rod).
HANDHELD = {
    'thirdperson_righthand': {'rotation': [0, -90, 55], 'translation': [0, 4, 0.5], 'scale': [0.85] * 3},
    'thirdperson_lefthand': {'rotation': [0, 90, -55], 'translation': [0, 4, 0.5], 'scale': [0.85] * 3},
    'firstperson_righthand': {'rotation': [0, -90, 25], 'translation': [1.13, 3.2, 1.13], 'scale': [0.68] * 3},
    'firstperson_lefthand': {'rotation': [0, 90, -25], 'translation': [1.13, 3.2, 1.13], 'scale': [0.68] * 3},
    'head': {'rotation': [0, 180, 0], 'translation': [0, 13, 7], 'scale': [1, 1, 1]},
}
GENERATED = {
    'thirdperson_righthand': {'rotation': [0, 0, 0], 'translation': [0, 3, 1], 'scale': [0.55] * 3},
    'thirdperson_lefthand': {'rotation': [0, 0, 0], 'translation': [0, 3, 1], 'scale': [0.55] * 3},
    'firstperson_righthand': {'rotation': [0, -90, 25], 'translation': [1.13, 3.2, 1.13], 'scale': [0.68] * 3},
    'firstperson_lefthand': {'rotation': [0, 90, -25], 'translation': [1.13, 3.2, 1.13], 'scale': [0.68] * 3},
    'head': {'rotation': [0, 180, 0], 'translation': [0, 13, 7], 'scale': [1, 1, 1]},
}
ROD = {
    'thirdperson_righthand': {'rotation': [0, 90, 55], 'translation': [0, 4, 2.5], 'scale': [0.85] * 3},
    'thirdperson_lefthand': {'rotation': [0, -90, -55], 'translation': [0, 4, 2.5], 'scale': [0.85] * 3},
    'firstperson_righthand': {'rotation': [0, -90, 25], 'translation': [0, 1.6, 0.8], 'scale': [0.68] * 3},
    'firstperson_lefthand': {'rotation': [0, 90, -25], 'translation': [0, 1.6, 0.8], 'scale': [0.68] * 3},
    'head': {'rotation': [0, 180, 0], 'translation': [0, 13, 7], 'scale': [1, 1, 1]},
}
# Worn on the head (equipment-model none): model center (8, 8, 8) at the head center, front to -z.
HELMET = {
    'head': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]},
    'gui': {'rotation': [20, 150, 0], 'translation': [0, -0.6, 0], 'scale': [0.56] * 3},
    'ground': {'translation': [0, 3, 0], 'scale': [0.3] * 3},
    'fixed': {'rotation': [0, 180, 0], 'scale': [0.55] * 3},
    'thirdperson_righthand': {'rotation': [75, 45, 0], 'translation': [0, 2.5, 0], 'scale': [0.33] * 3},
    'thirdperson_lefthand': {'rotation': [75, 45, 0], 'translation': [0, 2.5, 0], 'scale': [0.33] * 3},
    'firstperson_righthand': {'rotation': [0, 45, 0], 'scale': [0.36] * 3},
    'firstperson_lefthand': {'rotation': [0, 225, 0], 'scale': [0.36] * 3},
}
GUI_3D = [30, 45, 0]
# Third person: +x is the side, +y the front (where a vanilla sword points), z the arm axis.
# [0, 90, 90] puts a barrel built along +x to the front with the grip (-y) along the arm.
GUN_VIEWS = {'thirdperson_righthand': [0, 90, 90], 'thirdperson_lefthand': [0, -90, -90],
             'firstperson_righthand': [0, -90, 0], 'firstperson_lefthand': [0, 90, 0]}
HANDS = ('thirdperson_righthand', 'thirdperson_lefthand', 'firstperson_righthand', 'firstperson_lefthand')
GUN_LENGTH = 20.0      # a longer gun is scaled down in the hand
BLADE_LENGTH = 24.0    # diagonal: a vanilla sword is 22.6 from tip to pommel

STYLES = ('handheld', 'gun', 'rod', 'flat', 'object', 'helmet', 'furniture')
DEFAULT_BASE = {'handheld': 'iron_sword', 'gun': 'iron_horse_armor', 'rod': 'fishing_rod', 'flat': 'paper',
                'object': 'paper', 'helmet': 'iron_helmet', 'furniture': 'paper'}
# Armor piece -> (Bedrock c.item_slot, Java layer index: humanoid = 1, humanoid_leggings = 2)
ARMOR_PIECES = {'helmet': ('head', 1), 'chestplate': ('torso', 1), 'leggings': ('legs', 2), 'boots': ('feet', 1)}


class Item(Model):
    """
    style:
      handheld  sword, axe, pickaxe, staff: build it standing up (tip to +y, grip at the
                bottom); it is tilted 45 degrees like a vanilla sword and the pommel goes in the hand
      gun       side profile, barrel toward +x; `grip` = (x, y) of the hand on the model
      rod       held like a fishing rod (built standing up, tilted like 'handheld')
      flat      held like a flat vanilla item (gem, food, token)
      object    3D trinket shown three-quarter in the inventory (lantern, potion, totem)
      helmet    worn on the head, front facing -z, center (8, 8, 8) at the head center
      furniture placed with an ItemDisplay (transform NONE): drawn as built, block 0..16
    base:  vanilla item it rides on (behavior + fallback look), e.g. 'diamond_sword'.
    wears: (armor_set_id, 'helmet'|'chestplate'|'leggings'|'boots') for an armor piece.
    """

    def __init__(self, ident, parts, mats, style='handheld', name=None, base=None, grip=(4, 4), wears=None,
                 density=DENSITY, seed=None):
        _check_id(ident, 'item')
        if style not in STYLES:
            raise ValueError('%s: style %r not in %s' % (ident, style, ', '.join(STYLES)))
        super().__init__(ident, parts, mats, density)
        self.style = style
        self.name = name or ident.split('/')[-1].replace('_', ' ').title()
        self.grip = grip
        self.wears = wears
        if wears:
            if wears[1] not in ARMOR_PIECES:
                raise ValueError('%s: wears piece must be one of %s' % (ident, ', '.join(ARMOR_PIECES)))
            base = base or 'iron_' + wears[1]
        self.base = (base or DEFAULT_BASE[style]).replace('minecraft:', '')
        if style in ('handheld', 'rod'):
            for p in self.parts:
                p.rotate(rot(z=-45), [8, 8, 8])
        for p in self.parts:
            p.within_45()
        self._check_range()
        self._prepare_display()
        self.finish(seed)

    # ------------------------------------------------------------ checks

    def _check_range(self):
        """Java item models only accept from/to between -16 and 32."""
        bad = sorted({p.name for p in self.parts for v in p.frm + p.to if not -16 <= v <= 32})
        if bad:
            lo, hi = self.bounds()
            raise ValueError('%s: parts outside the Java range -16..32: %s (model spans %s..%s). Make it '
                             'smaller; the display scale can enlarge it back.' % (self.id, ', '.join(bad),
                                                                                  _r4(lo), _r4(hi)))

    def min_java(self):
        """Oldest Java version that renders every rotation (1.21.4 is the floor of item_model)."""
        need = (1, 21, 4)
        for p in self.parts:
            axes = [a for a in p.angles() if a]
            if not axes:
                continue
            if len(axes) > 1 or abs(axes[0]) > 45:
                return (1, 21, 11)
            if abs(axes[0] / 22.5 - round(axes[0] / 22.5)) > 1e-6:
                need = (1, 21, 6)
        return need

    # ------------------------------------------------------------ display

    def _fit(self, preset):
        lo, hi = self.bounds()
        w, h = hi[0] - lo[0], hi[1] - lo[1]
        s = round(min(1.0, 15.6 / max(w, h)), 3)
        cx, cy = (lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0
        t = [round(-(cx - 8) * s, 3), round(-(cy - 8) * s, 3), 0]
        d = copy.deepcopy(preset)
        d['gui'] = {'rotation': [0, 0, 0], 'translation': t, 'scale': [s] * 3}
        d['ground'] = {'rotation': [0, 0, 0], 'translation': [0, 2, 0], 'scale': [round(0.5 * s, 3)] * 3}
        d['fixed'] = {'rotation': [0, 180, 0], 'translation': [-t[0], t[1], 0], 'scale': [s] * 3}
        return d

    def _prepare_display(self):
        st = self.style
        if st == 'handheld':
            self.display = self._fit(HANDHELD)
            # The pommel is the bottom-left end; the hand holds it 2.8 units in, like a vanilla sword.
            diag = [(v[0] + v[1] - 16) / math.sqrt(2) for p in self.parts for v in p.vertices()]
            d = (-min(diag) - 2.83) / math.sqrt(2)
            self._shrink_in_hand(BLADE_LENGTH / (max(diag) - min(diag)), [-d, -d, 0])
        elif st == 'gun':
            self.display = self._fit(HANDHELD)
            g = [self.grip[0] - 8, self.grip[1] - 8, 0]
            for view, r in GUN_VIEWS.items():
                v = self.display[view]
                s = v['scale'][0]
                sword = apply(display_rot(v['rotation']), [-6 * s, -6 * s, 0])
                gun = apply(display_rot(r), [c * s for c in g])
                self.display[view] = {'rotation': r, 'scale': v['scale'],
                                      'translation': [round(a + b - c, 3) for a, b, c in zip(v['translation'], sword, gun)]}
            lo, hi = self.bounds()
            self._shrink_in_hand(GUN_LENGTH / (hi[0] - lo[0]), g)
        elif st == 'rod':
            self.display = self._fit(ROD)
        elif st == 'flat':
            self.display = self._fit(GENERATED)
        elif st == 'helmet':
            self.display = copy.deepcopy(HELMET)
        elif st == 'object':
            lo, hi = self.bounds()
            ext = max(h - l for l, h in zip(lo, hi))
            s = round(min(1.0, 0.625 * 16.0 / max(ext, 9.0) * 1.05), 4)
            q = apply(display_rot(GUI_3D), [(l + h) / 2.0 - 8 for l, h in zip(lo, hi)])
            self.display = copy.deepcopy(GENERATED)
            self.display['gui'] = {'rotation': GUI_3D, 'translation': [round(-v * s, 3) for v in q], 'scale': [s] * 3}
            self.display['ground'] = {'rotation': [0, 0, 0], 'translation': [0, 2, 0],
                                      'scale': [round(0.4 * s / 0.625, 3)] * 3}
            self.display['fixed'] = {'rotation': [0, 180, 0], 'translation': [0, 0, 0],
                                     'scale': [round(s / 0.625 * 0.6, 3)] * 3}
        else:  # furniture: no 'fixed', the ItemDisplay draws the model as built
            lo, hi = self.bounds()
            fit = min(1.0, 16.0 / max(h - l for l, h in zip(lo, hi)))
            c = [(l + h) / 2.0 - 8 for l, h in zip(lo, hi)]

            def center(r, s):
                return [round(max(-80, min(80, -v * s)), 3) for v in apply(display_rot(r), c)]

            gs, ts, fs = round(0.62 * fit, 4), round(0.375 * fit, 4), round(0.4 * fit, 4)
            self.display = {
                'gui': {'rotation': [30, 225, 0], 'translation': center([30, 225, 0], gs), 'scale': [gs] * 3},
                'ground': {'rotation': [0, 0, 0], 'translation': [0, 3, 0], 'scale': [round(0.25 * fit, 4)] * 3},
                'thirdperson_righthand': {'rotation': [75, 45, 0], 'translation': [0, 2.5, 0], 'scale': [ts] * 3},
                'thirdperson_lefthand': {'rotation': [75, 45, 0], 'translation': [0, 2.5, 0], 'scale': [ts] * 3},
                'firstperson_righthand': {'rotation': [0, 45, 0], 'translation': [0, 0, 0], 'scale': [fs] * 3},
                'firstperson_lefthand': {'rotation': [0, 225, 0], 'translation': [0, 0, 0], 'scale': [fs] * 3},
            }

    def _shrink_in_hand(self, k, hold):
        """Scale the hand views by k (< 1 only) keeping `hold` (relative to the center) in the hand."""
        if k >= 1:
            return
        for view in HANDS:
            v = self.display[view]
            s = v['scale'][0]
            before = apply(display_rot(v['rotation']), [c * s for c in hold])
            after = apply(display_rot(v['rotation']), [c * s * k for c in hold])
            v['translation'] = [round(t + a - b, 3) for t, a, b in zip(v['translation'], before, after)]
            v['scale'] = [round(s * k, 3)] * 3

    @property
    def flat_gui(self):
        return self.style in ('handheld', 'gun', 'rod', 'flat')

    # ------------------------------------------------------------ Java

    def java_model(self, texture_id):
        """The Java item model. `texture_id` like 'mypack:item/ember_sword'."""
        k = 16.0 / self.side
        elements = []
        for i, p in enumerate(self.parts):
            e = {'name': p.name, 'from': _r4(p.frm), 'to': _r4(p.to)}
            a = p.angles()
            if any(a):
                r = {'origin': _r4(p.origin)}
                axes = [(n, v) for n, v in zip('xyz', a) if v]
                if len(axes) == 1 and abs(axes[0][1]) <= 45:
                    r['axis'], r['angle'] = axes[0]
                else:
                    r['x'], r['y'], r['z'] = a        # multi-axis: Java 1.21.11+
                e['rotation'] = r
            if p.light:
                e['light_emission'] = p.light
            e['faces'] = {}
            for f in FACES:
                if f in p.hide:
                    continue
                x, y, w, h = self.uv[(i, f)]
                e['faces'][f] = {'uv': _r4([x * k, y * k, (x + w) * k, (y + h) * k]), 'texture': '#0'}
            elements.append(e)
        out = {'textures': {'0': texture_id, 'particle': texture_id}, 'elements': elements}
        if self.flat_gui:
            out['gui_light'] = 'front'
        out['display'] = self.display
        return out

    def java_definition(self, model_id):
        """assets/<ns>/items/<id>.json (Java 1.21.4+)."""
        return {'model': {'type': 'minecraft:model', 'model': model_id}}

    def mcmeta(self):
        return {'animation': {'frametime': self.frametime, 'interpolate': False}}

    # ------------------------------------------------------------ Blockbench (Java Block/Item)

    def bbmodel(self, ns):
        tex_png = png_bytes(self.strip())
        els, ids = [], []
        for i, p in enumerate(self.parts):
            u = _uuid(ns, self.id, 'el', i)
            ids.append(u)
            faces = {}
            for f in FACES:
                if f in p.hide:
                    faces[f] = {'uv': [0, 0, 0, 0], 'texture': None}
                else:
                    x, y, w, h = self.uv[(i, f)]
                    faces[f] = {'uv': [x, y, x + w, y + h], 'texture': 0}
            els.append({'name': p.name, 'box_uv': False, 'rescale': False, 'locked': False,
                        'light_emission': p.light, 'render_order': 'default', 'allow_mirror_modeling': True,
                        'from': _r4(p.frm), 'to': _r4(p.to), 'autouv': 0, 'color': i % 8,
                        'origin': _r4(p.origin), 'rotation': p.angles(), 'faces': faces, 'type': 'cube', 'uuid': u})
        folder, name = ('item/' + self.id).rsplit('/', 1)
        tex = {'path': '', 'name': name + '.png', 'folder': folder, 'namespace': ns, 'id': '0', 'group': '',
               'width': self.side, 'height': self.side * len(self.frames), 'uv_width': self.side,
               'uv_height': self.side, 'particle': True, 'use_as_default': False, 'layers_enabled': False,
               'sync_to_project': '', 'render_mode': 'default', 'render_sides': 'auto',
               'frame_time': self.frametime, 'frame_order_type': 'loop', 'frame_order': '', 'frame_interpolate': False,
               'visible': True, 'internal': True, 'saved': True, 'uuid': _uuid(ns, self.id, 'tex'),
               'source': 'data:image/png;base64,' + base64.b64encode(tex_png).decode('ascii')}
        return {'meta': {'format_version': '4.10', 'model_format': 'java_block', 'box_uv': False},
                'name': self.id.split('/')[-1], 'parent': '', 'ambientocclusion': True, 'front_gui_light': self.flat_gui,
                'visible_box': [1, 1, 0], 'variable_placeholders': '', 'variable_placeholder_buttons': [],
                'unhandled_root_fields': {}, 'resolution': {'width': self.side, 'height': self.side},
                'elements': els, 'outliner': ids, 'textures': [tex], 'display': self.display}

    # ------------------------------------------------------------ Bedrock (attachable for Geyser)

    def bedrock_cubes(self):
        cubes = []
        for i, p in enumerate(self.parts):
            c = {'origin': _r4([-(p.to[0] - 8), p.frm[1], p.frm[2] - 8]), 'size': _r4(p.size())}
            a = p.angles()
            if any(a):
                c['pivot'] = _r4([-(p.origin[0] - 8), p.origin[1], p.origin[2] - 8])
                c['rotation'] = [-a[0] if a[0] else 0.0, -a[1] if a[1] else 0.0, a[2]]
            c['uv'] = {}
            for f in FACES:
                if f not in p.hide:
                    x, y, w, h = self.uv[(i, f)]
                    c['uv'][f] = {'uv': [x, y], 'uv_size': [w, h]}
            cubes.append(c)
        return cubes

    def bedrock_geometry(self, ident):
        """
        Bones geyser_custom > _x > _y > _z (the java2bedrock layout): each animation turns
        one of them on one axis, which reproduces the rotation order of Java's `display`.
        """
        pivot = [0, 8, 0]
        binding = "c.item_slot == 'head' ? 'head' : q.item_slot_to_bone_name(c.item_slot)"
        desc = {'identifier': 'geometry.' + ident, 'texture_width': self.side, 'texture_height': self.side,
                'visible_bounds_width': 4, 'visible_bounds_height': 4.5, 'visible_bounds_offset': [0, 0.75, 0]}
        if self.style == 'furniture':
            # On a GeyserDisplayEntity entity, bind to its geyser_z bone (carries the ItemDisplay
            # transform); it is told apart by a property only that entity has.
            binding = "q.has_property('geyser:t_x') ? 'geyser_z' : (%s)" % binding
            lo, hi = self.bounds()
            ext = max(h - l for l, h in zip(lo, hi)) / 16.0
            desc.update(visible_bounds_width=round(ext + 2, 2), visible_bounds_height=round(ext + 2, 2),
                        visible_bounds_offset=[0, round(ext / 2, 2), 0])
        return {'format_version': '1.16.0', 'minecraft:geometry': [{'description': desc, 'bones': [
            {'name': 'geyser_custom', 'pivot': pivot, 'binding': binding},
            {'name': 'geyser_custom_x', 'parent': 'geyser_custom', 'pivot': pivot},
            {'name': 'geyser_custom_y', 'parent': 'geyser_custom_x', 'pivot': pivot},
            {'name': 'geyser_custom_z', 'parent': 'geyser_custom_y', 'pivot': pivot, 'cubes': self.bedrock_cubes()},
        ]}]}

    def bedrock_animations(self, ident):
        """Java's `display` turned into Bedrock animations (same split as java2bedrock)."""
        d = self.display or {}

        def bones(pos, root, mirror_x=True, k=1.0):
            r, t, s = pos.get('rotation', [0, 0, 0]), pos.get('translation', [0, 0, 0]), pos.get('scale', [1, 1, 1])
            return {'geyser_custom': root,
                    'geyser_custom_x': {'rotation': [-r[0], 0, 0],
                                        'position': [(-t[0] if mirror_x else t[0]) * k, t[1] * k, t[2] * k],
                                        'scale': [v * k for v in s]},
                    'geyser_custom_y': {'rotation': [0, -r[1], 0]},
                    'geyser_custom_z': {'rotation': [0, 0, r[2]]}}

        base = 'animation.' + ident
        tp = {'rotation': [90, 0, 0], 'position': [0, 13, -3]}
        fp = {'rotation': [90, 60, -40], 'position': [4, 10, 4], 'scale': 1.5}
        anims = {base + '.tp_right': bones(d['thirdperson_righthand'], tp),
                 base + '.tp_left': bones(d['thirdperson_lefthand'], tp, mirror_x=False),
                 base + '.fp_right': bones(d['firstperson_righthand'], fp),
                 base + '.fp_left': bones(d['firstperson_lefthand'], fp, mirror_x=False),
                 base + '.head': bones(d.get('head', {}), {'position': [0, 19.9, 0]}, k=0.625)}
        if self.style == 'furniture':
            # GeyserDisplayEntity sends the offset x10 (a block is 16) with z flipped, and bound
            # to the bone the model sits one block low: measured in the client.
            anims[base + '.placed'] = {'geyser_custom': {'position': [
                "0.6 * q.property('geyser:t_x')", "16 + 0.6 * q.property('geyser:t_y')",
                "-2.6 * q.property('geyser:t_z')"]}}
        return {'format_version': '1.8.0', 'animations': {k: {'loop': True, 'bones': v} for k, v in anims.items()}}

    def bedrock_attachable(self, bedrock_id, ident, texture, worn=None):
        """`worn` = (geometry piece, item_slot, layer texture path) for an armor piece."""
        base = 'animation.' + ident
        names = ('tp_right', 'tp_left', 'fp_right', 'fp_left', 'head')
        animations = {n: '%s.%s' % (base, n) for n in names}
        animate = [{'tp_right': 'v.main_hand && !c.is_first_person'},
                   {'tp_left': 'v.off_hand && !c.is_first_person'},
                   {'fp_right': 'v.main_hand && c.is_first_person'},
                   {'fp_left': 'v.off_hand && c.is_first_person'},
                   {'head': 'v.head && !c.is_first_person'}]
        pre = ["v.main_hand = c.item_slot == 'main_hand';", "v.off_hand = c.item_slot == 'off_hand';",
               "v.head = c.item_slot == 'head';"]
        if self.style == 'furniture':
            animations['placed'] = base + '.placed'
            pre.append("v.placed = q.has_property('geyser:t_x');")
            animate.append({'placed': 'v.placed'})
        desc = {'identifier': bedrock_id,
                'materials': {'default': 'entity_alphatest', 'enchanted': 'entity_alphatest_glint'},
                'textures': {'default': texture, 'enchanted': 'textures/misc/enchanted_item_glint'},
                'geometry': {'default': 'geometry.' + ident},
                'animations': animations, 'scripts': {'pre_animation': pre, 'animate': animate},
                'render_controllers': ['controller.render.item_default']}
        if worn:
            piece, slot, layer_tex = worn
            desc['materials']['worn'] = 'armor'
            desc['textures']['worn'] = layer_tex
            desc['geometry']['worn'] = 'geometry.player.armor.' + piece
            pre.append("v.worn = c.item_slot == '%s';" % slot)
            desc['render_controllers'] = ['controller.render.%s_worn' % ident]
        return {'format_version': '1.10.0', 'minecraft:attachable': {'description': desc}}

    @staticmethod
    def worn_controller(ident):
        """Worn: armor geometry + layer texture; in the hand or on the ground: the 3D model."""
        return {'controller.render.%s_worn' % ident: {
            'geometry': 'v.worn ? Geometry.worn : Geometry.default',
            'materials': [{'*': 'v.worn ? Material.worn : Material.default'}],
            'textures': ['v.worn ? Texture.worn : Texture.default']}}


# ================================================================= ArmorSet

def _cube_faces(u, v, w, h, d):
    """Faces of a box on Minecraft's box-UV map: name -> (x, y, width, height)."""
    return {'top': (u + d, v, w, d), 'bottom': (u + d + w, v, w, d), 'right': (u, v + d, d, h),
            'front': (u + d, v + d, w, h), 'left': (u + d + w, v + d, d, h), 'back': (u + 2 * d + w, v + d, w, h)}


_TONE = {'top': -3, 'front': 5, 'right': 4, 'left': 4, 'back': 3, 'bottom': 2}


def _paint_face(px, face, rect, pal, rows=None, accent=None, open_front=False):
    """One face of a worn layer: tone by orientation, dark border, plate lines, a rivet."""
    x0, y0, w, h = rect
    for j in range(h):
        if rows is not None and j not in rows:
            continue
        for i in range(w):
            if open_front and 1 <= j < h - 1 and 1 <= i < w - 1:
                continue                                    # the face opening of a helmet
            c = pal[_TONE[face]]
            edge = i in (0, w - 1) or j in (0, h - 1) or (rows is not None and j in (min(rows), max(rows)))
            if edge:
                c = pal[max(1, _TONE[face] - 2)] if face != 'top' else pal[4]
            elif face in ('front', 'back', 'right', 'left') and j % 4 == 3:
                c = pal[max(1, _TONE[face] - 1)]
            if face == 'front' and not edge and j == 1 and i == 1:
                c = pal[-1]
            px[y0 + j][x0 + i] = c
    if accent and face == 'front' and w >= 4 and not open_front:
        rr = [r for r in range(1, h - 1) if rows is None or r in rows]
        if rr:
            px[y0 + rr[len(rr) // 2]][x0 + w // 2] = accent[-2]


class ArmorSet:
    """
    The worn look of an armor: two 64x32 layers on the vanilla humanoid UV map.
    Layer 1 = helmet, chestplate (torso + arms), boots; layer 2 = leggings.
    `ramp` (8+ colors) paints them; or pass `layers=('l1.png', 'l2.png')` to use your own.
    Pieces are Items with wears=(this id, piece).
    """

    def __init__(self, ident, ramp=None, accent=None, layers=None, open_face=True):
        _check_id(ident, 'armor set')
        self.id = ident
        if layers:
            self.layer1, self.layer2 = read_png(layers[0]), read_png(layers[1])
            for lay in (self.layer1, self.layer2):
                w, h = len(lay[0]), len(lay)
                if w != 2 * h or w % 64:
                    raise ValueError('%s: worn layers must be 64x32 (or 128x64...), got %dx%d' % (ident, w, h))
            return
        if not ramp or len(ramp) < 7:
            raise ValueError('%s: give a ramp of 8 colors (paint.ramp) or layers=(png, png)' % ident)
        pal = list(ramp)
        l1 = [[CLEAR] * 64 for _ in range(32)]
        for face, rect in _cube_faces(0, 0, 8, 8, 8).items():         # helmet
            if face != 'bottom':
                _paint_face(l1, face, rect, pal, accent=accent, open_front=open_face and face == 'front')
        fx, fy, fw, _ = _cube_faces(0, 0, 8, 8, 8)['front']            # brow: two rows on top
        for i in range(fw):
            l1[fy + 1][fx + i] = pal[5]
            if 0 < i < fw - 1:
                l1[fy + 2][fx + i] = pal[3]
        for face, rect in _cube_faces(16, 16, 8, 12, 4).items():      # chest
            _paint_face(l1, face, rect, pal, accent=accent)
        for face, rect in _cube_faces(40, 16, 4, 12, 4).items():      # arms (shoulders down)
            if face != 'bottom':
                _paint_face(l1, face, rect, pal, rows=None if face == 'top' else range(0, 9))
        for face, rect in _cube_faces(0, 16, 4, 12, 4).items():       # boots
            if face != 'top':
                _paint_face(l1, face, rect, pal, rows=None if face == 'bottom' else range(8, 12))
        l2 = [[CLEAR] * 64 for _ in range(32)]
        for face, rect in _cube_faces(16, 16, 8, 12, 4).items():      # waist
            if face not in ('top', 'bottom'):
                _paint_face(l2, face, rect, pal, rows=range(7, 12))
        for face, rect in _cube_faces(0, 16, 4, 12, 4).items():       # legs
            if face != 'bottom':
                _paint_face(l2, face, rect, pal, rows=None if face == 'top' else range(0, 10))
        if accent:
            bx, by, _, _ = _cube_faces(16, 16, 8, 12, 4)['front']
            l2[by + 8][bx + 4] = accent[-2]
        self.layer1, self.layer2 = l1, l2

    def preview(self, k=4):
        bg = (60, 60, 70, 255)
        out = []
        for lay in (self.layer1, self.layer2):
            s = 64 * k // len(lay[0])
            out += [[lay[y // s][x // s] if lay[y // s][x // s][3] else bg for x in range(64 * k)]
                    for y in range(32 * k)]
            out += [[(30, 30, 36, 255)] * (64 * k) for _ in range(k)]
        return out


# ================================================================= Creature

class Bone:
    """A bone: pivot point, its cubes and child bones. Name prefixes carry loader behavior (h_ head...)."""

    def __init__(self, name, pivot, parts=(), children=()):
        self.name = name
        self.pivot = [float(v) for v in pivot]
        self.parts = list(parts)
        self.children = list(children)

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


def pair(name, pivot, parts, children=()):
    """A bone on the creature's right (x > 0, since it faces -z) and its mirrored twin on the left:
    names <name>_r and <name>_l. `children` is a list of (right, left) pairs from other pair() calls."""
    from .geom import mirror
    r = Bone(name + '_r', pivot, parts, [c[0] for c in children])
    l = Bone(name + '_l', [-pivot[0], pivot[1], pivot[2]], [mirror(p) for p in parts], [c[1] for c in children])
    return r, l


class Anim:
    """
    An animation. tracks = {bone: {'rot'|'pos'|'scale': [(t, value), ...]}} with (x, y, z) values in
    Blockbench's convention: rotation x and y are negated vs. math (arm forward = negative x;
    leaning forward = positive x); position x is negated and z = -2 moves forward.
    loop: 'loop', 'once' or 'hold'.
    """

    def __init__(self, length, loop='loop', tracks=None, smooth=True):
        self.length = length
        self.loop = loop
        self.tracks = tracks or {}
        self.smooth = smooth

    def track(self, bone, channel, keys):
        self.tracks.setdefault(bone, {}).setdefault(channel, []).extend(keys)
        return self


def wave(length, amp, base=(0, 0, 0), phase=0.0, n=8, times=1):
    """Keys of a sine that closes on itself (for loops): base + amp * sin."""
    return [(round(length * k / float(n), 4),
             tuple(round(b + a * math.sin(2 * math.pi * (times * k / float(n) + phase)), 3) for a, b in zip(amp, base)))
            for k in range(n + 1)]


def spin(length, axis='y', steps=4, direction=1):
    """A full turn in a loop (linear keys every 360/steps degrees)."""
    i = 'xyz'.index(axis)
    out = []
    for k in range(steps + 1):
        v = [0, 0, 0]
        v[i] = direction * 360.0 * k / steps
        out.append((round(length * k / float(steps), 4), tuple(v)))
    return out


def _value(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
            return a + (b - a) * k if isinstance(a, (int, float)) else tuple(x + (y - x) * k for x, y in zip(a, b))
    return keys[-1][1]


class Creature:
    """
    An animated entity model. `bones`: top-level Bones. `hitbox` = (width, height) in blocks
    (the size of the base mob). `anims` = {name: Anim}. Faces -z, feet at y = 0.
    `scale` resizes everything (cubes, pivots, animation offsets, hitbox) and keeps the
    texture detail: design a boss at mob size, then scale=3.
    """

    def __init__(self, ident, bones, mats, hitbox, anims, density=2.0, max_side=256, seed=None, scale=1.0):
        _check_id(ident, 'creature')
        if '/' in ident:
            raise ValueError('%s: creature ids cannot have folders (loaders use the file name)' % ident)
        self.id = ident
        self.bones = list(bones)
        self.mats = mats
        self.hitbox = hitbox
        self.anims = anims
        self.all_bones = [b for r in self.bones for b in r.walk()]
        names = [b.name for b in self.all_bones]
        dup = sorted({n for n in names if names.count(n) > 1})
        if dup:
            raise ValueError('%s: repeated bone names %s' % (ident, dup))
        if 'hitbox' in names:
            raise ValueError('%s: do not add a hitbox bone; it is generated from `hitbox`' % ident)
        for a, anim in anims.items():
            for b in anim.tracks:
                if b not in names:
                    raise ValueError('%s/%s: no bone named %s' % (ident, a, b))
        self.cubes = [(p, b) for b in self.all_bones for p in b.parts]
        if scale != 1.0:
            for p, _ in self.cubes:
                p.frm, p.to, p.origin = [v * scale for v in p.frm], [v * scale for v in p.to], [v * scale for v in p.origin]
            for b in self.all_bones:
                b.pivot = [v * scale for v in b.pivot]
            for a in anims.values():
                for ch in a.tracks.values():
                    if 'pos' in ch:
                        ch['pos'] = [(t, tuple(round(v * scale, 3) for v in val)) for t, val in ch['pos']]
            self.hitbox = (hitbox[0] * scale, hitbox[1] * scale)
            density /= scale
        for p, _ in self.cubes:
            p.within_45()     # a single-axis turn past 90 would read as three axes in Blockbench
        multi = ['%s (%s): %s' % (p.name, b.name, [a for a in p.angles() if a]) for p, b in self.cubes
                 if len([a for a in p.angles() if a]) > 1]
        if multi:
            raise ValueError('%s: cubes rotated on more than one axis (entity loaders reject them; use '
                             'geom.cube/limb or a child bone): %s' % (ident, '; '.join(multi)))
        self.model = Model(ident, [p for p, _ in self.cubes], mats, density=density)
        self.model.pack(max_side)
        self.model.paint(seed, frames=1)

    @property
    def warnings(self):
        return self.model.warnings

    def bbmodel(self):
        """Blockbench 'Generic Model' (free format) with bones, the hitbox bone and animations."""
        mod, ident = self.model, self.id
        els, ids = [], {}
        for i, (p, b) in enumerate(self.cubes):
            u = _uuid('creature', ident, 'cube', i)
            ids[i] = u
            faces = {}
            for f in FACES:
                x, y, w, h = mod.uv.get((i, f), (0, 0, 1, 1))
                faces[f] = {'uv': [x, y, x + w, y + h], 'texture': 0}      # loaders want every face textured
            els.append({'name': p.name, 'box_uv': False, 'rescale': False, 'locked': False, 'render_order': 'default',
                        'allow_mirror_modeling': True, 'from': _r4(p.frm), 'to': _r4(p.to), 'autouv': 0,
                        'color': i % 8, 'inflate': 0, 'origin': _r4(p.origin), 'rotation': p.angles(),
                        'faces': faces, 'type': 'cube', 'uuid': u})
        hw, hh = self.hitbox[0] * 8.0, self.hitbox[1] * 16.0
        hb = _uuid('creature', ident, 'hitbox-cube')
        els.append({'name': 'hitbox', 'box_uv': False, 'rescale': False, 'locked': False, 'render_order': 'default',
                    'allow_mirror_modeling': True, 'from': [-hw, 0, -hw], 'to': [hw, hh, hw], 'autouv': 0,
                    'color': 0, 'inflate': 0, 'origin': [0, 0, 0], 'rotation': [0, 0, 0],
                    'faces': {f: {'uv': [0, 0, 1, 1], 'texture': 0} for f in FACES}, 'type': 'cube', 'uuid': hb})
        uuids, count = {}, [0]

        def group(b):
            uuids[b.name] = _uuid('creature', ident, 'bone', b.name)
            kids = []
            for _ in b.parts:
                kids.append(ids[count[0]])
                count[0] += 1
            kids += [group(c) for c in b.children]
            return {'name': b.name, 'origin': _r4(b.pivot), 'rotation': [0, 0, 0], 'color': 0, 'uuid': uuids[b.name],
                    'export': True, 'mirror_uv': False, 'isOpen': False, 'locked': False, 'visibility': True,
                    'autouv': 0, 'children': kids}

        outliner = [group(b) for b in self.bones]
        outliner.append({'name': 'hitbox', 'origin': [0, 0, 0], 'rotation': [0, 0, 0], 'color': 0,
                         'uuid': _uuid('creature', ident, 'bone', 'hitbox'), 'export': True, 'mirror_uv': False,
                         'isOpen': False, 'locked': False, 'visibility': True, 'autouv': 0, 'children': [hb]})
        anims = []
        for name, a in self.anims.items():
            animators = {}
            for bn, channels in a.tracks.items():
                kfs = []
                for ch, keys in channels.items():
                    channel = {'rot': 'rotation', 'pos': 'position', 'scale': 'scale'}[ch]
                    for k, (t, v) in enumerate(keys):
                        v = (v, v, v) if isinstance(v, (int, float)) else v
                        kfs.append({'channel': channel, 'data_points': [{'x': v[0], 'y': v[1], 'z': v[2]}],
                                    'uuid': _uuid('creature', ident, 'kf', name, bn, ch, k), 'time': t, 'color': -1,
                                    'interpolation': 'catmullrom' if a.smooth else 'linear'})
                animators[uuids[bn]] = {'name': bn, 'type': 'bone', 'keyframes': kfs}
            anims.append({'uuid': _uuid('creature', ident, 'anim', name), 'name': name, 'loop': a.loop,
                          'override': False, 'length': a.length, 'snapping': 20, 'selected': False,
                          'anim_time_update': '', 'blend_weight': '', 'start_delay': '', 'loop_delay': '',
                          'animators': animators})
        side = mod.side
        tex = {'path': '', 'name': ident + '.png', 'folder': '', 'namespace': '', 'id': '0', 'width': side,
               'height': side, 'uv_width': side, 'uv_height': side, 'particle': True, 'use_as_default': False,
               'layers_enabled': False, 'sync_to_project': '', 'render_mode': 'default', 'render_sides': 'auto',
               'frame_time': 1, 'frame_order_type': 'loop', 'frame_order': '', 'frame_interpolate': False,
               'visible': True, 'internal': True, 'saved': True, 'uuid': _uuid('creature', ident, 'tex'),
               'source': 'data:image/png;base64,' + base64.b64encode(png_bytes(mod.px)).decode('ascii')}
        return {'meta': {'format_version': '4.10', 'model_format': 'free', 'box_uv': False}, 'name': ident,
                'model_identifier': ident, 'visible_box': [self.hitbox[0], self.hitbox[1], 0],
                'variable_placeholders': '', 'variable_placeholder_buttons': [], 'timeline_setups': [],
                'unhandled_root_fields': {}, 'resolution': {'width': side, 'height': side},
                'elements': els, 'outliner': outliner, 'textures': [tex], 'animations': anims}

    def pose(self, anim=None, t=0.0):
        """The cubes placed as at time `t` of `anim`, as a Model the renderer can draw."""
        a = self.anims.get(anim) if anim else None
        chain = {}

        def walk(b, parents):
            chain[b.name] = parents + [b]
            for c in b.children:
                walk(c, parents + [b])

        for r in self.bones:
            walk(r, [])
        parts = []
        for p, b in self.cubes:
            q = copy.deepcopy(p)
            for bb in reversed(chain[b.name]):
                ch = a.tracks.get(bb.name, {}) if a else {}
                s = _value(ch['scale'], t) if 'scale' in ch else 1.0
                s = s[0] if isinstance(s, tuple) else s
                if s != 1.0:
                    pv = bb.pivot
                    o2 = [pv[j] + s * (q.origin[j] - pv[j]) for j in range(3)]
                    q.frm = [o2[j] + s * (q.frm[j] - q.origin[j]) for j in range(3)]
                    q.to = [o2[j] + s * (q.to[j] - q.origin[j]) for j in range(3)]
                    q.origin = o2
                if 'rot' in ch:
                    kx, ky, kz = _value(ch['rot'], t)
                    q.rotate(rot(x=-kx, y=-ky, z=kz), bb.pivot)
                if 'pos' in ch:
                    px, py, pz = _value(ch['pos'], t)
                    q.move([-px, py, pz])
            parts.append(q)
        out = copy.copy(self.model)
        out.parts = parts
        out.display = None
        return out

    def bounds(self):
        vs = [v for p, _ in self.cubes for v in p.vertices()]
        return [min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]

    def bone_extents(self):
        """Largest cube span per bone, in units (loaders turn each bone into one item model)."""
        out = {}
        for b in self.all_bones:
            if b.parts:
                vs = [v for p in b.parts for v in p.vertices()]
                out[b.name] = max(max(v[i] for v in vs) - min(v[i] for v in vs) for i in range(3))
        return out
