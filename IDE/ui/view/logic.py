"""Utilidades geométricas de la vista (sin Qt)."""
import math

def snap(value, size):
    if not size: return value
    return round(value / size) * size

def camera_space(camera, x, y):
    dx = float(x) - float(camera.x)
    dy = float(y) - float(camera.y)
    rad = math.radians(-float(camera.rotation))
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    return dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a

def object_size(obj):
    for t in ("SpriteRenderer", "PrimitiveRect"):
        c = obj.get_component(t)
        if c is not None and c.enabled:
            s = c.get("size", [100, 100])
            return abs(float(s[0])), abs(float(s[1]))
    c = obj.get_component("PrimitiveCircle")
    if c is not None and c.enabled:
        r = abs(float(c.get("radius", 50)))
        return r * 2, r * 2
    return 50.0, 50.0