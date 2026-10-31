"""Funciones matemáticas auxiliares para el motor."""
import math

def clamp(value, min_value, max_value):
    """Limita un valor entre un mínimo y un máximo."""
    return max(min_value, min(max_value, value))

def lerp(a, b, t):
    """Interpolación lineal entre `a` y `b` con factor `t`."""
    t = clamp(t, 0.0, 1.0)
    return a + (b - a) * t

def lerp_angle(a, b, t):
    """Interpolación angular (evita el salto de 360 a 0)."""
    diff = ((b - a + 180) % 360) - 180
    return a + diff * clamp(t, 0.0, 1.0)

def deg_to_rad(degrees):
    return degrees * (math.pi / 180.0)

def rad_to_deg(radians):
    return radians * (180.0 / math.pi)

def move_towards(current, target, max_delta):
    """Mueve `current` hacia `target` sin pasarse."""
    if abs(target - current) <= max_delta:
        return target
    return current + math.copysign(max_delta, target - current)

def distance(x1, y1, x2, y2):
    """Distancia euclidiana entre dos puntos."""
    return math.hypot(x2 - x1, y2 - y1)

def angle_between(x1, y1, x2, y2):
    """Ángulo (en grados) de un punto a otro."""
    return rad_to_deg(math.atan2(y2 - y1, x2 - x1))

def smoothstep(t):
    """Suavizado tipo S (0 a 1)."""
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)