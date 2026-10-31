"""Script-facing operations for custom render and collision layers."""
from uron.core.layers import layers


class _LayersAPI:
    def create_render_layer(self, name, order):
        return layers.create_render_layer(name, order)

    def create_collision_layer(self, name):
        return layers.create_collision_layer(name)

    def render_layers(self):
        return layers.render_layers()

    def collision_layers(self):
        return layers.collision_layers()


Layers = _LayersAPI()
