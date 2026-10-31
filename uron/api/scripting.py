"""Sistema de scripts y clase base UronScript."""
import importlib.util
import json
import os
import sys
import traceback

from uron.core.components import Component, Field, register_component
from uron.core.physics import PhysicsSystem  # Para tipado
from uron.render.camera import CameraSystem

from .input import Input
from .audio import Audio
from .draw import draw
from .time import Time, Wait
from .components import (
    ColliderAPI, RigidBodyAPI, SpriteRendererAPI, TextRendererAPI,
)
from .layers import Layers


class _PhysicsAPI:
    _system = None
    @classmethod
    def configure(cls, system): cls._system = system
    @classmethod
    def velocity(cls, game_object):
        return cls._system.get_velocity(game_object) if cls._system else (0.0, 0.0)
    @classmethod
    def set_velocity(cls, game_object, vx, vy):
        if cls._system: cls._system.set_velocity(game_object, vx, vy)
    @classmethod
    def add_force(cls, game_object, fx, fy):
        if cls._system: cls._system.add_force(game_object, fx, fy)
    @classmethod
    def add_impulse(cls, game_object, ix, iy):
        if cls._system: cls._system.add_impulse(game_object, ix, iy)
    @classmethod
    def raycast(cls, origin, direction, distance, layer_mask=None, ignore=None, include_triggers=False):
        if not cls._system: return None
        return cls._system.raycast(origin, direction, distance, layer_mask, ignore, include_triggers)
    @classmethod
    def overlap_circle(cls, center, radius, layer_mask=None, ignore=None):
        return cls._system.overlap_circle(center, radius, layer_mask, ignore) if cls._system else []

Physics = _PhysicsAPI()


class _CameraAPI:
    _system = None
    @classmethod
    def configure(cls, system): cls._system = system
    @classmethod
    def main(cls): return cls._system
    @classmethod
    def set_ortho_size(cls, value):
        if cls._system: cls._system.set_ortho_size(value)
    @classmethod
    def set_position(cls, x, y):
        if cls._system: cls._system.set_position(x, y)
    @classmethod
    def set_background(cls, color):
        if cls._system: cls._system.set_background(color)
    @classmethod
    def follow(cls, target, lerp=0.1):
        if cls._system: cls._system.follow(target, lerp)
    @classmethod
    def transition_to(cls, camera, duration=0.5):
        if cls._system: cls._system.transition_to(camera, duration)

Camera = _CameraAPI()


# --- La clase que heredarán los scripts del usuario ---
class UronScript:
    game_object = None
    scene = None
    transform = None
    physics = Physics
    camera = Camera
    input = Input
    draw = draw
    audio = Audio
    time = Time
    sprite = None
    text = None
    rigidbody = None
    collider = None
    layers = Layers

    def get_component(self, component_type):
        if self.game_object is None:
            raise RuntimeError("Script is not attached to a GameObject")
        return self.game_object.get_component(component_type)

    def start(self): pass
    def update(self, dt): pass
    def on_destroy(self): pass


