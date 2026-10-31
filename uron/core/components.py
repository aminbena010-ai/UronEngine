"""Sistema de componentes de URON.

Cada componente declara un *esquema* (`fields`). Con ese esquema:
  * el editor genera el Inspector automáticamente,
  * la (de)serialización valida y normaliza los datos,
  * el runtime sabe qué propiedades existen.
"""
import copy
import math
from dataclasses import dataclass
from typing import Any
from .util import normalize_color

@dataclass(frozen=True)
class Field:
    name: str
    kind: str                 # float | int | bool | string | color | vec2 | image | enum
    default: Any
    label: str = ""
    minimum: float = -1e6
    maximum: float = 1e6
    step: float = 1.0
    choices: tuple = ()

    @property
    def title(self):
        return self.label or self.name.replace("_", " ").title()

COMPONENT_REGISTRY = {}

def register_component(cls):
    COMPONENT_REGISTRY[cls.type_name] = cls
    return cls

def _num(value, field):
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("no finito")
    return max(field.minimum, min(field.maximum, v))

def coerce(field, value):
    k = field.kind
    try:
        if k == "float": return _num(value, field)
        if k == "int": return int(round(_num(value, field)))
        if k == "bool": return bool(value)
        if k in ("string", "image"): return "" if value is None else str(value)
        if k == "color": return normalize_color(value, field.default)
        if k == "vec2":
            x, y = value
            return [_num(x, field), _num(y, field)]
        if k == "enum": return value if value in field.choices else field.default
    except (TypeError, ValueError):
        pass
    return copy.deepcopy(field.default)

class Component:
    type_name = "Component"
    fields: tuple = ()
    removable = True
    unique = True

    def __init__(self, props=None, enabled=True):
        self.enabled = bool(enabled)
        self.props = {f.name: copy.deepcopy(f.default) for f in self.fields}
        if props:
            for f in self.fields:
                if f.name in props:
                    self.props[f.name] = coerce(f, props[f.name])

    def field(self, name):
        for f in self.fields:
            if f.name == name: return f
        raise KeyError(f"{self.type_name} no tiene la propiedad '{name}'")

    def get(self, name, default=None):
        if name in self.props: return self.props[name]
        if default is not None: return default
        self.field(name)
        return self.props[name]

    def set(self, name, value):
        self.props[name] = coerce(self.field(name), value)

    def start(self, game_object): pass
    def update(self, game_object, dt): pass
    def destroy(self, game_object): pass

    def to_dict(self):
        return {"type": self.type_name, "enabled": self.enabled, "props": copy.deepcopy(self.props)}

    @staticmethod
    def from_dict(data):
        cls = COMPONENT_REGISTRY.get(data.get("type"))
        if cls is None: return MissingComponent(data)
        props = data.get("props")
        return cls(props if isinstance(props, dict) else None, data.get("enabled", True))

class MissingComponent(Component):
    """Componente desconocido (se conserva al guardar)."""
    type_name = "Missing"
    def __init__(self, raw):
        super().__init__()
        self.raw = copy.deepcopy(raw)
        self.enabled = bool(raw.get("enabled", True))
    def to_dict(self): return copy.deepcopy(self.raw)

# --- Componentes Integrados ---
@register_component
class Transform(Component):
    """Posición, rotación y escala."""
    type_name = "Transform"
    removable = False
    fields = (
        Field("position", "vec2", [0.0, 0.0], "Position", -1e6, 1e6, 1.0),
        Field("rotation", "float", 0.0, "Rotation", -360000, 360000, 1.0),
        Field("scale", "vec2", [1.0, 1.0], "Scale", -1000, 1000, 0.1),
    )

@register_component
class SpriteRenderer(Component):
    type_name = "SpriteRenderer"
    fields = (
        Field("image", "image", "", "Sprite"),
        Field("color", "color", "#ffffff", "Color"),
        Field("size", "vec2", [100.0, 100.0], "Size", 1, 100000, 1.0),
        Field("filter", "enum", "Linear", "Filter", choices=("Linear", "Nearest")),
        Field("flip_x", "bool", False, "Flip X"),
        Field("flip_y", "bool", False, "Flip Y"),
        Field("layer", "enum", "Midground", "Layer", choices=("Background", "Midground", "Foreground", "UI")),
        Field("sorting_order", "int", 0, "Sorting Order", -1000, 1000, 1),
    )

