"""Sistema de cámara 2D compartido por editor y runtime.

Selecciona la cámara activa por prioridad, aplica seguimiento suave de
objetivos y transiciones entre cámaras.
"""
import math
from uron.core.util import parse_color, format_color

DEFAULT_ORTHO = 360.0
DEFAULT_BG = (27, 30, 38, 255)


def camera_component(obj):
    """Devuelve el componente Camera activo de un GameObject, o None."""
    if obj is None or not getattr(obj, "active", True):
        return None
    comp = obj.get_component("Camera")
    if comp is None or not comp.enabled:
        return None
    return comp


def find_active_camera(scene):
    """Cámara activa de mayor prioridad (o la primera)."""
    best = None
    best_priority = None
    for obj in scene.objects:
        comp = camera_component(obj)
        if comp is None:
            continue
        priority = int(comp.get("priority", 0))
        if best is None or priority > best_priority:
            best = obj
            best_priority = priority
    return best


def read_camera(scene, camera_obj=None):
    """Lee la cámara activa y devuelve un dict normalizado."""
    if camera_obj is None:
        camera_obj = find_active_camera(scene)
        
    if camera_obj is None or camera_component(camera_obj) is None:
        return {
            "object": None,
            "x": 0.0, "y": 0.0,
            "ortho_size": DEFAULT_ORTHO,
            "rotation": 0.0,
            "background": DEFAULT_BG,
            "priority": 0,
            "follow_target": "",
            "follow_lerp": 0.0,
            "transition_duration": 0.0,
            "viewport_width": 1100,
            "viewport_height": 700,
        }
        
    comp = camera_component(camera_obj)
    world = scene.world_transform(camera_obj)
    
    return {
        "object": camera_obj,
        "x": float(world["world_x"]),
        "y": float(world["world_y"]),
        "ortho_size": max(0.001, float(comp.get("orthographic_size", DEFAULT_ORTHO))),
        "rotation": float(world["world_rotation"]),
        "background": parse_color(comp.get("background"), DEFAULT_BG),
        "priority": int(comp.get("priority", 0)),
        "follow_target": str(comp.get("follow_target", "")),
        "follow_lerp": max(0.0, min(1.0, float(comp.get("follow_lerp", 0.0)))),
        "transition_duration": max(0.0, float(comp.get("transition_duration", 0.0))),
        "viewport_width": max(1, int(comp.get("viewport_width", 1100))),
        "viewport_height": max(1, int(comp.get("viewport_height", 700))),
    }


def camera_frame(scene, fallback_aspect=1100 / 700):
    """Rectángulo visible de la cámara activa para dibujar en el editor.

    Devuelve dict con x, y, width, height, rotation, background, ortho_size,
    viewport_width/height y object.
    """
    info = read_camera(scene)
    vw, vh = info["viewport_width"], info["viewport_height"]
    aspect = vw / vh if vh else fallback_aspect
    half_h = info["ortho_size"]
    half_w = half_h * aspect
    info.update({
        "width": half_w * 2.0,
        "height": half_h * 2.0,
        "aspect": aspect,
    })
    return info


