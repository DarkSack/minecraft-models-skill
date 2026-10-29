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
python skills/minecraft-models/scripts/selftest.py
```

Then ask your agent things like "make me an obsidian battle axe with glowing runes for Nexo and
Geyser" or "un jefe araña para ModelEngine con animación de lanzar telarañas".

---

## En español

Skill para Claude Code, Codex y OpenCode que crea modelos 3D originales de Minecraft escritos como
código y los exporta para Java y Bedrock: armas, herramientas, objetos, cascos, armaduras, muebles,
mobs y jefes animados, con carpetas listas para FreeMinecraftModels, ModelEngine, BetterModel,
ItemsAdder, Oraxen, Nexo, RPGRoll y SackResourcePack, y vistas previas en PNG para revisarlos.
Se instala enlazando `skills/minecraft-models` en la carpeta de skills de cada agente (tabla de arriba).
