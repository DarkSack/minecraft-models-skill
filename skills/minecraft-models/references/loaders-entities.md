# Entity model loaders

All three read a Blockbench **Generic Model** (`.bbmodel`, `model_format: free`) with bones,
cubes, one embedded texture and animations, and generate their own resource pack from it. The
build writes the same file for all three; what differs is the folder, the bone tags and which
animations play by themselves. Common rules the build enforces:

- The model faces -z (north), feet at y = 0, centered on x = z = 0.
- One rotation axis per cube (FreeMinecraftModels rejects the rest; the others are safer with it).
- Every face of every cube has a texture.
- A top-level bone `hitbox` with one cube the size of the mob (generated from `hitbox=`).
- Each bone becomes one item model on the client: keep a bone's cubes under ~48 units across.

## FreeMinecraftModels (MagmaGuy, free, GPLv3)

- Folder: `plugins/FreeMinecraftModels/models/` (subfolders scanned). Model id = file name.
- Reload: `/fmm reload` (regenerates `output/FreeMinecraftModels.zip`, its own resource pack).
- Bones: `hitbox` (collision), `tag_name` (nametag anchor), `h_` prefix (turns with the look),
  `mount_` prefix (rideable seat).
- Animations played on its own: `spawn`, `idle`, `walk`, `attack`, `death`. Any other name is
  played by whatever plugin drives the entity.
- Java 1.21.4+ server (Paper/Spigot). Bedrock uses a fallback renderer: check models on a real
  Bedrock client.
- With RPGRoll-Mobs: `model.model-engine-id: <model id>` in the mob file; RPGRoll-Mobs plays
  `attack` on hit and other animations through its `ANIMATION` action. Use the `rpgroll` target.
- With SackResourcePack on the same server: run `/srp rebuild` after FMM converts new models.

## ModelEngine 4 (MythicCraft, paid)

- Folder: `plugins/ModelEngine/blueprints/`. Reload: `/meg reload`.
- Used through MythicMobs: `model{mid=<id>}`; play an animation with `state{mid=<id>;s=<name>}`.
- Bone tags (name prefixes): `h_` head (children need it too), `hi_` head inherited by children,
  `h[yaw=..,pitch=..]_` limited head, `mount` (bone id) driver seat, `p_` passenger seat,
  `tag_` nametag/HP bar anchor, `b_` axis-aligned sub-hitbox (one cube, square base),
  `ob_` oriented sub-hitbox, `ih_`/`ir_`/`il_` item display synced to head/right/left hand,
  `l_` leash point, `seg_`/`tl_` segments and tails, `jig_` physics bones, `g_` ghost bone,
  `phead_`, `prarm_`, `plarm_`, `pbody_`, `prleg_`, `plleg_` player skin parts.
- Default animations (`idle`, `walk`, `death`, `spawn`) depend on the MythicMobs/ModelEngine
  config; name them that way and trigger the rest with `state`.

## BetterModel (toxicity188, free)

- Folder: `plugins/BetterModel/models/` (general models). `plugins/BetterModel/players/` holds
  player animations without textures. Reload: `/bettermodel reload`.
- Blockbench Generic Model built from cubes; mesh support needs BetterModel 3.0+ and a 26.1+ client.
- Bone tags: `h_` head, `hi_` head with children, `b_` / `ob_` / `hitbox` hitbox bones,
  `p_` mountable bone (with a hitbox), plus nametag and shadow tags (see the wiki pages
  "Configuring custom nametag" and "Configuring custom shadow").
- Each bone renders as one item display. Works with MythicMobs, Citizens and others; it can merge
  its pack into ItemsAdder, Oraxen, Nexo or CraftEngine packs (wiki: "Merge with ...").
- Which animations play by themselves depends on the integration: name them `idle`, `walk` and
  so on and check "Animating your own model" on the wiki.

## Sources

- FreeMinecraftModels: github.com/MagmaGuy/FreeMinecraftModels, wiki.nightbreak.io
- ModelEngine 4: wiki.mythiccraft.io/modelengine (Modeling > Bone Behaviors)
- BetterModel: github.com/toxicity188/BetterModel/wiki
