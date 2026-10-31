"""Clase Vector2 para matemáticas 2D."""
import math

class Vector2:
    """Representa un vector de 2 dimensiones (X, Y)."""
    
    __slots__ = ('x', 'y')

    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    # --- Propiedades útiles ---
    @property
    def magnitude(self):
        """Longitud del vector."""
        return math.hypot(self.x, self.y)

    @property
    def sqr_magnitude(self):
        """Longitud al cuadrado (más rápido que magnitude)."""
        return self.x * self.x + self.y * self.y

    def normalized(self):
        """Devuelve un vector con la misma dirección pero longitud 1."""
        mag = self.magnitude
        if mag < 1e-9:
            return Vector2(0, 0)
        return Vector2(self.x / mag, self.y / mag)

    def normalize(self):
        """Normaliza este vector in-place."""
        mag = self.magnitude
        if mag < 1e-9: return
        self.x /= mag
        self.y /= mag

    def to_tuple(self):
        """Devuelve (x, y)."""
        return (self.x, self.y)

    def distance_to(self, other):
        """Distancia hasta otro vector."""
        return math.hypot(self.x - other.x, self.y - other.y)

    def lerp(self, target, t):
        """Interpola linealmente hacia `target` con un factor `t` (0 a 1)."""
        t = max(0.0, min(1.0, t))
        return Vector2(
            self.x + (target.x - self.x) * t,
            self.y + (target.y - self.y) * t
        )

    # --- Operadores matemáticos ---
    def __add__(self, other):
        if isinstance(other, Vector2):
            return Vector2(self.x + other.x, self.y + other.y)
        return Vector2(self.x + other, self.y + other)

    def __sub__(self, other):
        if isinstance(other, Vector2):
            return Vector2(self.x - other.x, self.y - other.y)
        return Vector2(self.x - other, self.y - other)

    def __mul__(self, other):
        if isinstance(other, Vector2):
            return Vector2(self.x * other.x, self.y * other.y)
        return Vector2(self.x * other, self.y * other)

    def __truediv__(self, other):
        if isinstance(other, Vector2):
            return Vector2(self.x / other.x, self.y / other.y)
        return Vector2(self.x / other, self.y / other)

    def __neg__(self):
        return Vector2(-self.x, -self.y)

    def __eq__(self, other):
        if isinstance(other, Vector2):
            return abs(self.x - other.x) < 1e-6 and abs(self.y - other.y) < 1e-6
        return False

    def __repr__(self):
        return f"Vector2({self.x:.3f}, {self.y:.3f})"