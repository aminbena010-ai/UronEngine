"""Lista global de proyectos recientes (~/.config/URON/recent_projects.json)."""
import json
import os
import sys

def _config_dir():
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "URON")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/URON")
    return os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "URON")

def _path():
    return os.path.join(_config_dir(), "recent_projects.json")

def load():
    try:
        with open(_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [p for p in data if isinstance(p, str) and os.path.isdir(p)]
    except (OSError, json.JSONDecodeError):
        pass
    return []

def push(folder):
    folder = os.path.abspath(folder)
    lst = [p for p in load() if p != folder]
    lst.insert(0, folder)
    os.makedirs(_config_dir(), exist_ok=True)
    with open(_path(), "w", encoding="utf-8") as f:
        json.dump(lst[:10], f, indent=2, ensure_ascii=False)