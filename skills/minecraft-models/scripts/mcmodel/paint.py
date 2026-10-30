"""
Colors, ramps, PNG files and the face painters.

A material is a dict: {'type': <painter name>, 'ramp': [colors dark -> light], ...options}.
Every face of every cube gets its own rectangle in the texture atlas and the painter of
its material fills it. Painters receive (mat, face, w, h, rnd, part, phase, index):
the face name, its size in pixels, a seeded Random for that face, the Part, the
animation phase (0-1) and the part index.
"""
import math
import random
import struct
import zlib

CLEAR = (0, 0, 0, 0)


# ---------------------------------------------------------------- color

def hex_rgba(h):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def mix(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3)) + (max(a[3], b[3]),)


def ramp(*stops, n=8):
    """
    `n` colors from dark to light through the given stops ('#rrggbb' or RGBA tuples).
    One stop builds a ramp around it (darker below, lighter above).
    """
    cols = [hex_rgba(s) if isinstance(s, str) else tuple(s) for s in stops]
    if len(cols) == 1:
        c = cols[0]
        cols = [mix(c, (0, 0, 0, 255), 0.65), c, mix(c, (255, 255, 255, 255), 0.55)]
    out = []
    for k in range(n):
        t = k / float(n - 1) * (len(cols) - 1)
        i = min(int(t), len(cols) - 2)
        out.append(mix(cols[i], cols[i + 1], t - i))
    return out


def material(kind, ramp_, **options):
    """
    A material. `kind` is a painter name (see PAINTERS). Common options:
      glow=0-15     light_emission of every part made of it (Java) and a halo in previews
      tone=0-1      where on the ramp the base color sits
      energy=ramp   second ramp for 'rune' and 'cracked'
      edge=ramp     glowing edge for 'metal'; flat=True: no bevel (parts forming one surface)
      animate=True  force animation frames (Java .mcmeta; Bedrock shows frame 0)
    """
    if kind not in PAINTERS:
        raise ValueError('unknown painter %r (choose from %s)' % (kind, ', '.join(sorted(PAINTERS))))
    m = dict(options)
    m['type'] = kind
    m['ramp'] = list(ramp_)
    return m


# ---------------------------------------------------------------- PNG

