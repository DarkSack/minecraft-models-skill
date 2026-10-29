"""
Draws a cube model into an image with nothing but Python: the Bedrock inventory icon
(Bedrock cannot show a 3D model in the inventory) and the previews used to review a
model without opening the game.

Orthographic projection from +z (south, as Java's inventory looks), z-buffer, texture
per face and a fixed light from the front and above. Glowing parts (light_emission)
are not darkened and leave a soft halo.
"""
import copy
import math

from .geom import FACES, apply, display_rot, matmul, rot


def _norm(v):
    n = math.sqrt(sum(a * a for a in v)) or 1.0
    return [a / n for a in v]


LIGHT = _norm([-0.35, 0.6, 0.72])


def render(model, side=64, frame=0, view=None, window=None, halo=True, ss=2, use_gui=True):
    """
    RGBA image `side` x `side`.
    view:   extra rotation matrix around the model center (three-quarter or turning views).
    window: (x0, y0, width) of the visible area in model units; default the inventory slot 0..16.
    use_gui: apply the model's display.gui transform (what the inventory shows).
    """
    tex = model.frames[frame % len(model.frames)]
    d = (model.display or {}).get('gui', {}) if use_gui else {}
    s = d.get('scale', [1, 1, 1])[0]
    t = d.get('translation', [0, 0, 0])
    gr = display_rot(d['rotation']) if d.get('rotation') and any(d['rotation']) else None
    x0, y0, width = window or (0.0, 0.0, 16.0)
    n = side * ss
    k = n / width
    zb = [[-1e9] * n for _ in range(n)]
    col = [[None] * n for _ in range(n)]
    glow = [[False] * n for _ in range(n)]

    def tf(p):
        q = [p[0] - 8, p[1] - 8, p[2] - 8]
        if view:
            q = apply(view, q)
        if gr:
            q = apply(gr, q)
        return [q[0] * s + t[0] + 8, q[1] * s + t[1] + 8, q[2] * s + t[2] + 8]

    for i, p in enumerate(model.parts):
        for f in FACES:
            if f in p.hide or (i, f) not in model.uv:
                continue
            a, b, c = [tf(v) for v in p.face_corners(f)]
            u = [b[j] - a[j] for j in range(3)]
            v = [c[j] - a[j] for j in range(3)]
            nrm = _norm([v[1] * u[2] - v[2] * u[1], v[2] * u[0] - v[0] * u[2], v[0] * u[1] - v[1] * u[0]])
            if nrm[2] <= 1e-4:
                continue                                        # facing away
            lum = 0.42 + 0.58 * max(0.0, sum(nrm[j] * LIGHT[j] for j in range(3)))
            if p.light:
                lum = max(lum, 0.85 + p.light / 100.0)
            A = ((a[0] - x0) * k, (y0 + width - a[1]) * k)
            U, V = (u[0] * k, -u[1] * k), (v[0] * k, -v[1] * k)
            det = U[0] * V[1] - U[1] * V[0]
            if abs(det) < 1e-9:
                continue
            xs = [A[0], A[0] + U[0], A[0] + V[0], A[0] + U[0] + V[0]]
            ys = [A[1], A[1] + U[1], A[1] + V[1], A[1] + U[1] + V[1]]
            tx, ty, tw, th = model.uv[(i, f)]
            for py in range(max(0, int(min(ys))), min(n, int(max(ys)) + 1)):
                for px in range(max(0, int(min(xs))), min(n, int(max(xs)) + 1)):
                    qx, qy = px + 0.5 - A[0], py + 0.5 - A[1]
                    su = (qx * V[1] - qy * V[0]) / det
                    sv = (U[0] * qy - U[1] * qx) / det
                    if not (0 <= su <= 1 and 0 <= sv <= 1):
                        continue
                    z = a[2] + u[2] * su + v[2] * sv
                    if z <= zb[py][px]:
                        continue
                    texel = tex[ty + min(th - 1, int(sv * th))][tx + min(tw - 1, int(su * tw))]
                    if texel[3] < 128:
                        continue
                    zb[py][px] = z
                    col[py][px] = tuple(min(255, int(ch * lum)) for ch in texel[:3])
                    glow[py][px] = bool(p.light)

    img = [[(0, 0, 0, 0)] * side for _ in range(side)]
    for y in range(side):
        for x in range(side):
            acc, cnt = [0, 0, 0], 0
            for dy in range(ss):
                for dx in range(ss):
                    c = col[y * ss + dy][x * ss + dx]
                    if c:
                        acc = [acc[j] + c[j] for j in range(3)]
                        cnt += 1
            if cnt:
                img[y][x] = (acc[0] // cnt, acc[1] // cnt, acc[2] // cnt, 255 * cnt // (ss * ss))
    if halo:
        _halo(img, glow, ss, side)
    return img


def _halo(img, glow, ss, side, radius=3):
    """Glow around emissive pixels: their color, fading out."""
    src = {}
    for y in range(side):
        for x in range(side):
            if any(glow[y * ss + dy][x * ss + dx] for dy in range(ss) for dx in range(ss)):
                src[(x, y)] = img[y][x]
    for (fx, fy), c in src.items():
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                x, y = fx + dx, fy + dy
                d = math.hypot(dx, dy)
                if not (0 <= x < side and 0 <= y < side) or d == 0 or d > radius:
                    continue
                a = int(110 * (1 - d / (radius + 0.5)) ** 2)
                cur = img[y][x]
                if cur[3] < 200 and a > cur[3]:
                    img[y][x] = (min(255, c[0] + 30), min(255, c[1] + 30), min(255, c[2] + 30), a)


def three_quarter(model, side=96):
    """The model turned 35 degrees and tilted from above, framed to fit, without the inventory transform."""
    m, window = centered(model)
    return render(m, side, view=matmul(rot(x=-22), rot(y=-35)), window=window, use_gui=False)


def turntable(model, side=96, steps=8, tilt=-18, window=None):
    """Frames of a full turn, slightly tilted, cycling the animated texture."""
    return [render(model, side, frame=i, view=matmul(rot(x=-tilt), rot(y=360.0 * i / steps)), window=window,
                   use_gui=False) for i in range(steps)]


def centered(model, margin=1.0):
    """A copy moved so its bounding box is centered on (8, 8, 8) (where views rotate) and the
    square window that holds it from any angle."""
    m = copy.copy(model)
    m.parts = [copy.deepcopy(p) for p in model.parts]
    vs = [v for p in m.parts for v in p.vertices()]
    lo = [min(v[i] for v in vs) for i in range(3)]
    hi = [max(v[i] for v in vs) for i in range(3)]
    for p in m.parts:
        p.move([8 - (a + b) / 2.0 for a, b in zip(lo, hi)])
    w = math.sqrt(sum((b - a) ** 2 for a, b in zip(lo, hi))) + 2 * margin
    return m, (8 - w / 2.0, 8 - w / 2.0, w)
