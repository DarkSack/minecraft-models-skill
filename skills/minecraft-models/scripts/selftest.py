#!/usr/bin/env python3
"""
Self-test: math checks plus a full build of the examples with every target, validating
what the game would choke on. Run after changing anything in mcmodel/.

    python scripts/selftest.py
"""
import json
import os
import random
import shutil
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import build  # noqa: E402
from mcmodel import Item, Part, box, material, ramp, tube  # noqa: E402
from mcmodel.paint import png_bytes, read_png  # noqa: E402

EXAMPLES = os.path.join(HERE, '..', 'examples')


def test_bedrock_conversion():
    """Blockbench's conversion: x mirrored, z - 8, x/y rotations negated."""
    m = {'m': material('flat', ramp('#808080'))}
    it = Item('t', [box('a', (8, 2, 8), (4, 4, 4), 'm', r=(0, 0, 22.5)),
                    box('b', (5, 6, 11), (2, 2, 6), 'm', r=(22.5, 0, 0))], m, style='flat')
    a, b = it.bedrock_cubes()
    assert a['origin'] == [-2, 0, -2] and a['size'] == [4, 4, 4], a
    assert a['pivot'] == [0, 2, 0] and a['rotation'] == [0.0, 0.0, 22.5], a
    assert b['origin'] == [2, 5, 0] and b['rotation'] == [-22.5, 0.0, 0.0], b


def test_png_roundtrip():
    rnd = random.Random(3)
    px = [[(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256), rnd.choice((0, 128, 255)))
           for _ in range(7)] for _ in range(5)]
    path = os.path.join(tempfile.mkdtemp(), 't.png')
    open(path, 'wb').write(png_bytes(px))
    assert read_png(path) == px


def test_java_range_error():
    m = {'m': material('flat', ramp('#808080'))}
    try:
        Item('big', [box('a', (8, 8, 8), (60, 2, 2), 'm')], m, style='flat')
    except ValueError as e:
        assert 'outside the Java range' in str(e)
    else:
        raise AssertionError('a 60-unit part must be rejected')


def test_large_weapons_and_tubes():
    m = {'m': material('flat', ramp('#808080'))}
    for axis in 'xyz':
        parts = tube('pipe', (8, 8, 8), 10, 2, 'm', axis=axis)
        i = 'xyz'.index(axis)
        assert all(p.size()[i] == 10 and p.angles() == [0, 0, 0] for p in parts)
        for p in parts:
            cross = sorted(p.size()[j] for j in range(3) if j != i)
            assert abs(cross[0] - 4 * (1 - 2 * 0.293)) < 1e-8 and cross[1] == 4
    stepped = Item('stepped', tube('grip', (8, 8, 8), 10, 2, 'm', axis='y'), m)
    rounded = Item('rounded', tube('grip', (8, 8, 8), 10, 2, 'm', axis='y', round=True), m)
    assert stepped.min_java() == (1, 21, 4)
    assert rounded.min_java() == (1, 21, 11)
    for style in ('handheld', 'gun'):
        size = (2, 100, 2) if style == 'handheld' else (100, 2, 2)
        it = Item('huge', [box('body', (8, 8, 8), size, 'm')], m, style=style, hand_scale=1.7)
        assert all(-16 <= v <= 32 for p in it.parts for v in p.frm + p.to)
        assert all(-16 <= v <= 32 for bounds in it.bounds() for v in bounds)
        assert any(w.startswith('NOTE model spans') for w in it.warnings)
        for view in ('firstperson_righthand', 'thirdperson_righthand'):
            assert all(0 < s <= 4 for s in it.display[view]['scale'])
            assert all(abs(t) <= 80 for t in it.display[view]['translation'])


