"""
Cubes and the helpers that build shapes out of them.

Units are model pixels: a vanilla item or block spans 0..16 on each axis, y is up.
Item models are built around (8, 8, 8) and seen from +z (south) in the inventory.
Creatures are built around their feet at (0, 0, 0) and face -z (north).

Rotations are in degrees and applied like Minecraft does: X first, then Y, then Z.
"""
import math

FACES = ('north', 'south', 'east', 'west', 'up', 'down')
# Where each face ends up after a +90 degree turn around x, y, z.
_QUARTER = ({'up': 'south', 'south': 'down', 'down': 'north', 'north': 'up'},
            {'east': 'north', 'south': 'east', 'west': 'south', 'north': 'west'},
            {'east': 'up', 'up': 'west', 'west': 'down', 'down': 'east'})


# ---------------------------------------------------------------- rotation math

def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def apply(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def rot(x=0.0, y=0.0, z=0.0):
    """Rotation matrix as Minecraft applies element rotations: X, then Y, then Z (degrees)."""
    return matmul(_rz(math.radians(z)), matmul(_ry(math.radians(y)), _rx(math.radians(x))))


def display_rot(r):
    """Rotation of a Java `display` transform (rotationXYZ: Rx * Ry * Rz)."""
    rx, ry, rz = [math.radians(a) for a in r]
    return matmul(_rx(rx), matmul(_ry(ry), _rz(rz)))


def angles(m):
    """Inverse of `rot`: the (x, y, z) angles in degrees."""
    b = math.asin(max(-1.0, min(1.0, -m[2][0])))
    if abs(math.cos(b)) > 1e-6:
        a, c = math.atan2(m[2][1], m[2][2]), math.atan2(m[1][0], m[0][0])
    else:                                           # gimbal lock: put it all on X
        a, c = math.atan2(-m[1][2], m[1][1]), 0.0
    r = [round(math.degrees(v), 4) for v in (a, b, c)]
    return [0.0 if abs(v) < 1e-4 else v for v in r]


# ---------------------------------------------------------------- the cube

class Part:
    """
    One cube from `frm` to `to`, rotated `r` = (x, y, z) degrees around `origin`
    (its center by default). `light` = Java light_emission 0-15 (default: the
    material's `glow`). `hide` = faces never drawn (always covered).
    """

    def __init__(self, name, frm, to, mat, r=None, origin=None, light=None, hide=()):
        self.name = name
        self.frm = [float(v) for v in frm]
        self.to = [float(v) for v in to]
        self.mat = mat
        self.m = rot(*r) if r else rot()
        self.origin = list(origin) if origin else [(a + b) / 2.0 for a, b in zip(self.frm, self.to)]
        self.light = light
        self.hide = set(hide)

    def rotate(self, m, center):
        """
        Apply rotation `m` around `center` on top of the current one. An element has a
        single pivot, so the pivot moves to where it lands and the box follows: same solid.
        """
        rel = [o - c for o, c in zip(self.origin, center)]
        new = [a + c for a, c in zip(apply(m, rel), center)]
        self.move([n - o for n, o in zip(new, self.origin)])
        self.m = matmul(m, self.m)
        return self

    def move(self, d):
        self.frm = [v + dv for v, dv in zip(self.frm, d)]
        self.to = [v + dv for v, dv in zip(self.to, d)]
        self.origin = [v + dv for v, dv in zip(self.origin, d)]
        return self

    def size(self):
        return [b - a for a, b in zip(self.frm, self.to)]

    def face_size(self, f):
        """Width and height of a face in model units, as seen from the front of that face."""
        sx, sy, sz = self.size()
        return {'north': (sx, sy), 'south': (sx, sy), 'east': (sz, sy), 'west': (sz, sy),
                'up': (sx, sz), 'down': (sx, sz)}[f]

    def face_corners(self, f):
        """Top-left, top-right and bottom-left corners of a face, rotated: the UV frame."""
        x0, y0, z0 = self.frm
        x1, y1, z1 = self.to
        c = {'south': ((x0, y1, z1), (x1, y1, z1), (x0, y0, z1)),
             'north': ((x1, y1, z0), (x0, y1, z0), (x1, y0, z0)),
             'east': ((x1, y1, z1), (x1, y1, z0), (x1, y0, z1)),
             'west': ((x0, y1, z0), (x0, y1, z1), (x0, y0, z0)),
             'up': ((x0, y1, z0), (x1, y1, z0), (x0, y1, z1)),
             'down': ((x0, y0, z1), (x1, y0, z1), (x0, y0, z0))}[f]
        return [self.point(p) for p in c]

    def point(self, p):
        rel = [a - o for a, o in zip(p, self.origin)]
        return [a + o for a, o in zip(apply(self.m, rel), self.origin)]

    def vertices(self):
        x0, y0, z0 = self.frm
        x1, y1, z1 = self.to
        return [self.point((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]

    def angles(self):
        return angles(self.m)

    def within_45(self):
        """
        A single-axis rotation beyond +-45 degrees, rewritten as a quarter turn baked into the box
        (sizes swapped, faces renamed) plus the rest: the same solid, but readable by Java clients
        before 1.21.11 (which only accept -45..45). Multi-axis rotations are left alone.
        """
        m = self.m
        axis = [i for i in range(3) if abs(m[i][i] - 1) < 1e-9]
        if len(axis) != 1:                      # identity (3) or not a single-axis rotation (0)
            return self
        i = axis[0]
        ang = math.degrees([math.atan2(m[2][1], m[1][1]), math.atan2(m[0][2], m[0][0]),
                            math.atan2(m[1][0], m[0][0])][i])
        while abs(ang) > 45 + 1e-6:
            step = 90 if ang > 0 else -90
            q = rot(**{'xyz'[i]: step})
            c = [(lo + hi) / 2.0 for lo, hi in zip(self.frm, self.to)]
            c = [o + d for o, d in zip(self.origin, apply(q, [x - o for x, o in zip(c, self.origin)]))]
            s = self.size()
            j, k = [n for n in range(3) if n != i]
            s[j], s[k] = s[k], s[j]
            self.frm = [cc - ss / 2.0 for cc, ss in zip(c, s)]
            self.to = [cc + ss / 2.0 for cc, ss in zip(c, s)]
            turn = _QUARTER[i] if step > 0 else {v: k_ for k_, v in _QUARTER[i].items()}
            self.hide = {turn.get(f, f) for f in self.hide}
            ang -= step
        self.m = rot(**{'xyz'[i]: ang})
        return self


# ---------------------------------------------------------------- shape helpers

def box(name, center, size, mat, r=None, light=None, hide=()):
    """A cube centered on `center` that rotates around itself."""
    frm = [c - s / 2.0 for c, s in zip(center, size)]
    to = [c + s / 2.0 for c, s in zip(center, size)]
    return Part(name, frm, to, mat, r=r, origin=list(center), light=light, hide=hide)


def bar(name, p0, p1, width, depth, mat, z=8.0, light=None, overlap=0.0, tilt=0.0):
    """A beam from p0 to p1 (x, y) in the xy plane at depth z: a blade, a shaft, an arm."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dy) + overlap
    a = math.degrees(math.atan2(dy, dx)) - 90.0
    c = [(p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0, z]
    return box(name, c, [width, length, depth], mat, r=(0, tilt, a), light=light)


def curve(name, points, widths, depth, mat, z=8.0, light=None, overlap=0.35):
    """Straight beams along a polyline; width goes from widths[0] to widths[-1]."""
    out, n = [], len(points) - 1
    for i in range(n):
        t = i / float(max(1, n - 1))
        w = widths[0] + (widths[-1] - widths[0]) * t if len(widths) == 2 else widths[min(i, len(widths) - 1)]
        d = depth[0] + (depth[-1] - depth[0]) * t if isinstance(depth, (list, tuple)) else depth
        out.append(bar(name, points[i], points[i + 1], w, d, mat, z=z, light=light, overlap=overlap))
    return out


def arc(c, r, a0, a1, n, ry=None):
    """Points on an arc (degrees, counter-clockwise from +x). `ry` squashes it into an ellipse."""
    ry = r if ry is None else ry
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / float(n))),
             c[1] + ry * math.sin(math.radians(a0 + (a1 - a0) * i / float(n)))) for i in range(n + 1)]


def orb(name, c, radius, mat, light=15):
    """Three rotated cubes that intersect: reads as round from every side."""
    s = radius * 1.55
    return [box(name, c, [s, s, s], mat, r=(0, 45, 0), light=light),
            box(name, c, [s * 0.98] * 3, mat, r=(45, 0, 0), light=light),
            box(name, c, [s * 0.96] * 3, mat, r=(0, 0, 45), light=light)]


def ring(name, c, radius, n, size, mat, tilt=0.0, light=None, phase=0.0, axis='y'):
    """`n` cubes spread on a circle around `axis` through `c`: orbiting runes, a guard, links."""
    out = []
    g = rot(x=tilt) if axis == 'y' else rot(y=tilt)
    for i in range(n):
        a = 2 * math.pi * (i + phase) / n
        if axis == 'y':
            local, r = [radius * math.cos(a), 0.0, radius * math.sin(a)], (tilt, -math.degrees(a), 0)
        else:
            local, r = [radius * math.cos(a), radius * math.sin(a), 0.0], (0, tilt, math.degrees(a))
        p = apply(g, local)
        out.append(box(name, [c[0] + p[0], c[1] + p[1], c[2] + p[2]], size, mat, r=r, light=light))
    return out


def spikes(name, p0, p1, n, length, width, mat, side=1, lean=0.0, z=8.0, depth=None, light=None):
    """`n` spikes along p0-p1 pointing to one side; `lean` tilts them forward or back."""
    out = []
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * side, dx / L * side
    base = math.degrees(math.atan2(ny, nx)) - 90.0 + lean * side
    for i in range(n):
        t = (i + 0.5) / n
        r = math.radians(base + 90.0)
        c = [p0[0] + dx * t + math.cos(r) * length * 0.35, p0[1] + dy * t + math.sin(r) * length * 0.35, z]
        out.append(box(name, c, [width, length, depth or width], mat, r=(0, 0, base), light=light))
    return out


def rotate_parts(parts, m, center):
    for p in parts:
        p.rotate(m, center)
    return parts


def move_parts(parts, d):
    for p in parts:
        p.move(d)
    return parts


# ---------------------------------------------------------------- single-axis helpers (creatures)

def cube(name, center, size, mat, axis=None, angle=0.0, origin=None):
    """A cube rotated `angle` degrees around ONE axis ('x', 'y' or 'z'): what entity loaders accept."""
    r = None
    if axis and angle:
        r = {'x': (angle, 0, 0), 'y': (0, angle, 0), 'z': (0, 0, angle)}[axis]
    frm = [c - s / 2.0 for c, s in zip(center, size)]
    to = [c + s / 2.0 for c, s in zip(center, size)]
    return Part(name, frm, to, mat, r=r, origin=list(origin or center))


def limb(name, p0, p1, thick, mat, width=None, overlap=0.6):
    """
    A beam from p0 to p1 (3D) that only needs one rotation axis: the two points must share
    one coordinate (same x -> rotates on x, same z -> on z, same y -> on y).
    """
    width = thick if width is None else width
    dx, dy, dz = [b - a for a, b in zip(p0, p1)]
    L = math.sqrt(dx * dx + dy * dy + dz * dz) + overlap
    c = [(a + b) / 2.0 for a, b in zip(p0, p1)]

    def fold(a):  # a beam is the same turned 180 degrees: stay within +-90
        return a - 180 if a > 90 else a + 180 if a < -90 else a

    if abs(dx) < 1e-6:
        return cube(name, c, [width, L, thick], mat, 'x', fold(math.degrees(math.atan2(dz, dy))))
    if abs(dz) < 1e-6:
        return cube(name, c, [width, L, thick], mat, 'z', fold(math.degrees(math.atan2(-dx, dy))))
    if abs(dy) < 1e-6:
        return cube(name, c, [width, thick, L], mat, 'y', fold(math.degrees(math.atan2(dx, dz))))
    raise ValueError('%s: %s -> %s is not in an axis plane (share x, y or z)' % (name, p0, p1))


def mirror(p, name=None):
    """The part mirrored across x = 0 (the other side of a body). Single-axis parts only."""
    ax, ay, az = p.angles()
    swap = {'east': 'west', 'west': 'east'}
    return Part(name or p.name, [-p.to[0], p.frm[1], p.frm[2]], [-p.frm[0], p.to[1], p.to[2]], p.mat,
                r=(ax, -ay, -az), origin=[-p.origin[0], p.origin[1], p.origin[2]], light=p.light,
                hide={swap.get(f, f) for f in p.hide})
