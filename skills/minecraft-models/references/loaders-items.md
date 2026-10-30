# Item plugins

Every item target ships the same Java assets (models, textures, `items/` definitions, equipment)
inside the plugin's pack folder and a config that points at them. Configs marked **check** are a
starting point written from the plugin docs: field names change between plugin versions, so compare
them with the docs of the version installed before telling the user they are final.

For Bedrock add the `geyser` target. Its mapping expects each item to carry
`item_model = <ns>:<id>`; if the plugin assigns its own item model, read the real value from an
item in game (F3+H tooltip, or `/data get entity @s SelectedItem`) and use it as `model`.

## RPGRoll + SackResourcePack (`rpgroll` target)

```
rpgroll/SackResourcePack/content/<ns>/pack.yml + assets/<ns>/...   -> plugins/SackResourcePack/content/
rpgroll/Geyser-Spigot/packs + custom_mappings                       -> plugins/Geyser-Spigot/ (or Geyser-Velocity/)
rpgroll/RPGRoll-Items/packs/<ns>/<id>.yml                           -> plugins/RPGRoll-Items/packs/<ns>/
rpgroll/RPGRoll-Furniture/<ns>.example.yml                          merge into the furniture definitions
rpgroll/FreeMinecraftModels/models/<creature>.bbmodel               -> plugins/FreeMinecraftModels/models/
rpgroll/RPGRoll-Mobs/<ns>.example.yml                               the model block for each mob file
```

- SackResourcePack module: `pack.yml` (`id`, `name`, `version`, `author`, `namespace`, `priority`,
  `depends`, `description`) next to `assets/`. No `pack.mcmeta` (it generates one). Then
  `/srp rebuild` and, if the pack is uploaded, `/srp publish`.
- RPGRoll-Items: `material` (base item), `item-model: "<ns>:<id>"` (sets `item_model`),
  `equipment-model: "<ns>:<set>"` (worn armor) or `equipment-model: none` (a `helmet`-style item
  worn as its 3D model). Add stats, triggers and lore to the generated minimal files; `/item reload`.
- RPGRoll-Furniture: `model: <ns>:<id>` per furniture or variant, `hitbox` (`barrier` blocks or
  `interaction` width/height), `placement`. **check** the hitbox blocks against the model size.
- RPGRoll-Mobs: `model.model-engine-id: <creature id>` (a FreeMinecraftModels model). FMM plays
  spawn/idle/walk/death, RPGRoll-Mobs plays `attack` on hit and custom ones via `ANIMATION`.

### SHOOT, ammunition and sustained lasers

`Item(shot={...})` writes a `SHOOT` action under `triggers: RIGHT_CLICK` in the `rpgroll` target.
Other loaders export the visual assets but ignore `shot`. `examples/lasers.py` has a pistol,
beam rifle, plasma cannon, ammo cell and projectile. A beam rifle spec can use:

```python
shot={'amount': 2, 'range': 24, 'sustain': 6, 'particle': 'DUST', 'color': '#30C8FF',
      'ammo': 'ammo/laser_cell', 'sound': 'BLOCK_BEACON_AMBIENT', 'pitch': 2.0}
```

If that cell is an Item in the same spec, generated YAML uses `ammo: ammo_laser_cell`. A local
projectile `model: projectiles/plasma_bolt` becomes `<ns>:projectiles/plasma_bolt`; it has pack
assets but no RPGRoll-Items file. External ammo ids/model keys pass through unchanged.

| Parameter | Meaning |
|---|---|
| `amount`, `range` | damage per shot/pulse, maximum distance in blocks |
| `speed` | 0 (default): hitscan; positive: flying projectile speed in blocks/tick |
| `model` | ItemDisplay item model key for a projectile; needs `speed > 0` |
| `ammo` | RPGRoll item id, or `minecraft:<material>` for vanilla ammo; omitted = unlimited |
| `ammo-amount` | ammo spent per shot/pulse (default 1, minimum 1) |
| `no-ammo-sound`, `no-ammo-message` | failure sound (default `BLOCK_DISPENSER_FAIL`) and optional action-bar message |
| `sound`, `volume`, `pitch` | shot sound and its volume/pitch (both default 1) |
| `sustain` | visual beam lifetime in ticks, renewed by each hitscan pulse; 0 = single shot |

Ammo is checked before firing; insufficient ammo cancels the shot without partial consumption.
Creative players need to carry enough ammo but do not spend it. Vanilla ammo does not match
custom RPGRoll items made from that same material.

