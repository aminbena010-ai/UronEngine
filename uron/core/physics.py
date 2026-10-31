"""Motor de física 2D de URON.

Características:
  * BoxCollider como OBB (soporta rotación y escala del Transform).
  * CircleCollider escalado.
  * Resolución AABB/OBB vs AABB/OBB, círculo vs círculo y círculo vs OBB.
  * Capas y máscaras de colisión (por nombre).
  * Triggers/sensores separados de colisiones sólidas.
  * Raycast contra todos los colliders.
  * Fuerzas por frame, fricción y rebote.
  * Callbacks de scripts on_collision_* y on_trigger_*, y on_destroy.
"""
import math
from .layers import DEFAULT_COLLISION_LAYERS, layers

DEFAULT_GRAVITY = (0.0, 980.0)   # px/s^2 hacia abajo (Y crece hacia abajo)
DEFAULT_LAYERS = DEFAULT_COLLISION_LAYERS


# --------------------------------------------------------------------------- #
# Formas en coordenadas de mundo
# --------------------------------------------------------------------------- #
class WorldBox:
    """Caja orientada (OBB). rotation en grados, mismo convenio que Transform."""
    def __init__(self, cx, cy, w, h, rotation=0.0):
        self.cx, self.cy = float(cx), float(cy)
        self.w, self.h = max(0.0001, abs(float(w))), max(0.0001, abs(float(h)))
        self.rotation = float(rotation)
        rad = math.radians(self.rotation)
        self.cos = math.cos(rad)
        self.sin = math.sin(rad)

    def to_local(self, px, py):
        dx = float(px) - self.cx
        dy = float(py) - self.cy
        return (dx * self.cos + dy * self.sin,
                -dx * self.sin + dy * self.cos)

    def to_world_direction(self, dx, dy):
        return (dx * self.cos - dy * self.sin,
                dx * self.sin + dy * self.cos)

    def corners(self):
        hw, hh = self.w / 2.0, self.h / 2.0
        pts = []
        for lx, ly in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
            dx, dy = self.to_world_direction(lx, ly)
            pts.append((self.cx + dx, self.cy + dy))
        return pts

    def axes(self):
        ax = (self.cos, self.sin)
        ay = (-self.sin, self.cos)
        return ax, ay


class WorldCircle:
    def __init__(self, cx, cy, r):
        self.cx, self.cy = float(cx), float(cy)
        self.r = max(0.0001, abs(float(r)))


# --------------------------------------------------------------------------- #
# Utilidades de capas
# --------------------------------------------------------------------------- #
def parse_layer_mask(value, default=None):
    if default is None:
        default = set(layers.collision_layers())
    if value is None:
        return set(default)
    if isinstance(value, str):
        names = {p.strip() for p in value.split(",") if p.strip()}
        if "*" in names or names == set(DEFAULT_LAYERS):
            return set(layers.collision_layers())
        return names or set(default)
    try:
        return {str(v) for v in value}
    except TypeError:
        return set(default)


def _layers_collide(a, b):
    return (b.layer in a.mask) and (a.layer in b.mask)


