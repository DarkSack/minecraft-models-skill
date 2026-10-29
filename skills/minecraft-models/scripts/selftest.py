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
from mcmodel import Item, box, material, ramp  # noqa: E402
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
    for proj in ('arsenal',):
        root = os.path.join(out, proj, 'vanilla', 'demo-resourcepack', 'assets', 'demo')
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
        eq = json.load(open(os.path.join(root, 'equipment', 'ember.json')))
        assert eq['layers']['humanoid'][0]['texture'] == 'demo:ember'
        mc = json.load(open(os.path.join(out, proj, 'vanilla', 'demo-resourcepack', 'pack.mcmeta')))
        assert mc['pack']['min_format'] <= mc['pack']['max_format']

        # Bedrock pack: names under 80 chars, version under 65536, attachables point at real files.
        z = zipfile.ZipFile(os.path.join(out, proj, 'geyser', 'packs', 'demo.mcpack'))
        names = set(z.namelist())
        assert all(len(n) < 80 for n in names)
        man = json.loads(z.read('manifest.json'))
        assert man['header']['version'][2] < 65536
        geos = {g['description']['identifier'] for n in names if n.endswith('.geo.json')
                for g in json.loads(z.read(n))['minecraft:geometry']}
        icons = json.loads(z.read('textures/item_texture.json'))['texture_data']
        mapping = json.load(open(os.path.join(out, proj, 'geyser', 'custom_mappings', 'demo.json')))
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
                    rc = 'render_controllers/demo.render_controllers.json'
                    assert desc['render_controllers'][0] in json.loads(z.read(rc))['render_controllers'], n

    # Creatures: single-axis cubes, hitbox bone, animations only on existing bones.
    for loader, folder in (('fmm', 'FreeMinecraftModels/models'), ('modelengine', 'ModelEngine/blueprints'),
                           ('bettermodel', 'BetterModel/models')):
        d = os.path.join(out, 'bestiary', loader, *folder.split('/'))
        files = sorted(os.listdir(d))
        assert files == ['ember_knight.bbmodel', 'magma_golem.bbmodel'], files
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


def main():
    for t in (test_bedrock_conversion, test_png_roundtrip, test_java_range_error):
        t()
        print('ok  ' + t.__name__)
    out = tempfile.mkdtemp(prefix='mcmodel-selftest-')
    try:
        for name, targets in (('arsenal', 'all'), ('bestiary', 'all')):
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
