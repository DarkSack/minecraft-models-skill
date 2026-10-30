"""
Writers: one function per target. Each writes under out/<target>/ the folders exactly as
they go into a server (plugins/<Plugin>/...) and returns install notes for INSTALL.md.

Every target shares the same Java assets (assets/<ns>/models|textures|items|equipment);
what changes is where they live and the plugin config that points at them.
"""
import json
import os
import zipfile
import zlib

from .model import ARMOR_PIECES, DISPLAYED, ArmorSet, Item
from .paint import png_bytes, scale_img
from .render import render

PACK_FORMATS = (46, 97)      # Java 1.21.4 .. 26.3: item model definitions exist since 46


# ---------------------------------------------------------------- helpers

def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(data, (dict, list)):
        data = json.dumps(data, indent=1, ensure_ascii=False) + '\n'
    if isinstance(data, str):
        data = data.encode('utf-8')
    with open(path, 'wb') as f:
        f.write(data)


def flat_id(ident):
    return ident.replace('/', '_')


def yaml_str(s):
    return '"%s"' % s.replace('\\', '\\\\').replace('"', '\\"')


class FixedZip:
    """A zip whose bytes depend only on its content (fixed dates), so rebuilds are comparable."""

    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.z = zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED)
        self.crc = 0

    def add(self, name, data):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, indent=1, ensure_ascii=False)
        if isinstance(data, str):
            data = data.encode('utf-8')
        self.crc = zlib.crc32(data, self.crc)
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        self.z.writestr(info, data)

    def close(self):
        self.z.close()


# ---------------------------------------------------------------- Java assets

def java_assets(p, assets, tex_prefix='item/'):
    """
    Writes assets/<ns>/... under `assets` (the folder that holds namespaces):
    models/item/<id>.json, textures/item/<id>.png (+ .mcmeta), items/<id>.json,
    equipment/<set>.json, textures/entity/equipment/humanoid[_leggings]/<set>.png.
    """
    ns = p.ns
    root = os.path.join(assets, ns)
    for it in p.items:
        tex_id = '%s:%s%s' % (ns, tex_prefix, it.id)
        model_id = '%s:item/%s' % (ns, it.id)
        write(os.path.join(root, 'models', 'item', it.id + '.json'), it.java_model(tex_id))
        tex = os.path.join(root, 'textures', *(tex_prefix + it.id).split('/')) + '.png'
        write(tex, png_bytes(it.strip()))
        if it.animated:
            write(tex + '.mcmeta', it.mcmeta())
        write(os.path.join(root, 'items', it.id + '.json'), it.java_definition(model_id))
    for a in p.armors:
        write(os.path.join(root, 'equipment', a.id + '.json'), {'layers': {
            'humanoid': [{'texture': '%s:%s' % (ns, a.id)}],
            'humanoid_leggings': [{'texture': '%s:%s' % (ns, a.id)}]}})
        write(os.path.join(root, 'textures', 'entity', 'equipment', 'humanoid', a.id + '.png'), png_bytes(a.layer1))
        write(os.path.join(root, 'textures', 'entity', 'equipment', 'humanoid_leggings', a.id + '.png'),
              png_bytes(a.layer2))


def pack_mcmeta(description, formats=PACK_FORMATS):
    lo, hi = formats
    # pack_format + supported_formats for clients before 1.21.9, min/max_format after.
    return {'pack': {'description': description, 'pack_format': lo, 'supported_formats': [lo, hi],
                     'min_format': lo, 'max_format': hi}}


# ---------------------------------------------------------------- Bedrock (Geyser)