# --------------------------------------------------------------------------- #
# Cuerpos
# --------------------------------------------------------------------------- #
class Body:
    """Representación interna de un cuerpo físico asociado a un GameObject."""
    def __init__(self, game_object, world_transform, scene=None):
        self.game_object = game_object
        self.world = world_transform
        self.scene = scene
        self.world_x = float(world_transform["world_x"])
        self.world_y = float(world_transform["world_y"])
        self.rotation = float(world_transform.get("world_rotation", 0.0))
        self.scale_x = float(world_transform.get("world_scale_x", 1.0))
        self.scale_y = float(world_transform.get("world_scale_y", 1.0))

        box = game_object.get_component("BoxCollider")
        circ = game_object.get_component("CircleCollider")
        rb = game_object.get_component("RigidBody")

        self.box = None
        self.circle = None
        self.collider = None
        self.layer = "Default"
        self.mask = set(DEFAULT_LAYERS)
        self.is_trigger = False

        if box is not None and box.enabled:
            self.collider = box
            size = box.get("size")
            off = box.get("offset")
            w = float(size[0]) * abs(self.scale_x)
            h = float(size[1]) * abs(self.scale_y)
            ox, oy = self._offset_world(off)
            self.box = WorldBox(self.world_x + ox, self.world_y + oy, w, h, self.rotation)
            self.is_trigger = bool(box.get("is_trigger"))
            self.layer = str(box.get("layer", "Default"))
            self.mask = parse_layer_mask(box.get("collision_mask"))
        elif circ is not None and circ.enabled:
            self.collider = circ
            off = circ.get("offset")
            ox, oy = self._offset_world(off)
            radius = float(circ.get("radius", 50)) * max(abs(self.scale_x), abs(self.scale_y))
            self.circle = WorldCircle(self.world_x + ox, self.world_y + oy, radius)
            self.is_trigger = bool(circ.get("is_trigger"))
            self.layer = str(circ.get("layer", "Default"))
            self.mask = parse_layer_mask(circ.get("collision_mask"))

        self.rigidbody = rb if rb is not None and rb.enabled else None
        self.body_type = rb.get("body_type") if self.rigidbody is not None else "Static"
        self.mass = max(0.001, float(rb.get("mass", 1.0))) if rb is not None else 1.0
        self.gravity_scale = (float(rb.get("gravity_scale", 1.0)) if rb is not None else 0.0)
        self.linear_drag = (float(rb.get("linear_drag", 0.0)) if rb is not None else 0.0)
        self.bounciness = (float(rb.get("bounciness", 0.0)) if rb is not None else 0.0)
        self.friction = float(rb.get("friction", 0.3)) if rb is not None else 0.3

    def _offset_world(self, off):
        if not isinstance(off, (list, tuple)) or len(off) < 2:
            return 0.0, 0.0
        lx = float(off[0]) * self.scale_x
        ly = float(off[1]) * self.scale_y
        rad = math.radians(self.rotation)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        return lx * cos_a - ly * sin_a, lx * sin_a + ly * cos_a

    def is_dynamic(self):
        return self.body_type == "Dynamic"


# --------------------------------------------------------------------------- #
# Detección de colisiones
# --------------------------------------------------------------------------- #
def _obb_mtv(a, b):
    """MTV para separar `a` de `b`. Devuelve (nx, ny, depth) o None."""
    axes = list(a.axes()) + list(b.axes())
    smallest = None
    for axis in axes:
        ax, ay = axis
        ra = (a.w / 2.0) * abs(ax * a.cos + ay * a.sin) + \
             (a.h / 2.0) * abs(ax * -a.sin + ay * a.cos)
        rb = (b.w / 2.0) * abs(ax * b.cos + ay * b.sin) + \
             (b.h / 2.0) * abs(ax * -b.sin + ay * b.cos)
        dx = a.cx - b.cx
        dy = a.cy - b.cy
        dist = dx * ax + dy * ay
        overlap = ra + rb - abs(dist)
        if overlap <= 0.0:
            return None
        if smallest is None or overlap < smallest[2]:
            sign = 1.0 if dist >= 0 else -1.0
            smallest = (ax * sign, ay * sign, overlap)
    return smallest


def _circle_vs_circle(a, b):
    dx = a.cx - b.cx
    dy = a.cy - b.cy
    dist = math.hypot(dx, dy)
    if dist >= a.r + b.r:
        return None
    if dist < 1e-9:
        return (1.0, 0.0, a.r + b.r)
    overlap = a.r + b.r - dist
    return (dx / dist, dy / dist, overlap)


def _circle_vs_obb(circle, box):
    """MTV para separar el círculo de la caja: (nx, ny, depth) o None."""
    lx, ly = box.to_local(circle.cx, circle.cy)
    hw, hh = box.w / 2.0, box.h / 2.0
    cx = max(-hw, min(lx, hw))
    cy = max(-hh, min(ly, hh))
    dx = lx - cx
    dy = ly - cy
    dist_sq = dx * dx + dy * dy
    if dist_sq > circle.r * circle.r:
        return None

    if dist_sq > 1e-12:
        dist = math.sqrt(dist_sq)
        nlx, nly = dx / dist, dy / dist
        depth = circle.r - dist
    else:
        # Centro dentro de la caja: salir por la cara más cercana.
        left = lx + hw
        right = hw - lx
        top = ly + hh
        bottom = hh - ly
        m = min(left, right, top, bottom)
        if m == left:
            nlx, nly, depth = -1.0, 0.0, left + circle.r
        elif m == right:
            nlx, nly, depth = 1.0, 0.0, right + circle.r
        elif m == top:
            nlx, nly, depth = 0.0, -1.0, top + circle.r
        else:
            nlx, nly, depth = 0.0, 1.0, bottom + circle.r

    nx, ny = box.to_world_direction(nlx, nly)
    return (nx, ny, depth)