# --- Componente que enlaza la escena con el script ---
@register_component
class ScriptComponent(Component):
    type_name = "Script"
    unique = False
    fields = (
        Field("path", "string", "", "Script path"),
        Field("class_name", "string", "", "Class"),
        Field("properties_json", "string", "{}", "Properties (JSON)"),
    )

    _instance = None
    _loaded_class = None
    _coroutine = None
    _wait = 0.0
    _mtime = 0.0

    def instantiate(self, game_object, scene, project_folder):
        path_rel = self.get("path", "")
        class_name = self.get("class_name", "")
        if not path_rel or not class_name: return None
        
        script_path = os.path.join(project_folder, path_rel)
        cls = ScriptLoader.load_class(script_path, class_name)
        if cls is None: return None
        
        try: self._mtime = os.path.getmtime(script_path)
        except OSError: self._mtime = 0.0
        
        try:
            instance = cls()
        except Exception:
            traceback.print_exc()
            return None
            
        # Inyectar dependencias
        instance.game_object = game_object
        instance.scene = scene  # API de escena
        instance.transform = game_object.transform
        instance.physics = Physics
        instance.camera = Camera
        instance.input = Input
        instance.draw = draw
        instance.audio = Audio
        instance.time = Time
        instance.sprite = SpriteRendererAPI(game_object)
        instance.text = TextRendererAPI(game_object)
        instance.rigidbody = RigidBodyAPI(game_object, Physics)
        instance.collider = ColliderAPI(game_object)
        instance.layers = Layers
        
        # Inyectar variables de usuario
        try: props = json.loads(self.get("properties_json", "{}"))
        except Exception: props = {}
        for k, v in props.items():
            try: setattr(instance, k, v)
            except Exception: pass
            
        self._instance = instance
        self._coroutine = None
        self._wait = 0.0
        return instance

    def start(self, game_object):
        if self._instance is not None:
            try: self._instance.start()
            except Exception: traceback.print_exc()

    def update(self, game_object, dt):
        if self._instance is None: return
        try:
            result = self._instance.update(dt)
            if result is not None and hasattr(result, "__next__"):
                self._coroutine = result
                self._start_coroutine()
            elif self._coroutine is not None:
                self._advance_coroutine(dt)
        except Exception: traceback.print_exc()

    def _start_coroutine(self):
        if self._coroutine is None: return
        try:
            value = next(self._coroutine)
            self._wait = Time._wait_seconds(value)
        except StopIteration:
            self._coroutine = None

    def _advance_coroutine(self, dt):
        if self._coroutine is None: return
        self._wait -= max(0.0, float(dt))
        steps = 0
        while self._coroutine is not None and self._wait <= 0.0 and steps < 64:
            steps += 1
            try:
                value = next(self._coroutine)
                self._wait = Time._wait_seconds(value)
            except StopIteration:
                self._coroutine = None
                self._wait = 0.0

    def destroy(self, game_object):
        if self._instance is not None:
            try: self._instance.on_destroy()
            except Exception: traceback.print_exc()
        if self._coroutine is not None:
            try: self._coroutine.close()
            except Exception: pass
        self._coroutine = None
        self._instance = None


class ScriptLoader:
    @staticmethod
    def list_scripts(project_folder):
        d = os.path.join(project_folder, "scripts")
        if not os.path.isdir(d): return []
        return sorted(f for f in os.listdir(d) if f.endswith(".py") and not f.startswith("_"))

    @staticmethod
    def load_class(script_path, class_name):
        if not os.path.isfile(script_path): return None
        module_name = "uron_user_scripts." + os.path.splitext(os.path.basename(script_path))[0]
        try:
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except Exception:
            traceback.print_exc()
            return None
        cls = getattr(module, class_name, None)
        if cls is None: print(f"[ScriptLoader] {script_path} no define '{class_name}'")
        return cls

    @staticmethod
    def discover_exposed_properties(cls):
        result = {}
        if cls is None: return result
        reserved = {"start", "update", "on_destroy", "game_object", "scene",
                    "transform", "physics", "camera", "input", "draw",
                    "audio", "time", "sprite", "text", "rigidbody", "collider",
                    "layers", "get_component"}
        for name in dir(cls):
            if name.startswith("_") or name in reserved: continue
            try: value = getattr(cls, name)
            except Exception: continue
            if isinstance(value, bool): result[name] = ("bool", value)
            elif isinstance(value, int): result[name] = ("int", value)
            elif isinstance(value, float): result[name] = ("float", value)
            elif isinstance(value, str): result[name] = ("string", value)
        return result

def reload_changed_scripts(scene, project_folder):
    """Recarga scripts cuyo archivo cambió en disco (hot-reload)."""
    reloaded = 0
    for obj in scene.objects:
        for comp in obj.get_components("Script"):
            path_rel = comp.get("path", "")
            if not path_rel:
                continue
            full = os.path.join(project_folder, path_rel)
            try:
                mtime = os.path.getmtime(full)
            except OSError:
                continue
            if mtime > getattr(comp, "_mtime", 0.0) + 1e-6:
                if comp.reload(project_folder):
                    reloaded += 1
    return reloaded