def bedrock_pack(p, path):
    """The .mcpack Geyser sends to Bedrock players. Returns its size in bytes."""
    ns = p.ns
    if not p.items:
        return 0
    z = FixedZip(path)
    icons, ctrls = {}, {}
    armors = {a.id: a for a in p.armors}
    for it in p.items:
        ck = '%s_%s' % (ns, flat_id(it.id))
        bid = '%s:%s' % (ns, flat_id(it.id))
        icons[ck] = render(it, 64)
        tex = 'textures/%s/%s' % (ns, ck)
        # Frame 0 only: attachables ignore uv_anim and a whole strip ends up squashed on every face.
        z.add(tex + '.png', png_bytes(it.px))
        z.add('models/entity/%s.geo.json' % ck, it.bedrock_geometry(ck))
        z.add('animations/%s.animation.json' % ck, it.bedrock_animations(ck))
        worn = worn3d = None
        if it.wears:
            slot, layer = ARMOR_PIECES[it.wears[1]]
            worn = (it.wears[1], slot, 'textures/%s/armor_%s_%d' % (ns, flat_id(it.wears[0]), layer))
            ctrls.update(Item.worn_controller(ck))
            armor = armors.get(it.wears[0])
            if armor and it.wears[1] in armor.extras:
                worn3d = tex + '_3d'
                z.add(worn3d + '.png', png_bytes(armor.extras[it.wears[1]][0].px))
                z.add('models/entity/%s_3d.geo.json' % ck, armor.extras_geometry(it.wears[1], ck + '_3d'))
                ctrls.update(ArmorSet.extras_controller(ck))
        z.add('attachables/%s.json' % ck, it.bedrock_attachable(bid, ck, tex, worn, worn3d))
    for a in p.armors:
        for n, lay in ((1, a.layer1), (2, a.layer2)):
            z.add('textures/%s/armor_%s_%d.png' % (ns, flat_id(a.id), n), png_bytes(lay))
    z.add('textures/item_texture.json', {'resource_pack_name': ns, 'texture_name': 'atlas.items', 'texture_data': {
        ck: {'textures': 'textures/%s/icons/%s' % (ns, ck[len(ns) + 1:])} for ck in icons}})
    for ck, px in sorted(icons.items()):
        z.add('textures/%s/icons/%s.png' % (ns, ck[len(ns) + 1:]), png_bytes(px))
    if ctrls:
        z.add('render_controllers/%s.render_controllers.json' % ns,
              {'format_version': '1.8.0', 'render_controllers': ctrls})
    z.add('pack_icon.png', png_bytes(scale_img(next(iter(icons.values())), 2)))
    long_ = [n for n in z.z.namelist() if len(n) >= 80]
    # Bedrock keeps packs by uuid + version and never re-downloads one it has: the version comes
    # from the content so a change reaches players. Above 65535 Bedrock drops the connection.
    version = [1, 0, z.crc % 65536]
    import uuid as _u
    base = _u.uuid5(_u.NAMESPACE_URL, 'mcmodel/%s' % ns)
    z.add('manifest.json', {'format_version': 2, 'header': {
        'name': p.title, 'description': 'Models of %s' % p.title, 'uuid': str(_u.uuid5(base, 'header')),
        'version': version, 'min_engine_version': [1, 21, 0]},
        'modules': [{'type': 'resources', 'uuid': str(_u.uuid5(base, 'resources')), 'version': version}]})
    z.close()
    if long_:
        raise ValueError('Bedrock fails on paths of 80+ characters, shorten these ids: %s' % long_)
    return os.path.getsize(path)


def geyser_mappings(p):
    """Geyser custom item mappings, format 2 (Geyser 2.9.3+, Java 1.21.4+ item_model)."""
    items = {}
    for it in p.items:
        opts = {'icon': '%s_%s' % (p.ns, flat_id(it.id)), 'allow_offhand': True,
                'display_handheld': it.style in ('handheld', 'gun', 'rod')}
        items.setdefault('minecraft:' + it.base, []).append({
            'type': 'definition', 'model': '%s:%s' % (p.ns, it.id),
            'bedrock_identifier': '%s:%s' % (p.ns, flat_id(it.id)),
            'display_name': it.name, 'bedrock_options': opts})
    return {'format_version': 2, 'items': items}


def _geyser(p, folder):
    size = bedrock_pack(p, os.path.join(folder, 'packs', p.ns + '.mcpack'))
    write(os.path.join(folder, 'custom_mappings', p.ns + '.json'), geyser_mappings(p))
    return size


# ---------------------------------------------------------------- targets

def t_vanilla(p, out):
    root = os.path.join(out, p.ns + '-resourcepack')
    write(os.path.join(root, 'pack.mcmeta'), pack_mcmeta(p.title, p.formats))
    java_assets(p, os.path.join(root, 'assets'))
    z = FixedZip(os.path.join(out, p.ns + '-resourcepack.zip'))
    for base, _, files in sorted(os.walk(root)):
        for f in sorted(files):
            full = os.path.join(base, f)
            z.add(os.path.relpath(full, root).replace(os.sep, '/'), open(full, 'rb').read())
    z.close()
    return ['Vanilla resource pack: `%s-resourcepack.zip` (or the folder). Serve it as the server pack '
            '(server.properties resource-pack + sha1) or drop it in .minecraft/resourcepacks to test.' % p.ns,
            'Give an item the model: `/give @s %s[item_model="%s:%s"]`.' % (
                'minecraft:' + p.items[0].base if p.items else 'minecraft:paper', p.ns,
                p.items[0].id if p.items else '<id>'),
            'Armor look: `equippable={slot:"chest",asset_id:"%s:<set>"}` on the item.' % p.ns]