# --------------------------------------------------------------------------- #
# Raycast helpers
# --------------------------------------------------------------------------- #
def _ray_obb(ox, oy, dx, dy, box, max_dist):
    lox, loy = box.to_local(ox, oy)
    ldx, ldy = box.to_local(ox + dx, oy + dy)
    rdx, rdy = ldx - lox, ldy - loy
    hw, hh = box.w / 2.0, box.h / 2.0
    tmin, tmax = 0.0, max_dist
    normal = None

    for origin, direction, lo, hi, axis in (
        (lox, rdx, -hw, hw, "x"),
        (loy, rdy, -hh, hh, "y"),
    ):
        if abs(direction) < 1e-12:
            if origin < lo or origin > hi:
                return None
            continue
        t1 = (lo - origin) / direction
        t2 = (hi - origin) / direction
        sign = -1.0 if direction > 0 else 1.0
        if t1 > t2:
            t1, t2 = t2, t1
            sign = -sign
        if t1 > tmin:
            tmin = t1
            normal = (sign, 0.0) if axis == "x" else (0.0, sign)
        tmax = min(tmax, t2)
        if tmin > tmax:
            return None

    if normal is None:
        return None
    wx, wy = box.to_world_direction(*normal)
    return (tmin, wx, wy)


def _ray_circle(ox, oy, dx, dy, circle, max_dist):
    fx, fy = ox - circle.cx, oy - circle.cy
    b = 2.0 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - circle.r * circle.r
    disc = b * b - 4.0 * c
    if disc < 0.0:
        return None
    root = math.sqrt(disc)
    t = (-b - root) / 2.0
    if t < 0.0:
        t = (-b + root) / 2.0
    if t < 0.0 or t > max_dist:
        return None
    px, py = ox + dx * t, oy + dy * t
    nx, ny = px - circle.cx, py - circle.cy
    length = math.hypot(nx, ny) or 1.0
    return (t, nx / length, ny / length)


