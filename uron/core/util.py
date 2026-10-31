"""Utilidades puras compartidas por editor y runtime."""
import math

def parse_color(value, default=(255, 255, 255, 255)):
    """Convierte '#rgb', '#rrggbb' o '#rrggbbaa' a (r, g, b, a)."""
    if not isinstance(value, str):
        return default
    s = value.strip().lstrip("#")
    try:
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        if len(s) == 6:
            r, g, b = (int(s[i:i + 2], 16) for i in (0, 2, 4))
            return (r, g, b, 255)
        if len(s) == 8:
            r, g, b, a = (int(s[i:i + 2], 16) for i in (0, 2, 4, 6))
            return (r, g, b, a)
    except ValueError:
        pass
    return default

def format_color(r, g, b, a=255):
    base = "#%02x%02x%02x" % (r, g, b)
    return base if a == 255 else base + "%02x" % a

def normalize_color(value, default="#ffffff"):
    return format_color(*parse_color(value, parse_color(default)))

def is_finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)