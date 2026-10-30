# Designing models that read well in Minecraft

## Sizes to compare against

| Thing | Size in units (16 = 1 block) |
|---|---|
| Vanilla sword sprite | 16 x 16 diagonally, about 22.6 tip to pommel |
| Player | 32 tall: legs 12, torso 12 (8 wide, 4 deep), head 8x8x8, arms 4x12x4 |
| Zombie / skeleton hitbox | 0.6 x 1.95 blocks |
| Iron golem hitbox | 1.4 x 2.7 blocks |
| Ravager / warden | about 2 x 2.2 / 0.9 x 2.9 blocks |
| A table / chair | top at 12-16 / seat at 7-8, back up to 18-20 |

## Shape

- **Silhouette first.** At 64 px in the inventory and at 10 blocks away, only the outline
  survives. Exaggerate what defines the object (a big guard, a hooked blade, horns) and skip
  detail smaller than 1 unit.
- **Thickness 1-3 units** for blades and flat parts; thinner than 0.6 flickers or disappears.
- **Overlap joints by a little** (0.3-0.6) so no gaps show when parts rotate. `curve()` and
  `limb()` already overlap.
- **Cube budget:** 6-20 cubes for an item, 20-60 for a mob, up to ~150 for a boss. More cubes cost
  texture space and client performance.
- **Weapons longer than a sword** can be built at full design size with `handheld` or `gun`:
  the build fits the geometry into -16..32. Set `hand_scale` to make the held weapon larger
  than its normal sword/gun fit. Other styles still require coordinates inside the Java box.

## Large weapons and bulky armor

Start from `examples/titans.py` for a greatsword, warhammer or heavy armor, and `examples/lasers.py`
for a pistol, sustained beam rifle or plasma cannon. Keep a strong grip, a thick spine and one
main glow line. `blade()` adds a tapered edge; `bevel()` gives metal heads and plates volume;
`plate` paints panel seams without spending extra cubes. Use `rivets()` sparingly: small studs
become noise in inventory icons and consume atlas space. Set `density=3` for detailed large
items if needed, then inspect any density warning and the 256 px atlas result.

Use the default unrotated `tube()` for handles on handheld weapons. A tube with `round=True`
adds a 45-degree turn that can combine with the weapon tilt into a Java 1.21.11 rotation.
Check the reported minimum version per item after building.

For armor, `detail=2` improves the worn layer borders. Add Bedrock pauldrons, knee guards and toe
caps through `ArmorSet.extras` in player coordinates. Inspect `armor_<set>_3d.png` for floating
parts and clipping; its grey player shows extras only. Java uses the layers, with a separate
`helmet` item if a 3D head silhouette is needed. Confirm movement on a real Bedrock player.

## Giant bosses

Design at mob size, then use `Creature(scale=3)` as in the colossus. Keep every cube small enough
that its rotated span after scaling is at most `max_bone` (48 by default). Wide groups split
automatically into child bones that follow the animated parent; individual cubes do not split.
Keep animation tracks on the original joint names. Recheck the scaled hitbox, shoulder/hip
pivots and front/side attack poses. Increase wind-up and recovery times for the boss's weight.

## Color

- 3 to 6 materials per model. One main material, one secondary, one accent, maybe a glow.
- Ramps from a dark, desaturated shadow to a light, slightly warmer highlight read best:
  `ramp('#262c3a', '#7d8aa3', '#eef3ff')`. Avoid pure black and pure white ends.
- Contrast between neighboring parts matters more than detail inside a part.
- Glow (`glow=`) on 10-20% of the model at most: cores, eyes, runes, flames. Everything glowing
  reads as flat.
- Animated materials (energy, crystal, rune, orb) are striking on Java; on Bedrock they are a still
  frame, so the model must still look right without the motion.

## Animation timing (seconds)

| Animation | Length | Notes |
|---|---|---|
| `idle` | 2-4, loop | breathing: 0.3-0.5 units of body bob, a few degrees of arm sway, head look-around |
| `walk` | 0.8-1.2 (big mobs 1.4-1.8), loop | legs +-20-35 degrees opposite to arms, body bob at twice the frequency |
| `attack` | 0.4-0.8 (bosses 1-1.5), once | wind-up 40%, strike 15%, recover 45% |
| `death` | 1-2, hold | fall over (root rotates 85-90 degrees) and stay down |
| `spawn` | 1-1.5, once | rise from the ground (root position y from -height to 0) |

Use `wave()` for loops (it closes on itself) and explicit keys for one-shots. Big creatures move
slower; scale the timing up with size.

## Reading the previews

- Icons cut at the border or tiny in the slot: the item is unusually long or off-center; the
  inventory fit is automatic, so check the cubes themselves (a stray part far away shrinks it).
- Grey or flat-looking: ramps too narrow; widen the gap between the dark and light stops.
- Noisy: painters with strong patterns (cracked, scales, rune) on big faces; lower `every`, raise
  `size`, or use `skin`/`metal` for large areas.
- Creature limbs detaching in a pose: the cube belongs to the wrong bone, or the bone pivot is not
  at the joint.
- Creature seen from the back in the 3/4 view: it faces +z; rotate it 180 degrees.