# --------------------------------------------------------------------------- #
# Sistema de física
# --------------------------------------------------------------------------- #
class PhysicsSystem:
    def __init__(self, scene, gravity=DEFAULT_GRAVITY):
        self.scene = scene
        self.gravity = gravity
        self._prev_collisions = set()
        self._prev_triggers = set()
        self._forces = {}          # object_id -> [fx, fy]
        self.fixed_dt = 1.0 / 60.0

    # ------------------------------------------------------------------ #
    # API para scripts
    # ------------------------------------------------------------------ #
    def add_force(self, game_object, fx, fy):
        if game_object is None: return
        queued = self._forces.setdefault(game_object.id, [0.0, 0.0])
        queued[0] += float(fx)
        queued[1] += float(fy)

    def add_impulse(self, game_object, ix, iy):
        rb = game_object.get_component("RigidBody") if game_object else None
        if rb is None: return
        mass = max(0.001, float(rb.get("mass", 1.0)))
        vx, vy = rb.get("velocity")
        rb.set("velocity", [vx + float(ix) / mass, vy + float(iy) / mass])

    def get_velocity(self, game_object):
        rb = game_object.get_component("RigidBody") if game_object else None
        if rb is None: return (0.0, 0.0)
        return tuple(rb.get("velocity"))

    def set_velocity(self, game_object, vx, vy):
        rb = game_object.get_component("RigidBody") if game_object else None
        if rb is not None: rb.set("velocity", [float(vx), float(vy)])

    def raycast(self, origin, direction, distance, layer_mask=None, ignore=None, include_triggers=False):
        """Lanza un rayo. Devuelve dict(object, point, normal, distance) o None."""
        ox, oy = float(origin[0]), float(origin[1])
        dx, dy = float(direction[0]), float(direction[1])
        length = math.hypot(dx, dy)
        if length < 1e-9: return None
        dx, dy = dx / length, dy / length
        max_dist = float(distance)
        wanted = parse_layer_mask(layer_mask) if layer_mask is not None else None
        ignore_ids = set()
        if ignore is not None:
            if hasattr(ignore, "id"): ignore_ids.add(ignore.id)
            else: ignore_ids.update(str(i) for i in ignore)

        best = None
        for body in self._collect_bodies():
            if body.game_object.id in ignore_ids: continue
            if body.is_trigger and not include_triggers: continue
            if wanted is not None and body.layer not in wanted: continue
            hit = None
            if body.box is not None: hit = _ray_obb(ox, oy, dx, dy, body.box, max_dist)
            elif body.circle is not None: hit = _ray_circle(ox, oy, dx, dy, body.circle, max_dist)
            if hit is None: continue
            t, nx, ny = hit
            if best is None or t < best[0]: best = (t, nx, ny, body)
        if best is None: return None
        t, nx, ny, body = best
        return {
            "object": body.game_object,
            "point": (ox + dx * t, oy + dy * t),
            "normal": (nx, ny),
            "distance": t,
            "collider": body.collider,
        }

    def overlap_circle(self, center, radius, layer_mask=None, ignore=None):
        cx, cy = float(center[0]), float(center[1])
        probe = WorldCircle(cx, cy, float(radius))
        wanted = parse_layer_mask(layer_mask) if layer_mask is not None else None
        ignore_ids = {getattr(ignore, "id", None)} if ignore is not None else set()
        result = []
        for body in self._collect_bodies():
            if body.game_object.id in ignore_ids: continue
            if wanted is not None and body.layer not in wanted: continue
            hit = None
            if body.circle is not None: hit = _circle_vs_circle(probe, body.circle)
            elif body.box is not None: hit = _circle_vs_obb(probe, body.box)
            if hit is not None: result.append(body.game_object)
        return result

    # ------------------------------------------------------------------ #
    # Un paso de simulación
    # ------------------------------------------------------------------ #
    def step(self, dt):
        if dt <= 0 or dt > 0.25: return
        bodies = self._collect_bodies()
        self._apply_forces(bodies, dt)
        self._apply_gravity(bodies, dt)
        self._integrate(bodies, dt)
        collisions, triggers = self._detect_collisions(bodies)
        self._resolve_collisions(collisions)
        self._dispatch_callbacks(collisions, triggers)

    # ------------------------------------------------------------------ #
    def _collect_bodies(self):
        bodies = []
        for obj in self.scene.objects:
            if not obj.active or getattr(obj, "_destroy_pending", False): continue
            if (obj.get_component("BoxCollider") is None and obj.get_component("CircleCollider") is None): continue
            bodies.append(Body(obj, self.scene.world_transform(obj), self.scene))
        return bodies

    def _apply_forces(self, bodies, dt):
        if not self._forces: return
        for body in bodies:
            force = self._forces.get(body.game_object.id)
            if force is None or not body.is_dynamic(): continue
            vx, vy = body.rigidbody.get("velocity")
            vx += (force[0] / body.mass) * dt
            vy += (force[1] / body.mass) * dt
            body.rigidbody.set("velocity", [vx, vy])
        self._forces.clear()

    def _apply_gravity(self, bodies, dt):
        for b in bodies:
            if not b.is_dynamic(): continue
            vx, vy = b.rigidbody.get("velocity")
            vx += self.gravity[0] * b.gravity_scale * dt
            vy += self.gravity[1] * b.gravity_scale * dt
            if b.linear_drag > 0:
                damp = max(0.0, 1.0 - b.linear_drag * dt)
                vx *= damp
                vy *= damp
            b.rigidbody.set("velocity", [vx, vy])

    def _integrate(self, bodies, dt):
        for b in bodies:
            if not b.is_dynamic(): continue
            vx, vy = b.rigidbody.get("velocity")
            pos = b.game_object.transform.get("position")
            b.game_object.transform.set("position", [pos[0] + vx * dt, pos[1] + vy * dt])

    def _detect_collisions(self, bodies):
        collisions = []
        triggers = []
        n = len(bodies)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = bodies[i], bodies[j]
                if not _layers_collide(a, b): continue
                hit = None
                if a.box is not None and b.box is not None: hit = _obb_mtv(a.box, b.box)
                elif a.circle is not None and b.circle is not None: hit = _circle_vs_circle(a.circle, b.circle)
                elif a.circle is not None and b.box is not None: hit = _circle_vs_obb(a.circle, b.box)
                elif a.box is not None and b.circle is not None:
                    hit = _circle_vs_obb(b.circle, a.box)
                    if hit is not None: hit = (-hit[0], -hit[1], hit[2])
                if hit is None: continue
                if a.is_trigger or b.is_trigger: triggers.append((a, b))
                else: collisions.append((a, b, hit))
        return collisions, triggers

    def _resolve_collisions(self, collisions):
        for a, b, hit in collisions:
            nx, ny, depth = hit
            if depth <= 0.0: continue
            self._separate(a, b, nx, ny, depth)
            self._bounce_and_friction(a, b, nx, ny)

    def _separate(self, a, b, nx, ny, depth):
        a_dyn, b_dyn = a.is_dynamic(), b.is_dynamic()
        if not a_dyn and not b_dyn: return
        total = a.mass + b.mass
        if a_dyn and b_dyn:
            a_share = b.mass / total
            b_share = a.mass / total
        elif a_dyn: a_share, b_share = 1.0, 0.0
        else: a_share, b_share = 0.0, 1.0

        if a_share:
            dx, dy = self.scene.world_delta_to_local(a.game_object, nx * depth * a_share, ny * depth * a_share)
            pos = a.game_object.transform.get("position")
            a.game_object.transform.set("position", [pos[0] + dx, pos[1] + dy])
        if b_share:
            dx, dy = self.scene.world_delta_to_local(b.game_object, -nx * depth * b_share, -ny * depth * b_share)
            pos = b.game_object.transform.get("position")
            b.game_object.transform.set("position", [pos[0] + dx, pos[1] + dy])

    def _bounce_and_friction(self, a, b, nx, ny):
        for body, sign in ((a, 1.0), (b, -1.0)):
            if not body.is_dynamic(): continue
            bnx, bny = nx * sign, ny * sign
            vx, vy = body.rigidbody.get("velocity")
            vn = vx * bnx + vy * bny
            tx = vx - vn * bnx
            ty = vy - vn * bny
            mu = min(1.0, (a.friction + b.friction) * 0.5)
            tx *= (1.0 - mu)
            ty *= (1.0 - mu)
            if vn < 0.0: vn = -vn * body.bounciness
            body.rigidbody.set("velocity", [tx + vn * bnx, ty + vn * bny])

    # ------------------------------------------------------------------ #
    # Callbacks a scripts
    # ------------------------------------------------------------------ #
    def _dispatch_callbacks(self, collisions, triggers):
        current_coll = set()
        for a, b, _hit in collisions:
            current_coll.add(tuple(sorted([a.game_object.id, b.game_object.id])))
        current_trig = set()
        for a, b in triggers:
            current_trig.add(tuple(sorted([a.game_object.id, b.game_object.id])))

        self._dispatch_set(collisions, current_coll, self._prev_collisions, "on_collision")
        self._dispatch_set(triggers, current_trig, self._prev_triggers, "on_trigger")

        self._prev_collisions = current_coll
        self._prev_triggers = current_trig

    def _dispatch_set(self, pairs, current, previous, prefix):
        entered = current - previous
        stayed = current & previous
        exited = previous - current

        for pair in pairs:
            a, b = pair[0], pair[1]
            key = tuple(sorted([a.game_object.id, b.game_object.id]))
            if key in entered:
                self._call_script(a, f"{prefix}_enter", b)
                self._call_script(b, f"{prefix}_enter", a)
            elif key in stayed:
                self._call_script(a, f"{prefix}_stay", b)
                self._call_script(b, f"{prefix}_stay", a)

        for key in exited:
            a = self.scene.find(key[0])
            b = self.scene.find(key[1])
            if a is not None and b is not None:
                self._call_script_by_obj(a, f"{prefix}_exit", b)
                self._call_script_by_obj(b, f"{prefix}_exit", a)

    def _call_script(self, body, method_name, other_body):
        self._call_script_by_obj(body.game_object, method_name, other_body.game_object)

    def _call_script_by_obj(self, obj, method_name, other_obj):
        for comp in obj.get_components("Script"):
            inst = getattr(comp, "_instance", None)
            if inst is None: continue
            method = getattr(inst, method_name, None)
            if method is None: continue
            try: method(other_obj)
            except Exception as e: print(f"[Physics] Error en {method_name} de {obj.name}: {e}")