Ammo and `sustain` require the RPGRoll-Items changes intended for **1.1.8**, currently local and
unpublished. Do not assume the installed release supports them. With `speed=0` and `sustain=6`,
the beam follows aim every tick; holding right click on Java repeats a pulse every 4 ticks
(5/second at 20 TPS), refreshing the visual. Damage, ammo and sound apply per pulse, not per
visual tick. For sustained hits, target invulnerability is reset each pulse. After release, the
visual expires when its remaining ticks run out. `speed > 0` takes the projectile path and
ignores `sustain`.

In-game checks remain: held-click repetition through Geyser, knockback under repeated pulses,
ammo depletion and beam timing, and projectile pitch with GeyserDisplayEntity. The skill build
validates exported assets/configuration; it does not exercise server combat behavior.

## ItemsAdder (`itemsadder` target) — check

```
ItemsAdder/contents/<ns>/configs/<ns>.yml
ItemsAdder/contents/<ns>/models/item/<id>.json
ItemsAdder/contents/<ns>/textures/item/<id>.png
ItemsAdder/contents/<ns>/textures/armor/<set>/layer_1.png, layer_2.png
```

- Copy `contents/<ns>/` to `plugins/ItemsAdder/contents/`, then `/iazip`.
- Items use `resource: {material, generate: false, model_path: item/<id>}` (works for every client
  version). On 1.21.4+ only, ItemsAdder 4.0.13+ also accepts the newer `graphics:` section.
- Armor (ItemsAdder 4.0.9+, 1.21.2+ clients): `equipments: <set>: {type: armor, layer_1:
  armor/<set>/layer_1, layer_2: armor/<set>/layer_2}`, and each piece has `equipment: {id: <ns>:<set>}`.
  Layer textures: power-of-two sizes, no animation. A helmet worn as a 3D model omits `equipment.id`.
- Furniture: `behaviours: furniture: {entity: item_display, solid, hitbox: {length, width, height},
  placeable_on}`; hitbox max 3x3x3; `/iahitbox` shows it in game.
- Model texture references must include the namespace (`<ns>:item/<id>`); the build does that.
- Avoid uppercase in ids, namespaces and file names.

## Oraxen (`oraxen` target) — check

```
Oraxen/pack/assets/<ns>/...          -> plugins/Oraxen/pack/assets/
Oraxen/items/<ns>.yml                -> plugins/Oraxen/items/
```

- Items: `material`, `Pack: {generate_model: false, model: <ns>:item/<id>}`.
- Armor: the build writes `Components.equippable` (`slot`, `model: <ns>:<set>`) pointing at the
  equipment file in the pack. Older Oraxen versions use the CustomArmor naming
  (`<name>_armor_layer_1.png`, item ids `<name>_<piece>`): check docs.oraxen.com.
- Furniture: `Mechanics: furniture: {type: DISPLAY_ENTITY, hitbox: {width, height}}`.
- Reload with `/oraxen reload all`.

## Nexo (`nexo` target) — check

```
Nexo/pack/assets/<ns>/...            -> plugins/Nexo/pack/assets/
Nexo/items/<ns>.yml                  -> plugins/Nexo/items/ (subfolders allowed)
```

- Items: `material` and `Components: item_model: <ns>:<id>`, which replaces the `Pack` section on
  1.21.2+ and is exactly what the Geyser mapping matches.
- Armor: `CustomArmor: {id: <set>, layer1: <texture id>, layer2: <texture id>}`; Nexo fills the
  `equippable` component itself.
- Furniture: `Mechanics: furniture:` with `properties.display_transform: NONE` (the model as built in
  Blockbench) and a hitbox (`barriers`, `interactions`, shulker or ghast hitboxes; see
  docs.nexomc.com/mechanics/furniture-mechanic), plus seats and lights.
- Reload with `/nexo reload all`. Nexo does not set `item_model` by default (it uses
  `nexo:<item id>`), which is why the build writes it explicitly.

## Sources

- SackResourcePack and RPGRoll: docs.sackito.online
- ItemsAdder: wiki.itemsadder.com (Items > Resource, Armors, Furnitures)
- Oraxen: docs.oraxen.com (Item appearance, Custom armors, Furniture mechanic)
- Nexo: docs.nexomc.com (Items, Custom armor, Furniture mechanic)