def check_build(out):
    """Validate everything the examples produced."""
    jsons = 0
    for base, _, files in os.walk(out):
        for f in files:
            if f.endswith(('.json', '.bbmodel', '.mcmeta')):
                json.load(open(os.path.join(base, f), encoding='utf-8'))
                jsons += 1
    assert jsons > 50, jsons

    # Java: every item definition points at a model that exists, every model at a texture that exists.
    for proj, ns in (('arsenal', 'demo'), ('lasers', 'lasers'), ('titans', 'titans')):
        pack = os.path.join(out, proj, 'vanilla', ns + '-resourcepack')
        root = os.path.join(pack, 'assets', ns)
        assert os.path.isdir(os.path.join(root, 'items')), proj
        for base, _, files in os.walk(os.path.join(root, 'items')):
            for f in files:
                d = json.load(open(os.path.join(base, f)))
                mid = d['model']['model'].split(':', 1)[1]
                model = json.load(open(os.path.join(root, 'models', mid + '.json')))
                tex = model['textures']['0'].split(':', 1)[1]
                assert os.path.isfile(os.path.join(root, 'textures', tex + '.png')), tex
                for e in model['elements']:
                    assert all(-16 <= v <= 32 for v in e['from'] + e['to']), (f, e['name'])
                    r = e.get('rotation')
                    if r and 'axis' in r:
                        assert abs(r['angle']) <= 45, (f, e['name'], r)
        if proj == 'arsenal':
            eq = json.load(open(os.path.join(root, 'equipment', 'ember.json')))
            assert eq['layers']['humanoid'][0]['texture'] == 'demo:ember'
        if proj == 'titans':
            for ident in ('titan_greatsword', 'titan_warhammer'):
                model = json.load(open(os.path.join(root, 'models', 'item', 'weapons', ident + '.json')))
                for e in model['elements']:
                    r = e.get('rotation')
                    assert not r or ('axis' in r and r['angle'] in (-45, -22.5, 0, 22.5, 45)), (ident, e)
        mc = json.load(open(os.path.join(pack, 'pack.mcmeta')))
        assert mc['pack']['min_format'] <= mc['pack']['max_format']

        # Bedrock pack: names under 80 chars, version under 65536, attachables point at real files.
        z = zipfile.ZipFile(os.path.join(out, proj, 'geyser', 'packs', ns + '.mcpack'))
        names = set(z.namelist())
        assert all(len(n) < 80 for n in names)
        man = json.loads(z.read('manifest.json'))
        assert man['header']['version'][2] < 65536
        geos = {g['description']['identifier'] for n in names if n.endswith('.geo.json')
                for g in json.loads(z.read(n))['minecraft:geometry']}
        icons = json.loads(z.read('textures/item_texture.json'))['texture_data']
        mapping = json.load(open(os.path.join(out, proj, 'geyser', 'custom_mappings', ns + '.json')))
        assert mapping['format_version'] == 2
        bids = [d['bedrock_identifier'] for v in mapping['items'].values() for d in v]
        assert len(bids) == len(set(bids)), 'duplicate bedrock identifiers'
        for v in mapping['items'].values():
            for d in v:
                assert d['bedrock_options']['icon'] in icons, d
                ident = d['model'].split(':', 1)[1]
                assert os.path.isfile(os.path.join(root, 'items', ident + '.json')), ident
        for n in names:
            if n.startswith('attachables/'):
                desc = json.loads(z.read(n))['minecraft:attachable']['description']
                assert desc['geometry']['default'] in geos, n
                assert desc['textures']['default'] + '.png' in names, n
                if 'worn' in desc['textures']:
                    assert desc['textures']['worn'] + '.png' in names, n
                    assert desc['geometry']['worn'].startswith('geometry.player.armor.'), n
                    rc = 'render_controllers/%s.render_controllers.json' % ns
                    controllers = json.loads(z.read(rc))['render_controllers']
                    assert all(c in controllers for c in desc['render_controllers']), n
                if 'worn3d' in desc['geometry']:
                    assert desc['geometry']['worn3d'] in geos, n
                    assert desc['textures']['worn3d'] + '.png' in names, n
        if proj == 'titans':
            for layer in (1, 2):
                data = z.read('textures/titans/armor_titan_%d.png' % layer)
                assert int.from_bytes(data[16:20], 'big') == 128
                assert int.from_bytes(data[20:24], 'big') == 64
            for piece in ('chestplate', 'leggings', 'boots'):
                ck = 'titans_armor_titan_' + piece
                desc = json.loads(z.read('attachables/%s.json' % ck))['minecraft:attachable']['description']
                assert 'worn3d' in desc['geometry'], piece
                geo = json.loads(z.read('models/entity/%s_3d.geo.json' % ck))['minecraft:geometry'][0]
                bones = {b['name']: b for b in geo['bones']}
                assert any(b.get('cubes') for b in bones.values()), piece
                assert all(b['parent'] in bones for b in bones.values() if 'parent' in b), piece
                ctrl = controllers['controller.render.%s_3d' % ck]
                assert ctrl['part_visibility'] == [{'*': 'v.worn'}], piece
        if proj == 'lasers':
            ck = 'lasers_projectiles_plasma_bolt'
            geo = json.loads(z.read('models/entity/%s.geo.json' % ck))['minecraft:geometry'][0]
            assert 'geyser_z' in geo['bones'][0]['binding']
            anims = json.loads(z.read('animations/%s.animation.json' % ck))['animations']
            assert 'animation.%s.placed' % ck in anims
            configs = os.path.join(out, proj, 'rpgroll', 'RPGRoll-Items', 'packs', ns)
            assert sorted(os.listdir(configs)) == [
                'ammo_laser_cell.yml', 'weapons_beam_rifle.yml', 'weapons_laser_pistol.yml', 'weapons_plasma_cannon.yml']
            for ident in ('laser_pistol', 'beam_rifle', 'plasma_cannon'):
                config = open(os.path.join(configs, 'weapons_%s.yml' % ident), encoding='utf-8').read()
                assert '  RIGHT_CLICK:\n    - type: SHOOT\n' in config, ident
                assert '      ammo: "ammo_laser_cell"\n' in config, ident
                if ident == 'beam_rifle':
                    assert '      sustain: "6"\n' in config
                if ident == 'plasma_cannon':
                    assert '      model: "lasers:projectiles/plasma_bolt"\n' in config
                    assert '      ammo-amount: "3"\n' in config
        z.close()

    # Creatures: single-axis cubes, hitbox bone, animations only on existing bones.
    for proj, expected in (('bestiary', ['ember_knight.bbmodel', 'magma_golem.bbmodel']),
                           ('titans', ['colossus.bbmodel'])):
        for loader, folder in (('fmm', 'FreeMinecraftModels/models'), ('modelengine', 'ModelEngine/blueprints'),
                               ('bettermodel', 'BetterModel/models')):
            d = os.path.join(out, proj, loader, *folder.split('/'))
            files = sorted(os.listdir(d))
            assert files == expected, files
            for f in files:
                bb = json.load(open(os.path.join(d, f), encoding='utf-8'))
                assert bb['meta']['model_format'] == 'free'
                assert any(g['name'] == 'hitbox' for g in bb['outliner'])
                for e in bb['elements']:
                    assert len([a for a in e['rotation'] if a]) <= 1, (f, e['name'], e['rotation'])
                    assert all(face['texture'] == 0 for face in e['faces'].values()), (f, e['name'])
                groups = set()

                def walk(g):
                    if isinstance(g, dict):
                        groups.add(g['uuid'])
                        for c in g['children']:
                            walk(c)
                for g in bb['outliner']:
                    walk(g)
                for a in bb['animations']:
                    assert set(a['animators']) <= groups, (f, a['name'])
                if proj == 'titans':
                    elements = {e['uuid']: e for e in bb['elements']}
                    names = set()

                    def spans(g):
                        if not isinstance(g, dict):
                            return
                        names.add(g['name'])
                        vs = []
                        for child in g['children']:
                            if isinstance(child, dict):
                                spans(child)
                            else:
                                e = elements[child]
                                vs += Part(e['name'], e['from'], e['to'], 'm',
                                           r=e['rotation'], origin=e['origin']).vertices()
                        if vs and g['name'] != 'hitbox':
                            assert max(max(v[i] for v in vs) - min(v[i] for v in vs) for i in range(3)) <= 48.001, g['name']
                    for g in bb['outliner']:
                        spans(g)
                    assert {'body_p1', 'arm_r_p1', 'arm_l_p1'} <= names
                    assert len(bb['elements']) == 23, 'splitting must preserve all 22 cubes plus hitbox'
                    assert all(abs(a - b) < 1e-8 for a, b in zip(bb['visible_box'][:2], (2.7, 6.9)))


def main():
    for t in (test_bedrock_conversion, test_png_roundtrip, test_java_range_error, test_large_weapons_and_tubes):
        t()
        print('ok  ' + t.__name__)
    out = tempfile.mkdtemp(prefix='mcmodel-selftest-')
    try:
        for name, targets in (('arsenal', 'all'), ('bestiary', 'all'), ('lasers', 'all'), ('titans', 'all')):
            build.main([os.path.join(EXAMPLES, name + '.py'), '--out', os.path.join(out, name), '--targets', targets])
        first = open(os.path.join(out, 'arsenal', 'geyser', 'packs', 'demo.mcpack'), 'rb').read()
        build.main([os.path.join(EXAMPLES, 'arsenal.py'), '--out', os.path.join(out, 'again'), '--targets', 'geyser'])
        again = open(os.path.join(out, 'again', 'geyser', 'packs', 'demo.mcpack'), 'rb').read()
        assert first == again, 'the .mcpack must be byte-identical between builds'
        check_build(out)
        print('ok  examples build and validate (all targets, deterministic .mcpack)')
    finally:
        shutil.rmtree(out, ignore_errors=True)
    print('ALL OK')


if __name__ == '__main__':
    main()
