"""Registry for render and collision layer names."""

DEFAULT_RENDER_LAYERS = (
    ("Background", 0),
    ("Midground", 1),
    ("Foreground", 2),
    ("UI", 3),
)
DEFAULT_COLLISION_LAYERS = ("Default", "Player", "Enemy", "Environment", "UI")


class LayerRegistry:
    def __init__(self):
        self.reset()

    def reset(self):
        self._render_layers = dict(DEFAULT_RENDER_LAYERS)
        self._collision_layers = list(DEFAULT_COLLISION_LAYERS)

    def create_render_layer(self, name, order):
        name = self._normalize_name(name)
        if isinstance(order, bool):
            raise ValueError("Render layer order must be an integer")
        requested_order = order
        try:
            order = int(order)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Render layer order must be an integer") from exc
        if isinstance(requested_order, float) and not requested_order.is_integer():
            raise ValueError("Render layer order must be an integer")

        if name in self._render_layers:
            if self._render_layers[name] != order:
                raise ValueError(f"Render layer already exists with another order: {name}")
            return name
        self._render_layers[name] = order
        return name

    def create_collision_layer(self, name):
        name = self._normalize_name(name)
        if name not in self._collision_layers:
            self._collision_layers.append(name)
        return name

    def render_order(self, name):
        return self._render_layers.get(name, max(self._render_layers.values(), default=-1) + 1)

    def render_layers(self):
        return tuple(sorted(self._render_layers.items(), key=lambda layer: (layer[1], layer[0])))

    def collision_layers(self):
        return tuple(self._collision_layers)

    @staticmethod
    def _normalize_name(name):
        if not isinstance(name, str):
            raise ValueError("Layer name must be a string")
        name = name.strip()
        if not name or "," in name:
            raise ValueError("Layer name must be non-empty and cannot contain commas")
        return name


layers = LayerRegistry()
