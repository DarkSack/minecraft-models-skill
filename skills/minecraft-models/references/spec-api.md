# Spec API (`from mcmodel import *`)

A spec is a Python file that `build.py` imports. It defines `NAMESPACE`, optionally `TITLE` and
`AUTHOR`, and `MODELS` (a list) or `models()` (a function returning the list) holding `Item`,
`ArmorSet` and `Creature` objects. Everything is plain Python: loops, helper functions and
shared materials are encouraged.

## Contents
1. Coordinates
2. Materials, ramps and painters
3. Shape helpers
4. Item and its styles
5. ArmorSet
6. Creature, Bone, Anim
7. Build command

## 1. Coordinates

- 1 unit = 1 pixel of a vanilla 16x16 item; a block spans 0..16; y is up.
- **Items** normally live in the 0..16 box around (8, 8, 8). `handheld` and `gun` models may be
  larger: the build moves/shrinks them into Java's -16..32 range automatically. Other styles
  must keep every from/to within that range. The inventory looks from +z (south); for `helmet`,
  the front faces -z.
- **Creatures** stand on y = 0, centered on x = z = 0, facing -z (north). Their right side is +x.
  A player is 32 units tall: legs 0..12, torso 12..24, head 24..32.
- Rotations are degrees `(x, y, z)`, applied X, then Y, then Z, around the part's `origin`.

## 2. Materials, ramps and painters

```python
ramp('#262c3a', '#7d8aa3', '#eef3ff', n=8)   # 8 colors dark -> light through the stops; 1 stop works too
material(kind, ramp, **options)                 # kind = painter name
```

| Painter | Looks like | Options (besides `glow`) |
|---|---|---|
| `metal` | brushed metal, bright bevel | `edge=ramp` glowing rim (animated), `flat=True` no bevel, `tone` |
| `plate` | metal panels, dark seams, corner rivets | `panel=12` (texture pixels, minimum 6), `tone=0.5` |
| `crystal` | sliding facets + sparkles (animated) | — |
| `energy` | bands running along the part (animated) | `cycles=2.0` |
| `rune` | dark stone/metal with pulsing glyphs (animated) | `energy=ramp` (required) |
| `grip` | wrapped handle | — |
| `trim` | guards, rims, bands with an engraved line | — |
| `gem` | cut gem with highlight | `pulse=True` (animated) |
| `orb` | swirling energy (animated) | — |
| `wood` | planks with grain | `tone` |
| `bone` | bone/ivory with cracks | — |
| `scales` | staggered scales | `size=4` |
| `skin` | skin/leather blotches | `cell=3`, `tone`, `flat=True` |
| `fur` | strands, darker at the root | `tone` |
| `cracked` | rock with glowing cracks | `energy=ramp` (required), `every=55` (higher = fewer cracks) |
| `cloth` | folds | `hem=ramp`, `torn=True`, `tone` |
| `eye` | bright center, dark rim | — |
| `flat` | one color with slight noise | `tone` (ramp index) |

Common options: `glow=0..15` (Java `light_emission` for every part of that material; halo in
previews), `animate=True` (force texture frames). Animated materials make a 16-frame strip with
`.png.mcmeta` on Java; Bedrock shows frame 0 (attachables cannot animate textures).

## 3. Shape helpers

All return a `Part` (or a list of them). `mat` is a key of the model's material dict.

| Helper | Use |
|---|---|
| `box(name, center, size, mat, r=None, light=None, hide=())` | the basic cube, rotating around its center |
| `bevel(name, center, size, mat, edge=0.5, r=None, light=None)` | three overlapping inset boxes: stepped chamfers for metal/stone |
| `tube(name, center, length, radius, mat, axis='x', light=None, round=False)` | two unrotated boxes forming a stepped octagonal pipe; `round=True` rotates the second square 45 degrees |
| `rivets(name, p0, p1, n, mat, size=0.6, light=None)` | studs evenly spaced between two 3D points |
| `blade(name, base, tip, width, depth, mat, edge=None, segments=4, taper=0.55, z=8, light=None)` | tapered xy blade with a point; `edge` is an optional bright material key |
| `Part(name, frm, to, mat, r=None, origin=None, ...)` | a cube by corners, rotating around `origin` |
| `bar(name, p0, p1, width, depth, mat, z=8, tilt=0)` | beam between two (x, y) points: blades, shafts, limbs |
| `curve(name, points, widths, depth, mat, z=8)` | beams along a polyline; widths `[start, end]` or one per segment |
| `arc(center, r, a0, a1, n, ry=None)` | points on an arc (degrees, counter-clockwise from +x) for `curve` |
| `orb(name, c, radius, mat, light=15)` | three cubes turned 45 degrees on x, y and z that read as a sphere |
| `ring(name, c, radius, n, size, mat, tilt=0, axis='y')` | `n` cubes on a circle (guards, halos, orbiting runes) |
| `spikes(name, p0, p1, n, length, width, mat, side=1, lean=0)` | spikes along a line, to one side |
| `cube(name, center, size, mat, axis=None, angle=0)` | single-axis cube for creatures |
| `limb(name, p0, p1, thick, mat, width=None)` | single-axis beam between two 3D points sharing one coordinate |
| `mirror(part)` | the part mirrored across x = 0 |
| `rotate_parts(parts, rot(x, y, z), center)`, `move_parts(parts, (dx, dy, dz))` | transform a group |
| `scale_parts(parts, k, center)` | resize cubes and pivots uniformly in place, keeping rotations |

