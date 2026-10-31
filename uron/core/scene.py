"""Modelo de escena de URON: GameObjects y Scene (sin dependencias externas)."""
import copy
import json
import os
import uuid
from .components import Component, Transform
from .version import SCENE_FORMAT_VERSION

def migrate_scene_data(data):
    if not isinstance(data, dict):
        raise ValueError("Scene.from_dict espera un dict")
    migrated = copy.deepcopy(data)
    version = int(migrated.get("format_version", 1) or 1)
    if version < 2:
        objects = migrated.get("objects")
        if not isinstance(objects, list):
            migrated["objects"] = []
        for obj in migrated["objects"]:
            if not isinstance(obj, dict): continue
            if not isinstance(obj.get("components"), list): obj["components"] = []
            if obj.get("parent_id") == "": obj["parent_id"] = None
    migrated["format_version"] = SCENE_FORMAT_VERSION
    return migrated

class GameObject:
    def __init__(self, name="GameObject", object_id=None, parent_id=None):
        self.id = object_id or str(uuid.uuid4())
        self.name = name
        self.active = True
        self.parent_id = parent_id
        self.components = []
        self._destroy_pending = False
        self.add_component(Transform())

    def add_component(self, component):
        if component.unique:
            for existing in self.components:
                if existing.type_name == component.type_name:
                    return existing
        self.components.append(component)
        return component

    def get_component(self, type_name):
        for c in self.components:
            if c.type_name == type_name: return c
        return None

    def get_components(self, type_name):
        return [c for c in self.components if c.type_name == type_name]

    def has_component(self, type_name):
        return self.get_component(type_name) is not None

    def remove_component(self, type_name):
        for c in list(self.components):
            if c.type_name == type_name and c.removable:
                self.components.remove(c)
                return True
        return False

    def remove_component_instance(self, component):
        if component in self.components and component.removable:
            self.components.remove(component)
            return True
        return False

    @property
    def transform(self):
        return self.get_component("Transform")

    def start(self):
        for c in self.components:
            if c.enabled: c.start(self)

    def update(self, dt):
        for c in self.components:
            if c.enabled: c.update(self, dt)

    def destroy(self):
        self._destroy_pending = True

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "active": self.active,
            "parent_id": self.parent_id,
            "components": [c.to_dict() for c in self.components],
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(name=data.get("name", "GameObject"), object_id=data.get("id"), parent_id=data.get("parent_id"))
        obj.active = bool(data.get("active", True))
        obj.components = []
        for comp_data in data.get("components", []):
            if isinstance(comp_data, dict):
                obj.components.append(Component.from_dict(comp_data))
        if obj.get_component("Transform") is None: obj.add_component(Transform())
        return obj

    def clone(self, new_name=None):
        data = self.to_dict()
        data["id"] = str(uuid.uuid4())
        if new_name is not None: data["name"] = new_name
        return GameObject.from_dict(data)


