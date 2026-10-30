---
name: minecraft-models
description: >-
  Create original Minecraft 3D models as code and export them for Java and Bedrock: weapons, tools,
  trinkets, helmets, armor sets (worn look), furniture, mobs and animated bosses. One Python spec
  builds textures, Java item models and item definitions (1.21.4+), equipment layers, Blockbench
  .bbmodel files, Bedrock attachables + icons, Geyser custom item mappings, and ready-to-copy folders
  for FreeMinecraftModels, ModelEngine, BetterModel, ItemsAdder, Oraxen, Nexo, RPGRoll and
  SackResourcePack, plus PNG previews to check the result. Use it whenever someone wants a custom
  Minecraft item, weapon, armor, furniture, mob or boss model, a resource pack model, a Blockbench
  model, a Geyser/Bedrock version of a Java model, or asks how to install models in one of those
  plugins, even if they do not say "model". También en español: modelo 3D de Minecraft, arma,
  herramienta, armadura, mueble, mob, jefe, textura, paquete de recursos, Bedrock, Geyser.
license: MIT
---

# Minecraft models

You describe the model as a small Python spec made of cubes and materials, and `scripts/build.py`
turns it into everything the game and the plugins need, plus preview images you inspect before
delivering. Textures are painted by code, so nothing is copied from Mojang or anyone else. The
only requirement is Python 3.8+ (no packages).

Paths below are relative to this skill's folder. Run the scripts with that folder's absolute path.

## 1. Pin down the request

Settle these before writing anything; ask only what you cannot infer:

| Question | Why it matters | Default |
|---|---|---|
| What is it: held item, helmet/hat, armor set, furniture, mob, boss? | Picks `Item` style, `ArmorSet` or `Creature` | — |
| Which plugin or loader shows it? | Picks the build targets (table below) | `vanilla` + `geyser` for items, `fmm` for creatures |
| Bedrock players (Geyser)? | Adds the `.mcpack` + mapping | yes if they mention Geyser/Bedrock |
| Java versions? | Rotations allowed, pack formats | 1.21.4+ (`--formats 46-97`) |
| Namespace | Every id lives in it | the server or pack name, lowercase |
| Vanilla base item | Behavior, and what players without the pack see | per style (see spec-api) |

| They use | Targets |
|---|---|
| A plain resource pack / datapack / their own plugin | `vanilla` (+ `geyser`) |
| Geyser for Bedrock | `geyser` (on top of any item target) |
| RPGRoll (Items, Furniture, Mobs) with SackResourcePack | `rpgroll` (includes its Geyser files and FMM models) |
| ItemsAdder / Oraxen / Nexo | `itemsadder` / `oraxen` / `nexo` (+ `geyser`) |
| FreeMinecraftModels / ModelEngine / BetterModel | `fmm` / `modelengine` / `bettermodel` |

## 2. Write the spec

Copy the closest example and edit it: `examples/arsenal.py` (sword, pickaxe, pistol, crown,
lantern, chair, armor set), `examples/bestiary.py` (a mob and a boss with animations),
`examples/titans.py` (huge weapons, bulky armor, giant boss) or `examples/lasers.py` (ammo cells,
laser pistol, sustained beam rifle, plasma cannon/projectile). Read
`references/spec-api.md` for the full API and `references/design.md` for proportions, palettes and
animation timing. Put the spec in the user's project (e.g. `models/<pack>.py`), not in this skill.

The rules that matter most, and why:

- **Build items upright in the 0..16 box, around (8, 8, 8).** Display transforms (hand, inventory,
  head, ground) are computed from the style, so the same cubes look right everywhere. A `handheld`
  item is built tip-up and tilted for you like a vanilla sword.
- **Large `handheld` and `gun` weapons fit into Java's -16..32 box automatically.** Build at design
  size and set `hand_scale` for a larger held weapon. Other item styles must stay within that box.
  Use the default unrotated `tube()` for handles; `round=True` can combine with the handheld tilt
  into rotations that need Java 1.21.11+.
- **Prefer single-axis rotations in 22.5 degree steps.** They work on every 1.21.4+ client. Free
  angles need 1.21.6+, multi-axis rotations 1.21.11+. The build prints the oldest version each item
  needs; tell the user when it is above what they run.