def t_geyser(p, out):
    size = _geyser(p, out)
    return ['Geyser: copy `packs/%s.mcpack` to `plugins/Geyser-*/packs/` and `custom_mappings/%s.json` to '
            '`plugins/Geyser-*/custom_mappings/` on the server that runs Geyser (proxy or backend). '
            'Needs `enable-custom-content: true`, Geyser 2.9.3+ and a full restart (`geyser reload` does not '
            'reload packs). Pack: %d KB.' % (p.ns, p.ns, size // 1024),
            'The mapping matches items by Java base item + `item_model` = `%s:<id>`: the server must give '
            'the items exactly that component.' % p.ns]


def t_rpgroll(p, out):
    notes = []
    if p.items or p.armors:
        mod = os.path.join(out, 'SackResourcePack', 'content', p.ns)
        write(os.path.join(mod, 'pack.yml'),
              'id: %s\nname: %s\nversion: 1.0.0\nauthor: %s\nnamespace: %s\npriority: 25\ndepends: []\n'
              'description: %s\n' % (p.ns, yaml_str(p.title), yaml_str(p.author), p.ns, yaml_str('Models of ' + p.title)))
        java_assets(p, os.path.join(mod, 'assets'))
        size = _geyser(p, os.path.join(out, 'Geyser-Spigot'))
        notes.append('SackResourcePack: copy `SackResourcePack/content/%s/` to `plugins/SackResourcePack/content/` '
                     'and run `/srp rebuild` (then `/srp publish` if you upload the pack).' % p.ns)
        notes.append('Bedrock: `Geyser-Spigot/` goes into `plugins/Geyser-Spigot/` (or `Geyser-Velocity/` on '
                     'the proxy). Restart Geyser. Pack: %d KB.' % (size // 1024))
    held = [it for it in p.items if it.style not in DISPLAYED]
    for it in held:
        lines = ['id: %s' % flat_id(it.id), 'pack: %s' % p.ns, 'material: %s' % it.base.upper(),
                 'item-model: "%s:%s"' % (p.ns, it.id), 'display-name: %s' % yaml_str('&f' + it.name)]
        if it.wears:
            lines.append('equipment-model: "%s:%s"' % (p.ns, it.wears[0]))
        elif it.style == 'helmet':
            lines.append('equipment-model: none     # the 3D model itself is worn on the head')
        if it.shot:
            lines += ['triggers:', '  RIGHT_CLICK:', '    - type: SHOOT']
            lines += ['      %s: %s' % (k, yaml_str(_shot_value(p, k, v))) for k, v in it.shot.items()]
        write(os.path.join(out, 'RPGRoll-Items', 'packs', p.ns, flat_id(it.id) + '.yml'), '\n'.join(lines) + '\n')
    if held:
        notes.append('RPGRoll-Items: `RPGRoll-Items/packs/%s/*.yml` are minimal item files (material, '
                     'item-model, equipment-model, SHOOT for guns); add stats and triggers, then `/item reload`.'
                     % p.ns)
    if any(it.shot for it in p.items):
        notes.append('SHOOT `ammo` and `sustain` need RPGRoll-Items 1.1.8+. A sustained beam (`sustain`) stays '
                     'on while right click is held: Java repeats the click every 4 ticks, so `amount` and the '
                     'ammo are per pulse (5 per second).')
    if any(it.style == 'projectile' for it in p.items):
        notes.append('Projectiles have no item file: SHOOT shows them through `model` (with `speed` > 0).')
    furn = [it for it in p.items if it.style == 'furniture']
    if furn:
        write(os.path.join(out, 'RPGRoll-Furniture', p.ns + '.example.yml'), ''.join(
            '%s:\n  category: decor\n  name: %s\n  model: %s:%s\n  placement: { surfaces: [floor], rotations: 4 }\n'
            '  hitbox: { type: barrier, blocks: ["0,0,0"] }\n' % (flat_id(it.id), yaml_str('&f' + it.name), p.ns, it.id)
            for it in furn))
        notes.append('RPGRoll-Furniture: merge `RPGRoll-Furniture/%s.example.yml` into your furniture '
                     'definitions (adjust hitbox blocks to the model size).' % p.ns)
    if p.creatures:
        for c in p.creatures:
            write(os.path.join(out, 'FreeMinecraftModels', 'models', c.id + '.bbmodel'), c.bbmodel())
        write(os.path.join(out, 'RPGRoll-Mobs', p.ns + '.example.yml'), ''.join(
            '# in the mob file of %s\nmodel:\n  model-engine-id: %s   # FreeMinecraftModels model id\n'
            % (c.id, c.id) for c in p.creatures))
        notes.append('RPGRoll-Mobs: creatures go to `plugins/FreeMinecraftModels/models/` (`/fmm reload`); '
                     'point each mob at its model with `model.model-engine-id`. RPGRoll-Mobs plays `attack` '
                     'when the mob hits; FMM plays spawn/idle/walk/death.')
    return notes


def _plugin_assets(p, root):
    java_assets(p, os.path.join(root, 'assets'))


def _shot_value(p, key, value):
    """SHOOT `model` and `ammo` may name items of the spec: give them as RPGRoll sees them."""
    ids = {it.id for it in p.items}
    if key == 'model' and value in ids:
        return '%s:%s' % (p.ns, value)
    if key == 'ammo' and value in ids:
        return flat_id(value)
    return str(value).lower() if isinstance(value, bool) else str(value)


def t_itemsadder(p, out):
    ns = p.ns
    root = os.path.join(out, 'ItemsAdder', 'contents', ns)
    # ItemsAdder resolves <ns>:item/<id> to contents/<ns>/textures|models/item/<id>.
    for it in p.items:
        write(os.path.join(root, 'models', 'item', it.id + '.json'), it.java_model('%s:item/%s' % (ns, it.id)))
        write(os.path.join(root, 'textures', 'item', it.id + '.png'), png_bytes(it.strip()))
        if it.animated:
            write(os.path.join(root, 'textures', 'item', it.id + '.png.mcmeta'), it.mcmeta())
    y = ['info:', '  namespace: %s' % ns]
    if p.armors:
        y.append('equipments:')
        for a in p.armors:
            write(os.path.join(root, 'textures', 'armor', a.id, 'layer_1.png'), png_bytes(a.layer1))
            write(os.path.join(root, 'textures', 'armor', a.id, 'layer_2.png'), png_bytes(a.layer2))
            y += ['  %s:' % flat_id(a.id), '    type: armor',
                  '    layer_1: armor/%s/layer_1' % a.id, '    layer_2: armor/%s/layer_2' % a.id]
    y.append('items:')
    for it in p.items:
        y += ['  %s:' % flat_id(it.id), '    name: %s' % yaml_str(it.name),
              '    resource:                 # every client version; 1.21.4+ also accepts graphics: { model: ... }',
              '      material: %s' % it.base.upper(), '      generate: false',
              '      model_path: item/%s' % it.id]
        if it.wears:
            y += ['    equipment:', '      id: %s:%s' % (ns, flat_id(it.wears[0]))]
        if it.style == 'furniture':
            y += ['    behaviours:', '      furniture:', '        entity: item_display', '        solid: true',
                  '        hitbox: { length: 1, width: 1, height: 1 }',
                  '        placeable_on: { floor: true, walls: false, ceiling: false }']
    write(os.path.join(root, 'configs', ns + '.yml'), '\n'.join(y) + '\n')
    return ['ItemsAdder: copy `ItemsAdder/contents/%s/` to `plugins/ItemsAdder/contents/` and run `/iazip`. '
            'Check `configs/%s.yml` against the wiki of your ItemsAdder version (wiki.itemsadder.com).' % (ns, ns),
            'ItemsAdder assigns its own item_model/CustomModelData: for Geyser, read the real value from an item '
            'in game and set it as `model` in the Geyser mapping (or skip Geyser for these items).']


def t_oraxen(p, out):
    ns = p.ns
    root = os.path.join(out, 'Oraxen')
    _plugin_assets(p, os.path.join(root, 'pack'))
    y = []
    for it in p.items:
        y += ['%s:' % flat_id(it.id), '  displayname: %s' % yaml_str('<white>' + it.name),
              '  material: %s' % it.base.upper(), '  Pack:', '    generate_model: false',
              '    model: %s:item/%s' % (ns, it.id)]
        if it.wears:
            y += ['  # worn look: assets/%s/equipment/%s.json is in the pack;' % (ns, it.wears[0]),
                  '  Components:', '    equippable:', '      slot: %s' % {
                      'helmet': 'HEAD', 'chestplate': 'CHEST', 'leggings': 'LEGS', 'boots': 'FEET'}[it.wears[1]],
                  '      model: %s:%s' % (ns, it.wears[0])]
        if it.style == 'furniture':
            y += ['  Mechanics:', '    furniture:', '      type: DISPLAY_ENTITY',
                  '      hitbox: { width: 1.0, height: 1.0 }']
    write(os.path.join(root, 'items', ns + '.yml'), '\n'.join(y) + '\n')
    return ['Oraxen: copy `Oraxen/pack/assets/%s` to `plugins/Oraxen/pack/assets/` and `Oraxen/items/%s.yml` to '
            '`plugins/Oraxen/items/`, then `/oraxen reload all`. Check field names against docs.oraxen.com for '
            'your version (furniture and armor changed between releases).' % (ns, ns)]


def t_nexo(p, out):
    ns = p.ns
    root = os.path.join(out, 'Nexo')
    _plugin_assets(p, os.path.join(root, 'pack'))
    y = []
    for it in p.items:
        y += ['%s:' % flat_id(it.id), '  itemname: %s' % yaml_str('<white>' + it.name),
              '  material: %s' % it.base.upper(),
              '  Components:', '    item_model: %s:%s   # the items/ definition in the pack; also what Geyser '
              'matches' % (ns, it.id)]
        if it.wears:
            y += ['  CustomArmor:', '    id: %s' % flat_id(it.wears[0]),
                  '    layer1: %s:entity/equipment/humanoid/%s' % (ns, it.wears[0]),
                  '    layer2: %s:entity/equipment/humanoid_leggings/%s' % (ns, it.wears[0])]
        if it.style == 'furniture':
            y += ['  Mechanics:', '    furniture:', '      properties:', '        display_transform: NONE',
                  '      hitbox:', '        barriers: ["0,0,0"]']
    write(os.path.join(root, 'items', ns + '.yml'), '\n'.join(y) + '\n')
    return ['Nexo: copy `Nexo/pack/assets/%s` to `plugins/Nexo/pack/assets/` and `Nexo/items/%s.yml` to '
            '`plugins/Nexo/items/`, then `/nexo reload all`. Furniture hitbox keys vary by version: check '
            'docs.nexomc.com/mechanics/furniture-mechanic.' % (ns, ns)]


def _creatures(p, out, folder, note):
    for c in p.creatures:
        write(os.path.join(out, *folder.split('/'), c.id + '.bbmodel'), c.bbmodel())
    return [note] if p.creatures else []


def t_fmm(p, out):
    return _creatures(p, out, 'FreeMinecraftModels/models',
                      'FreeMinecraftModels: copy `FreeMinecraftModels/models/*.bbmodel` to '
                      '`plugins/FreeMinecraftModels/models/` and run `/fmm reload` (it rebuilds its resource pack '
                      'in `output/`). Auto animations: spawn, idle, walk, attack, death.')


def t_modelengine(p, out):
    return _creatures(p, out, 'ModelEngine/blueprints',
                      'ModelEngine 4: copy `ModelEngine/blueprints/*.bbmodel` to `plugins/ModelEngine/blueprints/` '
                      'and run `/meg reload`. Use the model with MythicMobs `model{mid=<id>}`; play the other '
                      'animations with `state{mid=<id>;s=<animation>}`.')


def t_bettermodel(p, out):
    return _creatures(p, out, 'BetterModel/models',
                      'BetterModel: copy `BetterModel/models/*.bbmodel` to `plugins/BetterModel/models/` and run '
                      '`/bettermodel reload`.')


TARGETS = {'vanilla': t_vanilla, 'geyser': t_geyser, 'rpgroll': t_rpgroll, 'itemsadder': t_itemsadder,
           'oraxen': t_oraxen, 'nexo': t_nexo, 'fmm': t_fmm, 'modelengine': t_modelengine,
           'bettermodel': t_bettermodel}
ITEM_TARGETS = ('vanilla', 'geyser', 'rpgroll', 'itemsadder', 'oraxen', 'nexo')
CREATURE_TARGETS = ('rpgroll', 'fmm', 'modelengine', 'bettermodel')
