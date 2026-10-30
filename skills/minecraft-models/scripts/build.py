#!/usr/bin/env python3
"""
Build a model spec into previews, Blockbench projects and server-ready folders.

    python build.py SPEC.py --out OUT [--targets vanilla,geyser,...|all] [--ns NAME]

SPEC.py is plain Python that does `from mcmodel import *` and defines:
    NAMESPACE = 'mypack'            # lowercase; the resource pack namespace (or pass --ns)
    TITLE = 'My Pack'               # optional, shown in pack descriptions
    MODELS = [Item(...), ArmorSet(...), Creature(...)]   # or def models(): return [...]

Targets: vanilla, geyser, rpgroll, itemsadder, oraxen, nexo (items, armor, furniture) and
rpgroll, fmm, modelengine, bettermodel (creatures). Previews and .bbmodel files are always made.
"""
import argparse
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True      # keep the installed skill folder clean

from mcmodel import ArmorSet, Creature, Item  # noqa: E402
from mcmodel.paint import png_bytes, sheet  # noqa: E402
from mcmodel.render import centered, render, three_quarter  # noqa: E402
from mcmodel.targets import CREATURE_TARGETS, ITEM_TARGETS, PACK_FORMATS, TARGETS, write  # noqa: E402

NS_OK = set('abcdefghijklmnopqrstuvwxyz0123456789_-.')
AUTO_ANIMS = {'fmm': ('idle', 'walk', 'attack', 'death', 'spawn'), 'modelengine': ('idle', 'walk', 'death', 'spawn'),
              'bettermodel': ('idle', 'walk'), 'rpgroll': ('idle', 'walk', 'attack', 'death', 'spawn')}


class Project:
    def __init__(self, ns, title, author, models, formats=PACK_FORMATS):
        self.ns, self.title, self.author, self.formats = ns, title, author, formats
        self.items = [m for m in models if isinstance(m, Item)]
        self.armors = [m for m in models if isinstance(m, ArmorSet)]
        self.creatures = [m for m in models if isinstance(m, Creature)]
        other = [m for m in models if not isinstance(m, (Item, ArmorSet, Creature))]
        if other:
            raise SystemExit('MODELS has things that are not Item/ArmorSet/Creature: %r' % other[:3])