- **Creatures face -z, feet at y = 0, one rotation axis per cube.** Entity loaders reject
  multi-axis cubes; use `cube()`/`limb()` and child bones. Name head bones `h_...`. Do not add a
  `hitbox` bone yourself: pass `hitbox=(width, height)` in blocks.
- **Giant creatures split wide bones automatically** (`max_bone=48`), keeping the original animation
  parents. Each individual cube must still fit after `scale`. `ArmorSet(detail=2, extras=..., mats=...)`
  adds finer layers and Bedrock worn 3D pieces; Java shows layers plus a separate 3D helmet if supplied.
- **`shot` exports RPGRoll SHOOT actions only.** Ammo and sustained beams need the local changes
  intended for RPGRoll-Items 1.1.8 (not yet published). Damage/ammo apply per pulse; read
  `references/loaders-items.md`. A `projectile` Item supplies the model; Bedrock needs GeyserDisplayEntity.
- **Use 3 to 6 materials with real ramps.** Ramps go dark to light; painters use the ends for
  bevels and highlights. Glow (`glow=`) only on what should emit light.
- **Ids are lowercase** (`a-z 0-9 _ - .`, folders with `/`). Never use the `minecraft` namespace.

## 3. Build and look

```bash
python <skill>/scripts/build.py models/mypack.py --out build/mypack --targets vanilla,geyser
```

Then open the previews with your image-reading tool, every time, before answering:

- `preview/items.png`: inventory icons (these are also the Bedrock icons). Is each item readable
  at 64 px, centered, not cut?
- `preview/items_3d.png`: three-quarter views. Proportions, gaps between parts, floating cubes.
- `preview/armor_<set>.png`: the two worn layers.
- `preview/armor_<set>_3d.png`: optional Bedrock extras on a stand-in player, front/side/back;
  it excludes the layer textures and separate helmet. Check actual bone binding in game.
- `preview/creature_<id>.png`: rest pose, then each animation at 30%, front 3/4 and side. Limbs
  should swing from joints, nothing should detach; the side view shows the front on the left.

Fix and rebuild until it reads well. Two or three passes is normal. Read the `WARN` and `NOTE`
lines: they flag what would only break in game (oversized bones, missing idle/walk, rotations that
need newer clients, lowered texture density).

## 4. Deliver

The output folder has one subfolder per target with the exact plugin layout, `blockbench/` with
editable `.bbmodel` projects, and `INSTALL.md` with copy-and-reload steps. Tell the user:

1. Where to copy each folder and which command reloads it (it is in `INSTALL.md`).
2. That the Geyser server needs a full restart, not `geyser reload`, to pick up new packs.
3. What to check in game (see the checklist in `references/bedrock-geyser.md` and `references/java.md`).
4. Which parts of a plugin config were generated as a starting point and must be checked against
   their plugin version (`references/loaders-items.md` lists them).

Loader details live in the references; read only the ones for the targets in play:

- `references/java.md`: item definitions, model limits, display, equipment, pack formats by version.
- `references/bedrock-geyser.md`: mapping format v2, attachables, icons, worn armor, furniture, traps.
- `references/loaders-entities.md`: FreeMinecraftModels, ModelEngine, BetterModel (folders, bone tags, animations).
- `references/loaders-items.md`: RPGRoll + SackResourcePack, ItemsAdder, Oraxen, Nexo.

## Traps worth knowing up front

- Bedrock caches packs by uuid + version and never re-downloads the same pair. The build derives the
  version from the content (kept under 65536, or Bedrock disconnects), so every change reaches players.
- Bedrock attachables ignore texture animation (`uv_anim`): a full animated strip shows up squashed as
  stripes. The build exports frame 0 to Bedrock; animated textures only move on Java.
- Bedrock fails on pack paths of 80+ characters; keep ids short.
- A Geyser mapping matches by Java base item + `item_model`. If a plugin gives the item a different
  `item_model` than `<namespace>:<id>`, Bedrock players see the vanilla item.
- SackResourcePack builds its zip before FreeMinecraftModels converts new models: run `/srp rebuild`
  after adding creatures.

## When the user brings existing files

This skill builds models from specs. If they hand over a finished `.bbmodel` or Java model and only
need it installed or converted, use the references for the folder layout and file formats
(`bedrock-geyser.md` shows a full attachable and mapping) and write those files directly. To rework
the model, rebuild it as a spec: look at their model or screenshot and reproduce the shapes with cubes.

Answer in the user's language; keep spec code and ids in English.