@register_component
class Camera(Component):
    type_name = "Camera"
    fields = (
        Field("orthographic_size", "float", 360.0, "Orthographic Size", 1, 100000, 10.0),
        Field("background", "color", "#1b1e26", "Background"),
        Field("priority", "int", 0, "Priority", -1000, 1000, 1),
        Field("follow_target", "string", "", "Follow Target (name/id)"),
        Field("follow_lerp", "float", 0.0, "Follow Lerp (0=instant)", 0.0, 1.0, 0.05),
        Field("transition_duration", "float", 0.0, "Transition (s)", 0.0, 10.0, 0.1),
        Field("viewport_width", "int", 1100, "Viewport Width", 1, 16384, 1),
        Field("viewport_height", "int", 700, "Viewport Height", 1, 16384, 1),
    )

@register_component
class Rotator(Component):
    type_name = "Rotator"
    fields = (Field("speed", "float", 90.0, "Speed (°/s)", -100000, 100000, 5.0),)
    def update(self, game_object, dt):
        tr = game_object.transform
        tr.set("rotation", (tr.get("rotation") + self.get("speed") * dt) % 360.0)

@register_component
class PrimitiveRect(Component):
    type_name = "PrimitiveRect"
    fields = (
        Field("color", "color", "#4dd0e1", "Color"),
        Field("size", "vec2", [100.0, 100.0], "Size", 1, 100000, 1.0),
        Field("filled", "bool", True, "Filled"),
        Field("layer", "enum", "Midground", "Layer", choices=("Background", "Midground", "Foreground", "UI")),
        Field("sorting_order", "int", 0, "Sorting Order", -1000, 1000, 1),
    )

@register_component
class PrimitiveCircle(Component):
    type_name = "PrimitiveCircle"
    fields = (
        Field("color", "color", "#ff7043", "Color"),
        Field("radius", "float", 50.0, "Radius", 1, 100000, 1.0),
        Field("filled", "bool", True, "Filled"),
        Field("layer", "enum", "Midground", "Layer", choices=("Background", "Midground", "Foreground", "UI")),
        Field("sorting_order", "int", 0, "Sorting Order", -1000, 1000, 1),
    )

@register_component
class TextRenderer(Component):
    type_name = "TextRenderer"
    fields = (
        Field("text", "string", "Hello", "Text"),
        Field("font_size", "int", 24, "Font Size", 4, 400, 1),
        Field("color", "color", "#ffffff", "Color"),
        Field("layer", "enum", "UI", "Layer", choices=("Background", "Midground", "Foreground", "UI")),
        Field("sorting_order", "int", 100, "Sorting Order", -1000, 1000, 1),
    )

@register_component
class Container(Component):
    type_name = "Container"
    fields = (Field("color", "color", "#8b75ff", "Marker Color"),)

@register_component
class BoxCollider(Component):
    type_name = "BoxCollider"
    fields = (
        Field("size", "vec2", [100.0, 100.0], "Size", 1, 100000, 1.0),
        Field("offset", "vec2", [0.0, 0.0], "Offset", -100000, 100000, 1.0),
        Field("is_trigger", "bool", False, "Is Trigger"),
        Field("layer", "enum", "Default", "Layer", choices=("Default", "Player", "Enemy", "Environment", "UI")),
        Field("collision_mask", "string", "Default,Player,Enemy,Environment,UI", "Collision Mask"),
    )

@register_component
class CircleCollider(Component):
    type_name = "CircleCollider"
    fields = (
        Field("radius", "float", 50.0, "Radius", 1, 100000, 1.0),
        Field("offset", "vec2", [0.0, 0.0], "Offset", -100000, 100000, 1.0),
        Field("is_trigger", "bool", False, "Is Trigger"),
        Field("layer", "enum", "Default", "Layer", choices=("Default", "Player", "Enemy", "Environment", "UI")),
        Field("collision_mask", "string", "Default,Player,Enemy,Environment,UI", "Collision Mask"),
    )

@register_component
class RigidBody(Component):
    type_name = "RigidBody"
    fields = (
        Field("body_type", "enum", "Dynamic", "Body Type", choices=("Dynamic", "Static", "Kinematic")),
        Field("velocity", "vec2", [0.0, 0.0], "Velocity", -100000, 100000, 1.0),
        Field("mass", "float", 1.0, "Mass", 0.001, 100000, 1.0),
        Field("gravity_scale", "float", 1.0, "Gravity Scale", -10.0, 10.0, 0.1),
        Field("linear_drag", "float", 0.0, "Linear Drag", 0.0, 100.0, 0.1),
        Field("bounciness", "float", 0.0, "Bounciness", 0.0, 1.0, 0.05),
        Field("friction", "float", 0.3, "Friction", 0.0, 1.0, 0.05),
    )