class CameraSystem:
    """Estado de cámara por frame para el runtime."""

    def __init__(self, scene):
        self.scene = scene
        self.x = 0.0
        self.y = 0.0
        self.ortho_size = DEFAULT_ORTHO
        self.rotation = 0.0
        self.background = DEFAULT_BG
        self.viewport_width = 1100
        self.viewport_height = 700
        self.object_id = None
        self._target_id = None
        self._follow_positions = {}
        self._transition = None
        self._forced_target = None
        self._forced_until_change = False
        self.update(0.0, force=True)

    # ------------------------------------------------------------------ #
    # API de scripts
    # ------------------------------------------------------------------ #
    def set_ortho_size(self, value):
        value = max(0.001, float(value))
        self.ortho_size = value
        cam_obj = self.current_object()
        comp = cam_obj.get_component("Camera") if cam_obj is not None else None
        if comp is not None:
            comp.set("orthographic_size", value)

    def set_background(self, value):
        self.background = parse_color(value, self.background)
        cam_obj = self.current_object()
        comp = cam_obj.get_component("Camera") if cam_obj is not None else None
        if comp is not None:
            comp.set("background", format_color(*self.background))

    def set_position(self, x, y):
        x, y = float(x), float(y)
        self.x, self.y = x, y
        cam_obj = self.current_object()
        if cam_obj is not None:
            local = self.scene.world_to_local_point(cam_obj, x, y)
            cam_obj.transform.set("position", local)

    def follow(self, target, lerp=0.1):
        """Fija un objetivo de seguimiento (nombre/id/GameObject) para la cámara actual."""
        cam_obj = self.current_object()
        if cam_obj is None: return
        comp = cam_obj.get_component("Camera")
        if comp is None: return
        target_name = ""
        if target is not None:
            target_name = getattr(target, "name", str(target))
        comp.set("follow_target", target_name)
        comp.set("follow_lerp", float(lerp))

    def transition_to(self, camera, duration=0.5):
        """Transiciona a otra cámara (objeto, id o nombre)."""
        target = camera
        if isinstance(camera, str):
            target = self.scene.find(camera) or self.scene.find_by_name(camera)
        if target is None: return
        self._forced_target = target
        self._forced_until_change = True
        self._begin_transition(target, max(0.0, float(duration)))

    def current_object(self):
        return self.scene.find(self.object_id) if self.object_id else None

    # ------------------------------------------------------------------ #
    # Actualización
    # ------------------------------------------------------------------ #
    def update(self, dt, force=False):
        target_obj = self._forced_target or find_active_camera(self.scene)
        info = read_camera(self.scene, target_obj)
        target_id = info["object"].id if info["object"] is not None else None

        desired = self._desired_state(info, dt)
        if force or self._transition is None and self.object_id is None:
            self._apply_state(desired)
            self.object_id = target_id
            self._target_id = target_id
            return

        if target_id != self._target_id and self._transition is None:
            duration = info["transition_duration"]
            self._begin_transition(info["object"], duration)
            self.object_id = target_id
            self._target_id = target_id

        if self._transition is not None:
            tr = self._transition
            tr["elapsed"] += max(0.0, float(dt))
            t = 1.0 if tr["duration"] <= 0 else min(1.0, tr["elapsed"] / tr["duration"])
            t = t * t * (3.0 - 2.0 * t)  # smoothstep
            start = tr["from"]
            self.x = start[0] + (desired["x"] - start[0]) * t
            self.y = start[1] + (desired["y"] - start[1]) * t
            self.ortho_size = start[2] + (desired["ortho_size"] - start[2]) * t
            self.rotation = start[3] + (desired["rotation"] - start[3]) * t
            self.background = tuple(
                int(start[4][i] + (desired["background"][i] - start[4][i]) * t)
                for i in range(4))
            self.viewport_width = desired["viewport_width"]
            self.viewport_height = desired["viewport_height"]
            if t >= 1.0:
                self._transition = None
        else:
            self.x = desired["x"]
            self.y = desired["y"]
            self.ortho_size = desired["ortho_size"]
            self.rotation = desired["rotation"]
            self.background = desired["background"]
            self.viewport_width = desired["viewport_width"]
            self.viewport_height = desired["viewport_height"]

    def _desired_state(self, info, dt):
        x, y = info["x"], info["y"]
        follow = info["follow_target"].strip()
        if follow:
            target = (self.scene.find(follow) or self.scene.find_by_name(follow))
            if target is not None:
                world = self.scene.world_transform(target)
                key = info["object"].id if info["object"] is not None else "default"
                lerp = info["follow_lerp"]
                if lerp <= 0.0:
                    self._follow_positions[key] = (world["world_x"], world["world_y"])
                else:
                    prev = self._follow_positions.get(key, (self.x, self.y))
                    factor = min(1.0, lerp * max(1.0, float(dt) * 60.0))
                    self._follow_positions[key] = (
                        prev[0] + (world["world_x"] - prev[0]) * factor,
                        prev[1] + (world["world_y"] - prev[1]) * factor,
                    )
                x, y = self._follow_positions[key]
        return {
            "x": x, "y": y,
            "ortho_size": info["ortho_size"],
            "rotation": info["rotation"],
            "background": info["background"],
            "viewport_width": info["viewport_width"],
            "viewport_height": info["viewport_height"],
        }

    def _begin_transition(self, target_obj, duration):
        if target_obj is None:
            self._transition = None
            return
        info = read_camera(self.scene, target_obj)
        desired = self._desired_state(info, 0.0)
        self._transition = {
            "from": (self.x, self.y, self.ortho_size,
                     self.rotation, self.background),
            "duration": max(0.0, float(duration)),
            "elapsed": 0.0,
        }
        self._target_id = info["object"].id if info["object"] is not None else None
        self._forced_until_change = False

    def _apply_state(self, state):
        self.x = state["x"]
        self.y = state["y"]
        self.ortho_size = state["ortho_size"]
        self.rotation = state["rotation"]
        self.background = state["background"]
        self.viewport_width = state["viewport_width"]
        self.viewport_height = state["viewport_height"]

    def frame_size(self, viewport_width, viewport_height):
        aspect = viewport_width / max(1, viewport_height)
        return self.ortho_size * aspect * 2.0, self.ortho_size * 2.0

    def world_to_screen(self, x, y, viewport_width, viewport_height):
        aspect = viewport_width / max(1, viewport_height)
        half_w = self.ortho_size * aspect
        half_h = self.ortho_size
        dx, dy = float(x) - self.x, float(y) - self.y
        rad = math.radians(-self.rotation)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        rx = dx * cos_a - dy * sin_a
        ry = dx * sin_a + dy * cos_a
        sx = (rx / (2.0 * half_w) + 0.5) * viewport_width
        sy = (ry / (2.0 * half_h) + 0.5) * viewport_height
        return sx, sy