class Scene:
    def __init__(self, name="Main Scene"):
        self.name = name
        self.objects = []
        self.project_folder = None

    def children_of(self, parent_id):
        return [o for o in self.objects if o.parent_id == parent_id]

    def get_root_objects(self):
        return [o for o in self.objects if o.parent_id is None]

    def is_ancestor(self, ancestor_id, node_id):
        cur = self.find(node_id)
        seen = set()
        while cur is not None and cur.parent_id is not None:
            if cur.parent_id == ancestor_id: return True
            if cur.parent_id in seen: break
            seen.add(cur.parent_id)
            cur = self.find(cur.parent_id)
        return False

    def reparent(self, child_id, new_parent_id):
        if child_id == new_parent_id: return False
        if new_parent_id is not None and self.is_ancestor(child_id, new_parent_id): return False
        child = self.find(child_id)
        if child is None: return False
        child.parent_id = new_parent_id
        return True

    def world_transform(self, obj):
        if obj is None or obj.transform is None:
            return {"world_x": 0, "world_y": 0, "world_rotation": 0, "world_scale_x": 1, "world_scale_y": 1}
        tr = obj.transform
        x, y = tr.get("position")
        rot = tr.get("rotation")
        sx, sy = tr.get("scale")
        chain = []
        cur = obj
        seen = set()
        while cur is not None and cur.parent_id is not None:
            if cur.id in seen: break
            seen.add(cur.id)
            parent = self.find(cur.parent_id)
            if parent is None: break
            chain.append(parent)
            cur = parent

        wx, wy = float(x), float(y)
        wrot = float(rot)
        wsx, wsy = float(sx), float(sy)
        import math as _m
        for parent in reversed(chain):
            ptr = parent.transform
            if ptr is None: continue
            px, py = ptr.get("position")
            prot = ptr.get("rotation")
            psx, psy = ptr.get("scale")
            rad = _m.radians(prot)
            cos_a, sin_a = _m.cos(rad), _m.sin(rad)
            wx *= psx; wy *= psy
            rx = wx * cos_a - wy * sin_a
            ry = wx * sin_a + wy * cos_a
            wx = rx + float(px); wy = ry + float(py)
            wrot += float(prot)
            wsx *= float(psx); wsy *= float(psy)
        return {"world_x": wx, "world_y": wy, "world_rotation": wrot, "world_scale_x": wsx, "world_scale_y": wsy}

    def parent_world_transform(self, obj):
        if obj is None or obj.parent_id is None:
            return {"world_x": 0.0, "world_y": 0.0, "world_rotation": 0.0, "world_scale_x": 1.0, "world_scale_y": 1.0}
        parent = self.find(obj.parent_id)
        if parent is None:
            return {"world_x": 0.0, "world_y": 0.0, "world_rotation": 0.0, "world_scale_x": 1.0, "world_scale_y": 1.0}
        return self.world_transform(parent)

    def world_to_local_point(self, obj, wx, wy):
        pw = self.parent_world_transform(obj)
        import math as _m
        dx = float(wx) - float(pw["world_x"]); dy = float(wy) - float(pw["world_y"])
        rad = _m.radians(-float(pw["world_rotation"]))
        cos_a, sin_a = _m.cos(rad), _m.sin(rad)
        rx = dx * cos_a - dy * sin_a; ry = dx * sin_a + dy * cos_a
        sx = float(pw["world_scale_x"]) or 1.0; sy = float(pw["world_scale_y"]) or 1.0
        return [rx / sx, ry / sy]

    def create_object(self, name="GameObject"):
        obj = GameObject(name=name)
        self.objects.append(obj)
        return obj

    def add_object(self, game_object):
        if any(o.id == game_object.id for o in self.objects): game_object.id = str(uuid.uuid4())
        self.objects.append(game_object)
        return game_object

    def remove_object(self, object_id, cascade=True):
        targets = {object_id}
        if cascade:
            for d in self.descendants(object_id): targets.add(d.id)
        first_removed = None
        new_objects = []
        for o in self.objects:
            if o.id in targets:
                if o.id == object_id: first_removed = o
            else: new_objects.append(o)
        self.objects = new_objects
        return first_removed

    def find(self, object_id):
        return next((o for o in self.objects if o.id == object_id), None)

    def find_by_name(self, name):
        return next((o for o in self.objects if o.name == name), None)

    def descendants(self, parent_id):
        result = []
        stack = list(self.children_of(parent_id))
        while stack:
            node = stack.pop()
            result.append(node)
            stack.extend(self.children_of(node.id))
        return result

    def clear(self):
        self.objects = []

    def start(self):
        for o in self.objects:
            if o.active: o.start()

    def update(self, dt):
        for o in self.objects:
            if o.active: o.update(dt)
        self.flush_destroyed()

    def flush_destroyed(self):
        doomed = [o for o in self.objects if getattr(o, "_destroy_pending", False)]
        if not doomed: return 0
        for o in doomed:
            for comp in list(o.components):
                try: comp.destroy(o)
                except Exception: pass
        doomed_ids = {o.id for o in doomed}
        self.objects = [o for o in self.objects if o.id not in doomed_ids]
        return len(doomed)

    def to_dict(self):
        return {"format_version": SCENE_FORMAT_VERSION, "name": self.name, "objects": [o.to_dict() for o in self.objects]}

    @classmethod
    def from_dict(cls, data):
        data = migrate_scene_data(data)
        scene = cls(name=data.get("name", "Main Scene"))
        for obj_data in data.get("objects", []):
            if isinstance(obj_data, dict): scene.objects.append(GameObject.from_dict(obj_data))
        return scene

    def make_portable(self, project_folder):
        root = os.path.abspath(project_folder)
        for obj in self.objects:
            for comp in obj.components:
                if comp.type_name == "SpriteRenderer":
                    value = comp.get("image", "")
                    if value and os.path.isabs(value):
                        try:
                            rel = os.path.relpath(value, root)
                        except ValueError:
                            continue
                        # Si la ruta no empieza con ".." (no se sale de la carpeta), la hacemos relativa
                        if not rel.startswith(".."):
                            comp.set("image", rel.replace(os.sep, "/"))
        return self

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))