def png_bytes(px):
    """RGBA rows -> PNG file bytes (8-bit, no interlace)."""
    h, w = len(px), len(px[0])
    raw = b''.join(b'\x00' + bytes(c for p in row for c in p) for row in px)

    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)

    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def read_png(path):
    """PNG file -> RGBA rows. 8-bit gray/RGB/RGBA/gray-alpha and palette (any depth)."""
    data = open(path, 'rb').read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'not a PNG: %s' % path
    pos, idat, palette, trns = 8, b'', None, None
    while pos < len(data):
        length, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b'IHDR':
            w, h, depth, ctype, _, _, interlace = struct.unpack('>IIBBBBB', body)
            assert interlace == 0, '%s: interlaced PNG not supported' % path
        elif kind == b'PLTE':
            palette = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif kind == b'tRNS':
            trns = body
        elif kind == b'IDAT':
            idat += body
        elif kind == b'IEND':
            break
    raw = zlib.decompress(idat)
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    if ctype == 3 and depth < 8:
        bpp, stride = 1, (w * depth + 7) // 8
    else:
        assert depth == 8, '%s: only 8-bit PNGs (or palette)' % path
        bpp, stride = channels, w * channels
    rows, prev, i = [], bytearray(stride), 0
    for _ in range(h):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    px = []
    for line in rows:
        row = []
        for x in range(w):
            if ctype == 3:
                if depth < 8:
                    per = 8 // depth
                    idx = (line[x // per] >> (8 - depth * (x % per + 1))) & ((1 << depth) - 1)
                else:
                    idx = line[x]
                r, g, b = palette[idx]
                row.append((r, g, b, trns[idx] if trns and idx < len(trns) else 255))
            elif ctype == 6:
                row.append(tuple(line[x * 4:x * 4 + 4]))
            elif ctype == 2:
                row.append(tuple(line[x * 3:x * 3 + 3]) + (255,))
            elif ctype == 4:
                row.append((line[x * 2],) * 3 + (line[x * 2 + 1],))
            else:
                row.append((line[x],) * 3 + (255,))
        px.append(row)
    return px


def scale_img(px, k):
    return [[p for p in row for _ in range(k)] for row in px for _ in range(k)]


def sheet(images, cols=8, gap=4, bg=(40, 40, 46, 255)):
    """Images of the same size side by side, with a checkerboard behind transparency."""
    if not images:
        return [[bg]]
    side_w, side_h = len(images[0][0]), len(images[0])
    rows = (len(images) + cols - 1) // cols
    cols = min(cols, len(images))
    W, H = cols * side_w + (cols + 1) * gap, rows * side_h + (rows + 1) * gap
    out = [[bg] * W for _ in range(H)]
    for n, img in enumerate(images):
        ox, oy = gap + (n % cols) * (side_w + gap), gap + (n // cols) * (side_h + gap)
        for y, row in enumerate(img):
            for x, p in enumerate(row):
                back = (70, 70, 78, 255) if (x // 6 + y // 6) % 2 else (58, 58, 64, 255)
                out[oy + y][ox + x] = mix(back, p, p[3] / 255.0)[:3] + (255,) if p[3] < 255 else p
    return out


# ---------------------------------------------------------------- painter helpers

def _at(r, i):
    return r[max(0, min(len(r) - 1, int(round(i))))]


def _face_tone(f):
    """How much each face shifts on the ramp (the game shades too; this only helps)."""
    return {'up': 1.0, 'down': -1.0}.get(f, 0.0)


def _bevel(px, w, h, light, dark, k=0.45):
    """One-pixel edge: light top-left, dark bottom-right. Keeps edges readable."""
    for y in range(h):
        for x in range(w):
            if y == 0 or x == 0:
                px[y][x] = mix(px[y][x], light, k)
            elif y == h - 1 or x == w - 1:
                px[y][x] = mix(px[y][x], dark, k)


def _along(f):
    """Side faces run along the part's length (y); top and bottom do not."""
    return f not in ('up', 'down')


def _noise(rnd, w, h, cell=3):
    """Smooth value noise (bilinear over a coarse grid)."""
    gw, gh = w // cell + 2, h // cell + 2
    g = [[rnd.uniform(-1, 1) for _ in range(gw)] for _ in range(gh)]
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            fx, fy = x / float(cell), y / float(cell)
            x0, y0 = int(fx), int(fy)
            tx, ty = fx - x0, fy - y0
            a = g[y0][x0] * (1 - tx) + g[y0][x0 + 1] * tx
            b = g[y0 + 1][x0] * (1 - tx) + g[y0 + 1][x0 + 1] * tx
            row.append(a * (1 - ty) + b * ty)
        out.append(row)
    return out


# ---------------------------------------------------------------- painters

def metal(mat, f, w, h, rnd, p, phase, i):
    """Brushed metal, light toward the tip, with a bright bevel; `edge` adds a glowing rim."""
    r = mat['ramp']
    b = mat.get('tone', 0.55) * len(r) + _face_tone(f)
    brushed = [rnd.uniform(-0.3, 0.3) for _ in range(w)]
    px = []
    for y in range(h):
        row = []
        for x in range(w):
            t = 1.0 - y / float(max(1, h - 1)) if _along(f) and not mat.get('flat') else 0.5
            v = b - 0.8 + 1.4 * t + brushed[x]
            if w > 3 and x in (1, w - 2):
                v += 1.2
            row.append(_at(r, v))
        px.append(row)
    edge = mat.get('edge')
    if edge and _along(f) and w > 2:
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * phase + i)
        for y in range(h):
            for x in (0, w - 1):
                px[y][x] = _at(edge, len(edge) - 2 + pulse)
    if not mat.get('flat'):
        _bevel(px, w, h, r[-1], r[1])
    return px


def plate(mat, f, w, h, rnd, p, phase, i):
    """Armor plating: panels split by dark seams every `panel` px (default 12), a rivet in each corner
    of panels on faces at least 8 px across."""
    r = mat['ramp']
    n = max(6, int(mat.get('panel', 12)))
    b = mat.get('tone', 0.5) * len(r) + _face_tone(f)
    px = [[_at(r, b + rnd.uniform(-0.25, 0.25)) for _ in range(w)] for _ in range(h)]
    studs = min(w, h) >= 8
    for y in range(h):
        for x in range(w):
            if (0 < x < w - 1 and x % n == n - 1) or (0 < y < h - 1 and y % n == n - 1):
                px[y][x] = r[1]
            elif studs and x % n in (2, n - 3) and y % n in (2, n - 3) and x < w - 2 and y < h - 2:
                px[y][x] = r[-2]
    _bevel(px, w, h, r[-1], r[1])
    return px


def crystal(mat, f, w, h, rnd, p, phase, i):
    """Diagonal facets that slide, with sparkles that move (animated)."""
    r = mat['ramp']
    ph = rnd.uniform(0, 6) + 2 * math.pi * phase
    px = [[_at(r, len(r) * 0.55 + 1.6 * math.sin((x * 0.9 + y * 0.45) * 0.55 + ph) + _face_tone(f)
               + (1 - y / float(max(1, h))) * 1.2) for x in range(w)] for y in range(h)]
    sparks = random.Random(rnd.random() + int(phase * 16))
    for _ in range(max(1, w * h // 40)):
        px[sparks.randrange(h)][sparks.randrange(w)] = r[-1]
    _bevel(px, w, h, r[-1], r[max(1, len(r) // 3)])
    return px


def energy(mat, f, w, h, rnd, p, phase, i):
    """Bands of energy running along the part, brighter core (animated). Option: cycles."""
    r = mat['ramp']
    cycles = mat.get('cycles', 2.0)
    px = []
    for y in range(h):
        row = []
        for x in range(w):
            v = (y / float(max(1, h))) if _along(f) else (x / float(max(1, w)))
            wave = math.sin(2 * math.pi * (v * cycles + phase) + i * 0.7)
            core = 1.0 - abs((x + 0.5) / w - 0.5) * 2 if w > 2 else 1.0
            row.append(_at(r, len(r) * 0.45 + 1.8 * wave + 1.6 * core + rnd.uniform(-0.3, 0.3)))
        px.append(row)
    return px


def rune(mat, f, w, h, rnd, p, phase, i):
    """Dark stone or metal with carved glyphs that pulse in the `energy` ramp (animated)."""
    r, e = mat['ramp'], mat['energy']
    px = [[_at(r, len(r) * 0.45 + _face_tone(f) + rnd.uniform(-0.35, 0.35)) for _ in range(w)] for _ in range(h)]
    _bevel(px, w, h, r[-2], r[0])
    if w >= 5 and h >= 5 and _along(f):
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * phase + i * 1.3)
        for cy in range(1, h - 4, 6):
            glyph = rnd.randrange(1 << 9)
            for gy in range(3):
                for gx in range(3):
                    if glyph >> (gy * 3 + gx) & 1 or (gx == 1 and gy == 1):
                        y = cy + gy
                        if 0 <= y < h:
                            px[y][(w - 3) // 2 + gx] = _at(e, len(e) - 3 + 2 * pulse)
    return px


def grip(mat, f, w, h, rnd, p, phase, i):
    """Wrapped handle: diagonal bands."""
    r = mat['ramp']
    px = [[_at(r, len(r) * 0.5 + (-1.3 if (x + y) % 5 in (0, 1) and _along(f) else 0) + _face_tone(f))
           for x in range(w)] for y in range(h)]
    _bevel(px, w, h, r[-2], r[0])
    return px


def trim(mat, f, w, h, rnd, p, phase, i):
    """Guards, rims and bands: light top half, an engraved line in the middle."""
    r = mat['ramp']
    px = []
    for y in range(h):
        row = []
        for x in range(w):
            v = len(r) * 0.6 + _face_tone(f) + (0.9 if y < h / 2.0 else -0.4)
            if h >= 5 and y == h // 2:
                v -= 2
            row.append(_at(r, v))
        px.append(row)
    _bevel(px, w, h, r[-1], r[1])
    return px


def gem(mat, f, w, h, rnd, p, phase, i):
    """Cut gem with a highlight; `pulse=True` makes it throb (animated)."""
    r = mat['ramp']
    pulse = 0.6 * math.sin(2 * math.pi * phase + i) if mat.get('pulse') else 0.0
    px = [[_at(r, len(r) - 1 - 5.5 * math.hypot((x + 0.5) / w - 0.35, (y + 0.5) / h - 0.3)
               + _face_tone(f) * 0.5 + pulse) for x in range(w)] for y in range(h)]
    px[max(0, h // 4)][max(0, w // 4)] = r[-1]
    return px


def orb(mat, f, w, h, rnd, p, phase, i):
    """A swirl that turns: the inside of an energy orb (animated)."""
    r = mat['ramp']
    px = []
    for y in range(h):
        row = []
        for x in range(w):
            dx, dy = (x + 0.5) / w - 0.5, (y + 0.5) / h - 0.5
            a, d = math.atan2(dy, dx), math.hypot(dx, dy)
            row.append(_at(r, len(r) - 1.5 - 4 * d + 1.4 * math.sin(3 * a + 10 * d - 2 * math.pi * phase + i)))
        px.append(row)
    return px


def wood(mat, f, w, h, rnd, p, phase, i):
    r = mat['ramp']
    grain = [rnd.random() < 0.3 for _ in range(w)]
    px = [[_at(r, len(r) * mat.get('tone', 0.5) + _face_tone(f) - (1 if grain[x] else 0) + rnd.uniform(-0.3, 0.3))
           for x in range(w)] for y in range(h)]
    _bevel(px, w, h, r[-2], r[0])
    return px


def bone(mat, f, w, h, rnd, p, phase, i):
    """Bone or ivory, darker toward the base, with thin cracks."""
    r = mat['ramp']
    px = [[_at(r, len(r) * 0.62 + _face_tone(f) - 1.2 * (y / float(max(1, h - 1)) if _along(f) else 0.5)
               + rnd.uniform(-0.3, 0.3)) for x in range(w)] for y in range(h)]
    for _ in range(max(0, w * h // 90)):
        x, y = rnd.randrange(w), rnd.randrange(h)
        for _ in range(rnd.randrange(2, 5)):
            if 0 <= x < w and 0 <= y < h:
                px[y][x] = r[2]
            x += rnd.choice((-1, 0, 1))
            y += 1
    _bevel(px, w, h, r[-1], r[1], 0.3)
    return px


def scales(mat, f, w, h, rnd, p, phase, i):
    """Staggered rows of scales (option size=4)."""
    r = mat['ramp']
    n = mat.get('size', 4)
    px = []
    for y in range(h):
        row = []
        for x in range(w):
            fy, fx = y % n, (x + (n // 2 if (y // n) % 2 else 0)) % n
            border = fy == n - 1 or (fy >= n // 2 and fx in (0, n - 1))
            row.append(_at(r, len(r) * 0.55 + _face_tone(f) + (1.2 - fy * 2.0 / n) - (2.2 if border else 0)))
        px.append(row)
    _bevel(px, w, h, r[-2], r[0], 0.3)
    return px


def skin(mat, f, w, h, rnd, p, phase, i):
    """Skin or leather: soft blotches and grain (option cell=3)."""
    r = mat['ramp']
    n = _noise(rnd, w, h, mat.get('cell', 3))
    px = [[_at(r, len(r) * mat.get('tone', 0.5) + _face_tone(f) * 0.8 + 1.1 * n[y][x] + rnd.uniform(-0.25, 0.25))
           for x in range(w)] for y in range(h)]
    if not mat.get('flat'):
        _bevel(px, w, h, r[-2], r[1], 0.25)
    return px


def fur(mat, f, w, h, rnd, p, phase, i):
    """Hair: strands along the part, darker at the root."""
    r = mat['ramp']
    b = len(r) * mat.get('tone', 0.55) + _face_tone(f)
    strands = [rnd.uniform(-1.2, 1.2) for _ in range(w + 2)]
    return [[_at(r, b + strands[x] * 0.8 + strands[(x + y // 3) % (w + 2)] * 0.4 - 0.8 * y / float(max(1, h)))
             if _along(f) else _at(r, b + rnd.uniform(-1, 1)) for x in range(w)] for y in range(h)]


def cracked(mat, f, w, h, rnd, p, phase, i):
    """Dark rock split by cracks of magma or energy (`energy` ramp; option every=55)."""
    r, e = mat['ramp'], mat['energy']
    n = _noise(rnd, w, h, 4)
    px = [[_at(r, len(r) * 0.45 + _face_tone(f) + 1.3 * n[y][x] + rnd.uniform(-0.3, 0.3)) for x in range(w)]
          for y in range(h)]
    _bevel(px, w, h, r[-2], r[0], 0.35)
    for _ in range(max(1, w * h // mat.get('every', 55))):
        x, y = rnd.randrange(w), rnd.randrange(h)
        for _ in range(rnd.randrange(3, 3 + max(w, h))):
            if 0 <= x < w and 0 <= y < h:
                px[y][x] = _at(e, len(e) - 2 + rnd.uniform(-1, 1))
                if x + 1 < w and rnd.random() < 0.3:
                    px[y][x + 1] = _at(e, len(e) * 0.5)
            x += rnd.choice((-1, 0, 0, 1))
            y += rnd.choice((-1, 1, 1))
    return px


def cloth(mat, f, w, h, rnd, p, phase, i):
    """Cloth with vertical folds; `hem=ramp` adds a border, `torn=True` frays the bottom edge."""
    r = mat['ramp']
    ph = rnd.uniform(0, 6)
    px = [[_at(r, len(r) * mat.get('tone', 0.45) + _face_tone(f) + rnd.uniform(-0.2, 0.2)
               + (math.sin(x * 1.3 + ph) * 0.9 + math.sin(x * 0.45 + ph * 2) * 0.6 if _along(f) else 0))
           for x in range(w)] for y in range(h)]
    hem = mat.get('hem')
    if hem and _along(f) and h > 4:
        for x in range(w):
            px[h - 2][x] = _at(hem, len(hem) * 0.7)
    if mat.get('torn') and _along(f):
        for x in range(w):
            for y in range(h - rnd.randrange(0, max(2, h // 3)), h):
                px[y][x] = CLEAR
    return px


def eye(mat, f, w, h, rnd, p, phase, i):
    r = mat['ramp']
    return [[r[-1] if (0 < x < w - 1 and 0 < y < h - 1) or w <= 2 or h <= 2 else r[-3] for x in range(w)]
            for y in range(h)]


def flat(mat, f, w, h, rnd, p, phase, i):
    """One color with a little noise (option tone = ramp index)."""
    r = mat['ramp']
    return [[_at(r, mat.get('tone', len(r) // 2) + rnd.uniform(-0.4, 0.4)) for x in range(w)] for y in range(h)]


PAINTERS = {'metal': metal, 'plate': plate, 'crystal': crystal, 'energy': energy, 'rune': rune, 'grip': grip, 'trim': trim,
            'gem': gem, 'orb': orb, 'wood': wood, 'bone': bone, 'scales': scales, 'skin': skin, 'fur': fur,
            'cracked': cracked, 'cloth': cloth, 'eye': eye, 'flat': flat}
ANIMATED = {'crystal', 'energy', 'rune', 'orb'}


def is_animated(mat):
    return bool(mat.get('animate') or mat['type'] in ANIMATED or (mat['type'] == 'metal' and mat.get('edge'))
                or (mat['type'] == 'gem' and mat.get('pulse')))