`hide={'down', ...}` skips faces that are always covered (saves texture space). Name parts
meaningfully: names show up in Blockbench and in error messages.

Rotations beyond 45 degrees on one axis are rewritten automatically as a quarter turn baked into the
box (same solid), so they stay readable by old Java clients.
`tube()` defaults to cross-sections `[s, s-2c]` and `[s-2c, s]`, where `s=2*radius` and
`c=0.293*s`. This avoids adding an axis to the automatic handheld tilt. `round=True` preserves
the rotated-square version; combined with the handheld tilt it can require Java 1.21.11+.

## 4. Item

```python
Item(id, parts, mats, style='handheld', name=None, base=None, grip=(4, 4), wears=None,
     density=4, seed=None, hand_scale=1.0, shot=None)
```

| style | Build it like this | Default `base` |
|---|---|---|
| `handheld` | sword, axe, pickaxe, staff, standing up (tip +y, pommel at the bottom); tilted 45 degrees for you, the pommel goes in the hand, longer than a sword is scaled down in the hand | `iron_sword` |
| `gun` | side profile, barrel toward +x; `grip=(x, y)` is the hand point | `iron_horse_armor` |
| `rod` | like `handheld`, held like a fishing rod | `fishing_rod` |
| `flat` | small items held like a vanilla sprite item (gem, food, coin) | `paper` |
| `object` | 3D trinkets shown three-quarter in the inventory (lantern, potion, totem, armor icons) | `paper` |
| `helmet` | worn on the head: center (8, 8, 8) at the head center, front -z, head is about 12.8 units wide, top of the head at y = 14.4 | `iron_helmet` |
| `furniture` | placed with an ItemDisplay, transform NONE: block 0..16, floor at y = 0 | `paper` |
| `projectile` | ItemDisplay fired by RPGRoll SHOOT: nose toward +z, centered around (8, 8, 8) | `paper` |

- `id`: lowercase, may contain folders (`weapons/ember_sword`). Becomes `<ns>:<id>` (item model),
  `<ns>:item/<id>` (model file) and `<ns>:<id with _>` on Bedrock.
- `name`: display name for Geyser and plugin configs.
- `base`: the vanilla item it rides on: its behavior (tool speed, armor slot, food) and what players
  without the pack see. Pick something that makes sense on its own.
- `wears=(armor_set_id, piece)` makes it an armor piece (`helmet|chestplate|leggings|boots`): Java
  uses the set's equipment layers, Bedrock switches to the armor geometry when worn. Base defaults
  to `iron_<piece>`. Use style `object` for the inventory model.
- `density`: texture pixels per unit (4 is crisp; the build lowers it if the atlas would pass 256 px).
- `hand_scale`: multiplier of the normal held size; e.g. `1.7` makes a greatsword larger than a
  vanilla sword. It preserves the grip point. First-person enlargement is softened to keep the
  screen usable; Java display scales cap at 4 and translations at ±80 (warnings on scale caps).
  Automatic range fitting applies only to `handheld` and `gun`; inventory fitting stays automatic.
- `shot`: a dict of RPGRoll SHOOT parameters, exported under `triggers: RIGHT_CLICK` only by
  `rpgroll`. A local `model` id becomes `<ns>:<id>`; a local `ammo` id becomes its flattened item
  id (`ammo/laser_cell` -> `ammo_laser_cell`). External values pass through. See
  [loaders-items.md](loaders-items.md) for ammunition and sustained beams, and `examples/lasers.py`.
- `projectile` exports pack assets, Geyser mappings and previews, but no RPGRoll-Items YAML;
  refer to its model from a gun's `shot` with `speed > 0`. Bedrock needs GeyserDisplayEntity.
