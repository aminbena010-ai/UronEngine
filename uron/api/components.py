"""Script-facing APIs for renderers, rigidbodies, and colliders."""


class _ComponentAPI:
    component_type = None

    def __init__(self, game_object):
        self.game_object = game_object

    @property
    def component(self):
        component = self.game_object.get_component(self.component_type)
        if component is None:
            raise RuntimeError(
                f"{self.game_object.name} has no {self.component_type} component"
            )
        return component

    @property
    def enabled(self):
        return self.component.enabled

    @enabled.setter
    def enabled(self, value):
        self.component.enabled = bool(value)

    def get(self, name):
        return self.component.get(name)

    def set(self, name, value):
        self.component.set(name, value)
        return self.component.get(name)


class SpriteRendererAPI(_ComponentAPI):
    component_type = "SpriteRenderer"

    @property
    def image(self):
        return self.get("image")

    @image.setter
    def image(self, value):
        self.set_image(value)

    @property
    def color(self):
        return self.get("color")

    @color.setter
    def color(self, value):
        self.set_color(value)

    @property
    def size(self):
        return self.get("size")

    @size.setter
    def size(self, value):
        self.set("size", value)

    @property
    def layer(self):
        return self.get("layer")

    @layer.setter
    def layer(self, value):
        self.set("layer", value)

    @property
    def sorting_order(self):
        return self.get("sorting_order")

    @sorting_order.setter
    def sorting_order(self, value):
        self.set("sorting_order", value)

    def set_image(self, image):
        return self.set("image", image)

    def set_color(self, color):
        return self.set("color", color)

    def set_size(self, width, height=None):
        return self.set("size", [width, width if height is None else height])

    def set_layer(self, name, sorting_order=None):
        self.set("layer", name)
        if sorting_order is not None:
            self.set("sorting_order", sorting_order)

    def set_filter(self, filter_mode):
        return self.set("filter", filter_mode)

    def set_flip(self, horizontal=False, vertical=False):
        self.set("flip_x", horizontal)
        self.set("flip_y", vertical)


class TextRendererAPI(_ComponentAPI):
    component_type = "TextRenderer"

    @property
    def text(self):
        return self.get("text")

    @text.setter
    def text(self, value):
        self.set_text(value)

    @property
    def font_size(self):
        return self.get("font_size")

    @font_size.setter
    def font_size(self, value):
        self.set_font_size(value)

    @property
    def color(self):
        return self.get("color")

    @color.setter
    def color(self, value):
        self.set_color(value)

    @property
    def layer(self):
        return self.get("layer")

    @layer.setter
    def layer(self, value):
        self.set("layer", value)

    def set_text(self, text):
        return self.set("text", text)

    def set_font_size(self, size):
        return self.set("font_size", size)

    def set_color(self, color):
        return self.set("color", color)

    def set_layer(self, name, sorting_order=None):
        self.set("layer", name)
        if sorting_order is not None:
            self.set("sorting_order", sorting_order)


class RigidBodyAPI(_ComponentAPI):
    component_type = "RigidBody"

    def __init__(self, game_object, physics_api):
        super().__init__(game_object)
        self._physics = physics_api

    @property
    def velocity(self):
        return tuple(self.get("velocity"))

    @velocity.setter
    def velocity(self, value):
        self.set("velocity", value)

    @property
    def body_type(self):
        return self.get("body_type")

    @body_type.setter
    def body_type(self, value):
        self.set("body_type", value)

    @property
    def mass(self):
        return self.get("mass")

    @mass.setter
    def mass(self, value):
        self.set("mass", value)

    @property
    def gravity_scale(self):
        return self.get("gravity_scale")

    @gravity_scale.setter
    def gravity_scale(self, value):
        self.set("gravity_scale", value)

    @property
    def linear_drag(self):
        return self.get("linear_drag")

    @linear_drag.setter
    def linear_drag(self, value):
        self.set("linear_drag", value)

    @property
    def bounciness(self):
        return self.get("bounciness")

    @bounciness.setter
    def bounciness(self, value):
        self.set("bounciness", value)

    @property
    def friction(self):
        return self.get("friction")

    @friction.setter
    def friction(self, value):
        self.set("friction", value)

    def set_velocity(self, x, y):
        self.velocity = [x, y]

    def add_force(self, x, y):
        self.component
        self._physics.add_force(self.game_object, x, y)

    def add_impulse(self, x, y):
        self.component
        self._physics.add_impulse(self.game_object, x, y)


class ColliderAPI:
    def __init__(self, game_object):
        self.game_object = game_object

    @property
    def component(self):
        for component_type in ("BoxCollider", "CircleCollider"):
            component = self.game_object.get_component(component_type)
            if component is not None:
                return component
        raise RuntimeError(f"{self.game_object.name} has no collider component")

    @property
    def layer(self):
        return self.component.get("layer")

    @layer.setter
    def layer(self, value):
        self.set_layer(value)

    @property
    def mask(self):
        return self.component.get("collision_mask")

    @mask.setter
    def mask(self, value):
        self.set_mask(value)

    def set_layer(self, name, mask=None):
        self.component.set("layer", name)
        if mask is not None:
            self.set_mask(mask)

    def set_mask(self, mask):
        if isinstance(mask, str):
            value = mask
        else:
            try:
                value = ",".join(str(name) for name in mask)
            except TypeError as exc:
                raise ValueError("Collision mask must be a string or iterable of names") from exc
        self.component.set("collision_mask", value)
        return self.component.get("collision_mask")
