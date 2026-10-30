# minecraft-models

An [Agent Skill](https://agentskills.io) for Claude Code, Codex and OpenCode that creates original
Minecraft 3D models as code and exports them for Java and Bedrock: weapons, tools, trinkets,
helmets, armor sets, furniture, mobs and animated bosses.

One Python spec (cubes + materials, no dependencies) builds:

- Java 1.21.4+ item models, item definitions, textures (animated on Java) and equipment layers
- Blockbench `.bbmodel` projects (Java Block/Item for items, Generic Model for creatures)
- Bedrock attachables, icons and a `.mcpack`, plus Geyser custom item mappings (format 2)
- Ready-to-copy folders for FreeMinecraftModels, ModelEngine 4, BetterModel, ItemsAdder, Oraxen,
  Nexo, RPGRoll and SackResourcePack
- PNG previews (inventory icons, 3/4 views, creature poses per animation) for the agent to check
- Oversized held weapons with automatic Java range fitting and configurable `hand_scale`, giant
  creatures with automatic bone splitting, 128x64 armor layers and Bedrock worn 3D extras
- RPGRoll SHOOT configurations for laser guns, ammo cells, sustained beams and plasma projectiles

Textures are painted by code: nothing is copied from Mojang or third parties.

## Install

The skill is the folder `skills/minecraft-models`. Link or copy it where your agent looks:

| Agent | User-wide folder |
|---|---|
| Claude Code | `~/.claude/skills/minecraft-models` |
| Codex | `~/.agents/skills/minecraft-models` |
| OpenCode | `~/.config/opencode/skills/`, `~/.claude/skills/` or `~/.agents/skills/` |

With the `skills` CLI: `npx skills add DarkSack/minecraft-models-skill`.

Requires Python 3.8+ on the machine where the agent runs.

## License

MIT. Models you build with it are yours.

## Try it

```bash
python skills/minecraft-models/scripts/build.py skills/minecraft-models/examples/arsenal.py --out out/arsenal --targets all
python skills/minecraft-models/scripts/build.py skills/minecraft-models/examples/bestiary.py --out out/bestiary --targets fmm
python -I skills/minecraft-models/scripts/build.py skills/minecraft-models/examples/titans.py --out out/titans --targets vanilla,geyser,fmm,rpgroll
python -I skills/minecraft-models/scripts/build.py skills/minecraft-models/examples/lasers.py --out out/lasers --targets vanilla,geyser,rpgroll
python skills/minecraft-models/scripts/selftest.py
```

Then ask your agent things like "make me an obsidian battle axe with glowing runes for Nexo and
Geyser" or "un jefe araña para ModelEngine con animación de lanzar telarañas".

`titans.py` includes a greatsword and warhammer compatible with Java 1.21.4+, a horned helmet
requiring 1.21.6+, bulky armor and a roughly seven-block colossus. `lasers.py` includes a pistol,
sustained beam rifle, plasma cannon, cell and projectile. Default tubes use unrotated stepped
octagons; `round=True` opts into rotated squares that can require newer Java when combined with
handheld tilt. Ammo and sustained lasers need the RPGRoll changes intended for 1.1.8, currently
local and unpublished. Export checks and previews do not replace in-game checks of Bedrock armor
bone binding, held size, projectile pitch, held-click repetition through Geyser and pulse knockback.

---

## En español

Skill para Claude Code, Codex y OpenCode que crea modelos 3D originales de Minecraft escritos como
código y los exporta para Java y Bedrock: armas, herramientas, objetos, cascos, armaduras, muebles,
mobs y jefes animados, con carpetas listas para FreeMinecraftModels, ModelEngine, BetterModel,
ItemsAdder, Oraxen, Nexo, RPGRoll y SackResourcePack, y vistas previas en PNG para revisarlos.
Se instala enlazando `skills/minecraft-models` en la carpeta de skills de cada agente (tabla de arriba).

Los ejemplos `titans.py` y `lasers.py` añaden armas enormes (`hand_scale`), armadura con capas de
128x64 y piezas 3D puestas en Bedrock, un coloso con división automática de huesos y armas láser
con munición y rayo sostenido. La munición y `sustain` dependen de los cambios locales de RPGRoll
previstos para 1.1.8, aún sin publicar. Quedan pruebas en juego de esas funciones y de Geyser.