- Furniture front: most plugins turn furniture to face the player. Build one, test it, and if it
  faces backward flip the whole model: `rotate_parts(parts, rot(y=180), (8, 8, 8))`.

## 5. ArmorSet

```python
ArmorSet(id, ramp=None, accent=None, layers=None, open_face=True, detail=1, extras=None,
         mats=None, density=4, seed=None)
```

Paints the two 64x32 worn layers on the vanilla humanoid map from an 8-color `ramp` (plates,
edges, rivets; `accent` ramp adds a gem/buckle) or loads your own `layers=('layer_1.png',
'layer_2.png')` (64x32 or 128x64...). Layer 1: helmet, chestplate (torso + arms), boots. Layer 2:
leggings. `open_face=False` closes the helmet front. Pieces are separate `Item`s with `wears=`.

`detail=2` paints 128x64 layers with finer borders and bevels; `detail=1` paints 64x32. Imported
`layers` keep their own resolution. `extras={piece: {bone: [parts]}}` adds worn 3D parts on Bedrock
using `mats` (and `density`/`seed` for their atlas). Pieces are `helmet`, `chestplate`, `leggings`,
`boots`; bones are `head`, `body`, `right_arm`, `left_arm`, `right_leg`, `left_leg`.

Build extras in player space: feet at (0, 0, 0), front -z, right +x, shoulders at (±5, 22, 0),
hips at (±1.9, 12, 0). Pair mirrored parts with `mirror()`. Each piece also needs an `Item` with
`wears=(set_id, piece)` in MODELS. Java shows only the worn layers; a separate `helmet`-style Item
without `wears` can supply a 3D helmet on both editions. `worn_model()` returns a stand-in player
with all extras for previewing; it does not include the worn layers or separate helmet item.
See `examples/titans.py`. Bedrock extras still need an in-game client check.

## 6. Creature

```python
Creature(id, bones, mats, hitbox=(width, height), anims={name: Anim}, density=2.0,
         max_side=256, seed=None, scale=1.0, max_bone=48)
Bone(name, pivot, parts=(), children=())
pair(name, pivot, parts, children=())   # -> (name_r at +x, name_l mirrored); children are pairs too
Anim(length, loop='loop'|'once'|'hold', tracks={bone: {'rot'|'pos'|'scale': [(t, (x, y, z)), ...]}}, smooth=True)
wave(length, amp, base=(0, 0, 0), phase=0.0, n=8, times=1)   # looping sine keys
spin(length, axis='y', steps=4)                                # full-turn keys
```

- Wrap everything in a `root` bone at (0, 0, 0) so `death` and `spawn` can move the whole body.
- Bone pivots are the joints: shoulder, hip, neck. Cubes rotate with their bone.
- Bone name prefixes carry loader behavior: `h_` head (all three loaders), `hi_` head with children
  (ModelEngine, BetterModel), `tag_...` nametag anchor, `p_` seat (ModelEngine, BetterModel),
  `mount_` seat (FreeMinecraftModels). See `loaders-entities.md`.
- Keyframe values follow Blockbench: rotation x/y are negated compared to math (arm forward =
  negative x, lean forward = positive x); position x is negated, z = -2 moves forward; scale is a
  number or (x, y, z).
- Twins from `pair()` are mirrored geometry, not mirrored animation: for a symmetric motion give the
  `_l` bone the same x rotation and the negated y and z (a right leg raised with z = 40 pairs with
  the left one at z = -40). A walk cycle offsets the twins by half a cycle (`phase=0.5`).
- `scale` builds a boss from a mob-sized design (cubes, pivots, position keys and hitbox) and
  keeps texture detail by reducing density proportionally.
- `max_bone=48` automatically moves the cubes of wide bones into child bones `<bone>_p1`,
  `_p2`, etc., preserving animation inheritance. Head tags survive; seat and other behavior
  tags stay on the original parent. A single oversized cube cannot be split: keep each cube's
  rotated bounds within the limit after scaling. The build warns when one still exceeds it.
- Name animations as the loaders expect: `idle`, `walk`, `attack`, `death`, `spawn` (others are
  played by the plugin on demand).

## 7. Build

```bash
python scripts/build.py SPEC.py --out OUT --targets t1,t2|all [--ns NAME] [--formats 46-97] [--author NAME]
python scripts/selftest.py      # after changing mcmodel/ itself
```

Targets: `vanilla geyser rpgroll itemsadder oraxen nexo` (items, armor, furniture) and
`rpgroll fmm modelengine bettermodel` (creatures). Previews and `.bbmodel` files are always written.
