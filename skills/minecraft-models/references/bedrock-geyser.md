# Bedrock through Geyser

Bedrock cannot read Java models. Geyser maps each custom Java item to a Bedrock item defined in a
resource pack (`.mcpack`) that Geyser sends to Bedrock players.

## What the build writes

```
geyser/packs/<ns>.mcpack                 resource pack for Bedrock players
geyser/custom_mappings/<ns>.json         which Java item becomes which Bedrock item
```

Inside the `.mcpack`:

```
manifest.json                                    uuid fixed per namespace, version from content CRC
textures/item_texture.json                       icon shorthands -> textures/<ns>/icons/<id>
textures/<ns>/icons/<id>.png                     64x64 inventory icon rendered from the model
textures/<ns>/<ns>_<id>.png                      model texture (frame 0)
models/entity/<ns>_<id>.geo.json                 geometry: bones geyser_custom > _x > _y > _z
animations/<ns>_<id>.animation.json              Java display transforms as animations (hands, head)
attachables/<ns>_<id>.json                       ties identifier, geometry, texture and animations
render_controllers/<ns>.render_controllers.json  only for worn armor (switches to armor geometry)
textures/<ns>/armor_<set>_<1|2>.png              worn armor layers
```

Install: copy `packs/` and `custom_mappings/` into `plugins/Geyser-<platform>/` on the server that
runs Geyser (the proxy if Geyser is on Velocity/BungeeCord), set `enable-custom-content: true` in
Geyser's config and **restart** that server. `geyser reload` does not load new packs.

## Mapping format 2 (Geyser 2.9.3+, Java 1.21.4+)

```json
{
  "format_version": 2,
  "items": {
    "minecraft:diamond_sword": [
      {
        "type": "definition",
        "model": "demo:weapons/ember_sword",
        "bedrock_identifier": "demo:weapons_ember_sword",
        "display_name": "Ember Sword",
        "bedrock_options": {"icon": "demo_weapons_ember_sword", "allow_offhand": true, "display_handheld": true}
      }
    ]
  }
}
```

- The key is the Java base item; `model` is the `item_model` the server puts on the item.
  Both must match or Bedrock players see the vanilla item.
- `bedrock_identifier` must be unique and not in the `minecraft` namespace.
- Other `bedrock_options`: `creative_category` (`none|construction|nature|equipment|items`; needed
  for items that appear in recipe outputs), `creative_group`, `protection_value` (visual armor
  points), `tags`.
- `components` can override Java components for Bedrock (`minecraft:consumable`, `food`,
  `equippable`, `max_stack_size`, `tool`, ...); `rarity` and attribute modifiers are translated.
- `predicate` picks a different Bedrock item by state (`condition`: broken, damaged,
  custom_model_data, has_component, fishing_rod_cast; `match`: charge_type, trim_material,
  context_dimension, custom_model_data; `range_dispatch`: damage, count, custom_model_data).
- Legacy servers that still use CustomModelData: `{"type": "legacy", "custom_model_data": 1234, ...}`.
- Only one definition without predicates per (base item, model) pair.

## Cube conversion (Blockbench's, verified in game)

Java cube `from`/`to` around (8, 8, 8) -> Bedrock cube `origin = [-(to.x - 8), from.y, from.z - 8]`,
`size` unchanged; the Java rotation origin `o` -> Bedrock `pivot = [-(o.x - 8), o.y, o.z - 8]`;
rotation `(x, y, z)` -> `[-x, -y, z]`. UVs are copied per face in pixels.

## Worn armor

The attachable of each armor piece carries two geometries: the 3D item model (`default`) and
`geometry.player.armor.<helmet|chestplate|leggings|boots>` (`worn`) with material `armor` and the
layer texture. A render controller switches on `v.worn = c.item_slot == '<head|torso|legs|feet>'`.
The base item must be wearable (e.g. `iron_chestplate`) so Bedrock equips it.

## Furniture (ItemDisplay)

Geyser shows Java ItemDisplay entities only with the **GeyserDisplayEntity** extension
(`plugins/Geyser-*/extensions/`). The build binds furniture geometry to that entity's
`geyser_z` bone and adds a `placed` animation that applies the display offset (measured in the
client: x and y times 0.6, z times -2.6, plus one block of height). Without the extension,
Bedrock players see nothing.

## Traps

- Bedrock caches each pack by uuid + version. Same version = no re-download, so players keep the
  old look. The build sets the patch version from the content CRC (under 65536: higher versions
  make Bedrock drop the connection).
- Attachables ignore `uv_anim`: an animated strip gets squashed onto each face as stripes. Only
  frame 0 goes to Bedrock.
- Any path inside the pack of 80+ characters breaks loading. Keep ids short.
- Two Java items on the same model need two Bedrock identifiers (one per base item).
- Bedrock has no 3D inventory: icons are 2D renders of the model.
- Entity models from FreeMinecraftModels/ModelEngine/BetterModel reach Bedrock through those
  plugins' own Bedrock support (or not at all); this skill does not export creature packs for
  Bedrock.

## In-game checklist (Bedrock client)

- The pack downloads on join (watch for "Downloading resource packs").
- Inventory icon, held in first and third person, dropped, in an item frame, worn (armor/helmet).
- If an item shows as vanilla: mapping key or `model` mismatch, or Geyser not restarted.
- If it is invisible or stretched: geometry/texture mismatch; rebuild and restart Geyser.