def load_spec(path):
    spec = importlib.util.spec_from_file_location('mcmodel_spec', path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec.loader.exec_module(mod)
    models = mod.models() if hasattr(mod, 'models') else getattr(mod, 'MODELS', None)
    if not models:
        raise SystemExit('%s defines neither MODELS nor models()' % path)
    return mod, list(models)


def check(p, targets):
    """Problems that would only show up in game. Returns (errors, warnings)."""
    errors, warns, notes = [], [], []
    for kind, group in (('item', p.items), ('armor set', p.armors), ('creature', p.creatures)):
        ids = [m.id for m in group]
        for d in sorted({i for i in ids if ids.count(i) > 1}):
            errors.append('two %ss with id %s' % (kind, d))
    sets = {a.id for a in p.armors}
    for it in p.items:
        if it.wears and it.wears[0] not in sets:
            errors.append('%s wears armor set %r, which is not in MODELS' % (it.id, it.wears[0]))
        warns += ['%s: %s' % (it.id, w) for w in it.warnings if not w.startswith('NOTE ')]
        notes += ['%s: %s' % (it.id, w[5:]) for w in it.warnings if w.startswith('NOTE ')]
    for c in p.creatures:
        warns += ['%s: %s' % (c.id, w) for w in c.warnings if not w.startswith('NOTE ')]
        notes += ['%s: %s' % (c.id, w[5:]) for w in c.warnings if w.startswith('NOTE ')]
        for bone, ext in sorted(c.bone_extents().items()):
            if ext > c.max_bone:
                warns.append('%s: bone %s spans %.0f units with one cube; loaders build each bone as an item '
                             'model (max %d units across): use smaller cubes' % (c.id, bone, ext, c.max_bone))
        for t in targets:
            missing = [a for a in AUTO_ANIMS.get(t, ())[:2] if a not in c.anims]
            if missing:
                warns.append('%s: no %s animation (%s plays it on its own)' % (c.id, '/'.join(missing), t))
    if p.creatures and not any(t in CREATURE_TARGETS for t in targets):
        warns.append('creatures only get previews and .bbmodel: add a target (fmm, modelengine, bettermodel, rpgroll)')
    if (p.items or p.armors) and not any(t in ITEM_TARGETS for t in targets):
        warns.append('items only get previews and .bbmodel: add a target (vanilla, geyser, rpgroll, ...)')
    return errors, warns, notes


def previews(p, out):
    files = []
    if p.items:
        write(os.path.join(out, 'items.png'), png_bytes(sheet([render(it, 64) for it in p.items], cols=8)))
        write(os.path.join(out, 'items_3d.png'), png_bytes(sheet([three_quarter(it, 96) for it in p.items], cols=6)))
        files += ['items.png (inventory icons, also the Bedrock icons)', 'items_3d.png (three-quarter view)']
    from mcmodel.geom import matmul, rot
    for a in p.armors:
        write(os.path.join(out, 'armor_%s.png' % a.id.replace('/', '_')), png_bytes(a.preview()))
        files.append('armor_%s.png (worn layers 1 and 2)' % a.id)
        if a.extras:
            m, win = centered(a.worn_model())
            views = [render(m, 160, view=matmul(rot(x=-15), rot(y=y)), window=win, use_gui=False)
                     for y in (145, 215, 90, 0)]
            write(os.path.join(out, 'armor_%s_3d.png' % a.id.replace('/', '_')), png_bytes(sheet(views, cols=4)))
            files.append('armor_%s_3d.png (Bedrock 3D pieces on a stand-in player: front 3/4 both sides, '
                         'side, back)' % a.id)
    for c in p.creatures:
        frames = []
        for name in [None] + list(c.anims):
            t = c.anims[name].length * 0.3 if name else 0.0
            m, win = centered(c.pose(name, t))
            # creatures face -z and the camera looks from +z: turn them round to see the front
            frames.append(render(m, 128, view=matmul(rot(x=-15), rot(y=145)), window=win, use_gui=False))
            frames.append(render(m, 128, view=rot(y=90), window=win, use_gui=False))
        write(os.path.join(out, 'creature_%s.png' % c.id), png_bytes(sheet(frames, cols=6)))
        files.append('creature_%s.png (rest, then each animation at 30%%: 3/4 and side view; %s)'
                     % (c.id, ', '.join(c.anims) or 'no animations'))
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec')
    ap.add_argument('--out', default='out')
    ap.add_argument('--targets', default='', help='comma list, or all (default: previews + .bbmodel only)')
    ap.add_argument('--ns', help='namespace (overrides NAMESPACE in the spec)')
    ap.add_argument('--formats', default='%d-%d' % PACK_FORMATS, help='Java pack formats, e.g. 46-97')
    ap.add_argument('--author', default='')
    a = ap.parse_args(argv)

    mod, models = load_spec(a.spec)
    ns = (a.ns or getattr(mod, 'NAMESPACE', '')).strip()
    if not ns or set(ns) - NS_OK or ns == 'minecraft':
        raise SystemExit('Namespace %r: use your own lowercase name (a-z 0-9 _ - .), never minecraft' % ns)
    targets = list(TARGETS) if a.targets == 'all' else [t for t in a.targets.split(',') if t]
    bad = [t for t in targets if t not in TARGETS]
    if bad:
        raise SystemExit('Unknown targets %s. Choose from: %s' % (bad, ', '.join(TARGETS)))
    lo, hi = (int(x) for x in a.formats.split('-'))
    p = Project(ns, getattr(mod, 'TITLE', ns), a.author or getattr(mod, 'AUTHOR', ''), models, (lo, hi))

    errors, warns, notes = check(p, targets)
    for e in errors:
        print('ERROR  ' + e)
    if errors:
        raise SystemExit(1)

    out = os.path.abspath(a.out)
    print('Models (%s):' % ns)
    newest = (1, 21, 4)
    for it in p.items:
        need = it.min_java()
        newest = max(newest, need)
        print('  item     %-28s %-10s on %-18s %3dpx%s  Java %s+' % (
            it.id, it.style, it.base, it.side, ' x%d frames' % len(it.frames) if it.animated else '',
            '.'.join(map(str, need))))
    for ar in p.armors:
        print('  armor    %s' % ar.id)
    for c in p.creatures:
        print('  creature %-28s %d bones, %d cubes, %dpx, hitbox %gx%g, anims: %s' % (
            c.id, len(c.all_bones), len(c.cubes), c.model.side, c.hitbox[0], c.hitbox[1], ', '.join(c.anims) or '-'))
    if newest > (1, 21, 4):
        print('NOTE   some item rotations need Java %s+ (see Java column): older clients show those models '
              'broken. Use only 22.5-degree steps on one axis to support 1.21.4.' % '.'.join(map(str, newest)))
    for n in notes:
        print('NOTE   ' + n)
    for w in warns:
        print('WARN   ' + w)

    files = previews(p, os.path.join(out, 'preview'))
    for it in p.items:
        write(os.path.join(out, 'blockbench', 'items', it.id + '.bbmodel'), it.bbmodel(ns))
    for c in p.creatures:
        write(os.path.join(out, 'blockbench', 'creatures', c.id + '.bbmodel'), c.bbmodel())

    notes = []
    for t in targets:
        notes += ['**%s**: %s' % (t, n) for n in TARGETS[t](p, os.path.join(out, t))]
    lines = ['# Install: %s' % p.title, '', 'Built from `%s`.' % os.path.basename(a.spec), '']
    lines += ['- ' + n for n in notes] or ['- No targets: only previews and Blockbench projects.']
    lines += ['', 'Previews in `preview/`: ' + '; '.join(files) + '.',
              'Blockbench projects in `blockbench/` (open, tweak, re-export by hand if needed).']
    write(os.path.join(out, 'INSTALL.md'), '\n'.join(lines) + '\n')
    print('\nWrote %s' % out)
    for f in files:
        print('  preview/' + f)
    for t in targets:
        print('  %s/' % t)
    print('  INSTALL.md')


if __name__ == '__main__':
    main()
