"""Modelo de proyecto URON (project.uron + .uron/ interno oculto)."""
import json
import os
import shutil
import sys
import time
import uuid
from .version import ENGINE_VERSION, PROJECT_FORMAT_VERSION

ANCHOR_NAME = "project.uron"
INTERNAL_DIRNAME = ".uron"
ANCHOR_VERSION = PROJECT_FORMAT_VERSION

DEFAULT_SETTINGS = {"window": {"width": 1100, "height": 700, "resizable": True}, "runtime": {"target_fps": 60}}
DEFAULT_EDITOR_CFG = {"grid": {"size": 32, "visible": True}, "zoom": 1.0, "theme": "dark", "snap": {"enabled": False, "size": 32}, "window": {"width": 1440, "height": 900}}
DEFAULT_KEYBINDS = {"select": "Q", "move": "W", "rotate": "E", "scale": "R", "play": "F5", "save": "Ctrl+S", "open": "Ctrl+O"}

def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _read_json(path, default=None):
    if not os.path.isfile(path): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except (OSError, json.JSONDecodeError): return default

class NotAProjectError(ValueError): pass

class UronProject:
    def __init__(self, folder, data):
        self.folder = os.path.abspath(folder)
        self.data = data

    @property
    def anchor_path(self): return os.path.join(self.folder, ANCHOR_NAME)
    @property
    def name(self): return self.data.get("name", os.path.basename(self.folder))
    @property
    def id(self): return self.data.get("id", "")

    @classmethod
    def create(cls, base_dir, name):
        base_dir = os.path.abspath(base_dir)
        folder = os.path.join(base_dir, name)
        if os.path.exists(folder): raise FileExistsError(f"Ya existe la carpeta: {folder}")
        os.makedirs(folder, exist_ok=True)
        data = {
            "uron_project_version": ANCHOR_VERSION, "engine_version": ENGINE_VERSION,
            "id": str(uuid.uuid4()), "name": name,
            "main_scene": "scenes/main.uron.json",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        proj = cls(folder, data)
        os.makedirs(proj.scenes_dir(), exist_ok=True)
        for sub in ("sprites", "audio", "fonts"): os.makedirs(os.path.join(proj.assets_dir(), sub), exist_ok=True)
        os.makedirs(proj.scripts_dir(), exist_ok=True)
        _write_json(proj.scene_path("main.uron.json"), {"name": "Main Scene", "objects": []})
        proj.save_anchor()
        proj.internal_ensure()
        return proj

    @classmethod
    def open(cls, folder_or_anchor):
        path = os.path.abspath(folder_or_anchor)
        if os.path.isfile(path):
            if os.path.basename(path) != ANCHOR_NAME: raise NotAProjectError(f"No es un project.uron: {path}")
            folder = os.path.dirname(path)
        elif os.path.isdir(path): folder = path
        else: raise FileNotFoundError(f"No existe: {path}")
        
        anchor = os.path.join(folder, ANCHOR_NAME)
        if not os.path.isfile(anchor): raise NotAProjectError(f"Esta carpeta no es un proyecto URON (falta {ANCHOR_NAME}):\n{folder}")
        data = _read_json(anchor)
        if not isinstance(data, dict): raise NotAProjectError(f"project.uron inválido: {anchor}")
        
        proj = cls(folder, data)
        proj.internal_ensure()
        return proj

    def save_anchor(self): _write_json(self.anchor_path, self.data)
    def internal_dir(self): return os.path.join(self.folder, INTERNAL_DIRNAME)
    def internal_ensure(self):
        os.makedirs(self.internal_dir(), exist_ok=True)
        os.makedirs(self.cfg_dir(), exist_ok=True)
        os.makedirs(self.cache_dir(), exist_ok=True)
        os.makedirs(self.logs_dir(), exist_ok=True)
        os.makedirs(self.prefabs_dir(), exist_ok=True)
        if not os.path.isfile(self.settings_path()): _write_json(self.settings_path(), DEFAULT_SETTINGS)
        if not os.path.isfile(os.path.join(self.cfg_dir(), "editor.cfg")): _write_json(os.path.join(self.cfg_dir(), "editor.cfg"), DEFAULT_EDITOR_CFG)
        if not os.path.isfile(os.path.join(self.cfg_dir(), "keybinds.cfg")): _write_json(os.path.join(self.cfg_dir(), "keybinds.cfg"), DEFAULT_KEYBINDS)

    def cfg_dir(self): return os.path.join(self.internal_dir(), ".cfg")
    def cache_dir(self): return os.path.join(self.internal_dir(), "cache")
    def logs_dir(self): return os.path.join(self.internal_dir(), "logs")
    def settings_path(self): return os.path.join(self.internal_dir(), "settings.json")
    def scenes_dir(self): return os.path.join(self.folder, "scenes")
    def scripts_dir(self): return os.path.join(self.folder, "scripts")
    def assets_dir(self): return os.path.join(self.folder, "assets")
    def sprites_dir(self): return os.path.join(self.assets_dir(), "sprites")
    def prefabs_dir(self): return os.path.join(self.assets_dir(), "prefabs")

    def list_scripts(self):
        d = self.scripts_dir()
        return sorted(f for f in os.listdir(d) if f.endswith(".py")) if os.path.isdir(d) else []

    def list_scenes(self):
        d = self.scenes_dir()
        return sorted(f for f in os.listdir(d) if f.endswith(".uron.json")) if os.path.isdir(d) else []

    def scene_path(self, name):
        if not name.endswith(".uron.json"): name = name + ".uron.json"
        return os.path.join(self.scenes_dir(), name)

    def create_scene(self, name):
        path = self.scene_path(name)
        if os.path.isfile(path): raise FileExistsError(f"Ya existe: {path}")
        _write_json(path, {"name": name.rsplit(".uron.json", 1)[0], "objects": []})
        return path

    def main_scene_path(self): return os.path.join(self.folder, self.data.get("main_scene", "scenes/main.uron.json"))


    def load_settings(self):
        data = _read_json(self.settings_path(), DEFAULT_SETTINGS)
        base = json.loads(json.dumps(DEFAULT_SETTINGS))
        for section, values in (data or {}).items():
            if isinstance(values, dict) and isinstance(base.get(section), dict):
                base[section].update(values)
            else:
                base[section] = values
        return base

    def save_settings(self, settings):
        _write_json(self.settings_path(), settings)

    def load_editor_cfg(self):
        return _read_json(os.path.join(self.cfg_dir(), "editor.cfg"), DEFAULT_EDITOR_CFG)

    def save_editor_cfg(self, cfg):
        _write_json(os.path.join(self.cfg_dir(), "editor.cfg"), cfg)

    def load_keybinds(self):
        data = _read_json(os.path.join(self.cfg_dir(), "keybinds.cfg"), DEFAULT_KEYBINDS)
        result = dict(DEFAULT_KEYBINDS)
        if isinstance(data, dict):
            result.update({k: str(v) for k, v in data.items()})
        return result

    def import_asset(self, source_path, kind="sprites"):
        dest_dir = self.sprites_dir() if kind == "sprites" else os.path.join(self.assets_dir(), kind)
        os.makedirs(dest_dir, exist_ok=True)
        base = os.path.basename(source_path)
        dest = os.path.join(dest_dir, base)
        stem, ext = os.path.splitext(base)
        n = 1
        while os.path.isfile(dest):
            dest = os.path.join(dest_dir, f"{stem}_{n}{ext}")
            n += 1
        shutil.copy2(source_path, dest)
        return os.path.relpath(dest, self.folder).replace(os.sep, "/")