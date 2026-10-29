# Java Edition (1.21.4 and later)

## What the build writes

```
assets/<ns>/items/<id>.json            item model definition: {"model": {"type": "minecraft:model", "model": "<ns>:item/<id>"}}
assets/<ns>/models/item/<id>.json      the cube model (elements, display, light_emission)
assets/<ns>/textures/item/<id>.png     its texture (+ .png.mcmeta when animated: a vertical strip of frames)
assets/<ns>/equipment/<set>.json       worn armor: layers humanoid + humanoid_leggings -> <ns>:<set>
assets/<ns>/textures/entity/equipment/humanoid/<set>.png            layer 1 (64x32)
assets/<ns>/textures/entity/equipment/humanoid_leggings/<set>.png   layer 2 (64x32)
pack.mcmeta                            pack_format + supported_formats (old clients), min_format + max_format (1.21.9+)
```

An item shows the model when it carries the `item_model` component `<ns>:<id>` (the file name in
`items/`). Worn armor uses the `equippable` component with `asset_id` `<ns>:<set>`.

Quick test with the vanilla pack loaded:

```
/give @s diamond_sword[item_model="demo:weapons/ember_sword"]
/give @s iron_chestplate[item_model="demo:armor/ember_chestplate",equippable={slot:"chest",asset_id:"demo:ember"}]
```

## Model limits (why the build checks them)

- `from`/`to` within -16..32 on every axis. Beyond that the model fails to load.
- Element rotation: one axis, -45..45 (`axis` + `angle`). Until 1.21.5 only multiples of 22.5;
  1.21.6 (25w16a) allows any angle; 1.21.11 (25w46a) allows several axes (`x`, `y`, `z` fields)
  and angles past 45. The build writes the classic form whenever it can and prints the oldest
  version each item needs.
- `light_emission` 0-15 per element (1.21.2+): the part ignores darkness.
- `display` transforms: translation is clamped to -80..80, scale to 4. Translation applies before
  rotation. Positions: `thirdperson_righthand/lefthand`, `firstperson_righthand/lefthand`, `gui`,
  `head`, `ground`, `fixed` (item frame), `on_shelf` (1.21.9+).
- `gui_light: front` lights the model like a flat sprite (used for held items); `side` (default)
  like a block.

## Pack formats

| Version | Resource pack format |
|---|---|
| 1.21.4 | 46 (item model definitions, `items/` folder) |
| 1.21.5 | 55 |
| 1.21.6 | 63 |
| 1.21.7-1.21.8 | 64 |
| 1.21.9-1.21.10 | 69 (min_format/max_format introduced) |
| 1.21.11 | 75 (multi-axis element rotation) |
| 26.1 / 26.2 / 26.3 | 84 / 88 / 97 |

Pass `--formats LOW-HIGH` to match what the server supports. Check the current numbers on the
Minecraft Wiki ("Pack format") when a new version is out.

## Equipment layers

`equipment/<set>.json` lists layers per type; a missing type means nothing is drawn for that slot
(except the head, which then shows the item model with its `display.head` transform: that is how
`helmet`-style items are worn, with `equipment-model: none` / no `asset_id`). Layer types besides
humanoid: `wings`, `wolf_body`, `horse_body`, `llama_body`, `happy_ghast_body`, saddles. Textures
resolve to `textures/entity/equipment/<layer_type>/<name>.png`.

## In-game checklist

- F3+T reloads resource packs on the client; watch the log for "Unable to load model".
- Check first person, third person (F5), inventory, item frame, dropped on the ground.
- Missing texture (purple/black) = wrong texture id or path; missing model (no item at all or the
  vanilla look) = wrong `item_model` or a model file that failed to load.
