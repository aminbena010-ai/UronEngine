import pytest

from uron.api.components import (
    ColliderAPI, RigidBodyAPI, SpriteRendererAPI, TextRendererAPI,
)
from uron.api.layers import Layers
from uron.core.components import (
    BoxCollider, RigidBody, SpriteRenderer, TextRenderer,
)
from uron.core.layers import layers
from uron.core.physics import parse_layer_mask
from uron.core.physics import PhysicsSystem
from uron.core.scene import GameObject, Scene
from uron.api.scripting import ScriptComponent


@pytest.fixture(autouse=True)
def reset_layers():
    layers.reset()
    yield
    layers.reset()


def test_sprite_and_text_apis_update_renderer_components():
    game_object = GameObject("HUD")
    sprite_component = game_object.add_component(SpriteRenderer())
    text_component = game_object.add_component(TextRenderer())
    sprite = SpriteRendererAPI(game_object)
    text = TextRendererAPI(game_object)

    sprite.set_color("#123456")
    sprite.set_size(80, 40)
    sprite.image = "assets/sprites/icon.png"
    text.text = "Score: 12"
    text.font_size = 36

    assert sprite_component.get("color") == "#123456"
    assert sprite_component.get("size") == [80.0, 40.0]
    assert sprite_component.get("image") == "assets/sprites/icon.png"
    assert text_component.get("text") == "Score: 12"
    assert text_component.get("font_size") == 36


def test_rigidbody_and_collider_apis_update_physics_components():
    class PhysicsStub:
        def __init__(self):
            self.forces = []
            self.impulses = []

        def add_force(self, game_object, x, y):
            self.forces.append((game_object, x, y))

        def add_impulse(self, game_object, x, y):
            self.impulses.append((game_object, x, y))

    game_object = GameObject("Player")
    body_component = game_object.add_component(RigidBody())
    collider_component = game_object.add_component(BoxCollider())
    physics = PhysicsStub()
    body = RigidBodyAPI(game_object, physics)
    collider = ColliderAPI(game_object)

    body.velocity = (3, 5)
    body.mass = 2
    body.add_force(10, 0)
    body.add_impulse(0, 4)
    collider.set_layer("Player", mask=["Enemy"])

    assert body_component.get("velocity") == [3.0, 5.0]
    assert body_component.get("mass") == 2.0
    assert physics.forces == [(game_object, 10, 0)]
    assert physics.impulses == [(game_object, 0, 4)]
    assert collider_component.get("layer") == "Player"
    assert collider_component.get("collision_mask") == "Enemy"


def test_custom_layers_are_retained_and_default_collision_masks_include_them():
    Layers.create_render_layer("Effects", 5)
    Layers.create_collision_layer("Pickup")
    renderer = SpriteRenderer({"layer": "Effects"})
    collider = BoxCollider()

    assert renderer.get("layer") == "Effects"
    assert layers.render_order("Effects") == 5
    assert "Pickup" in parse_layer_mask(collider.get("collision_mask"))


def test_layer_names_and_conflicting_orders_are_validated():
    with pytest.raises(ValueError, match="non-empty"):
        Layers.create_collision_layer("")
    Layers.create_render_layer("Effects", 5)
    with pytest.raises(ValueError, match="another order"):
        Layers.create_render_layer("Effects", 6)
    with pytest.raises(ValueError, match="must be an integer"):
        Layers.create_render_layer("Fractional", 1.5)


def test_script_component_injects_renderer_physics_and_layer_apis(tmp_path):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script_path = scripts_dir / "gameplay.py"
    script_path.write_text(
        "from uron.api import UronScript\n"
        "class Gameplay(UronScript):\n"
        "    def start(self):\n"
        "        self.text.text = 'Ready'\n"
        "        self.sprite.color = '#abcdef'\n"
        "        self.layers.create_render_layer('Overlay', 8)\n"
        "        self.sprite.layer = 'Overlay'\n",
        encoding="utf-8",
    )
    game_object = GameObject("HUD")
    text = game_object.add_component(TextRenderer())
    sprite = game_object.add_component(SpriteRenderer())
    script = ScriptComponent({
        "path": "scripts/gameplay.py",
        "class_name": "Gameplay",
    })

    instance = script.instantiate(game_object, Scene(), str(tmp_path))
    instance.start()

    assert text.get("text") == "Ready"
    assert sprite.get("color") == "#abcdef"
    assert sprite.get("layer") == "Overlay"
    assert layers.render_order("Overlay") == 8


def test_physics_collision_separates_nested_dynamic_object():
    scene = Scene()
    floor = scene.create_object("Floor")
    floor.transform.set("position", [0, 0])
    floor.add_component(BoxCollider({"size": [20, 20]}))

    parent = scene.create_object("Parent")
    parent.transform.set("position", [0, 0])
    parent.transform.set("rotation", 35)
    parent.transform.set("scale", [2, 0.75])

    player = scene.create_object("Player")
    scene.reparent(player.id, parent.id)
    player.transform.set("position", [1, 0])
    player.add_component(BoxCollider({"size": [20, 20]}))
    player.add_component(RigidBody({"gravity_scale": 0}))

    before = scene.world_transform(player)
    PhysicsSystem(scene, gravity=(0, 0)).step(1 / 60)
    after = scene.world_transform(player)

    assert (after["world_x"], after["world_y"]) != (
        before["world_x"], before["world_y"]
    )


def test_world_delta_to_local_applies_parent_rotation_and_scale():
    scene = Scene()
    parent = scene.create_object("Parent")
    parent.transform.set("rotation", 90)
    parent.transform.set("scale", [2, 4])
    child = scene.create_object("Child")
    scene.reparent(child.id, parent.id)

    assert scene.world_delta_to_local(child, 0, 8) == pytest.approx([4, 0])


@pytest.mark.parametrize(
    ("is_trigger", "event_prefix"),
    [(False, "on_collision"), (True, "on_trigger")],
)
def test_physics_dispatches_enter_stay_and_exit_events(is_trigger, event_prefix):
    class EventRecorder:
        def __init__(self):
            self.events = []

        def on_collision_enter(self, other):
            self.events.append(("on_collision_enter", other))

        def on_collision_stay(self, other):
            self.events.append(("on_collision_stay", other))

        def on_collision_exit(self, other):
            self.events.append(("on_collision_exit", other))

        def on_trigger_enter(self, other):
            self.events.append(("on_trigger_enter", other))

        def on_trigger_stay(self, other):
            self.events.append(("on_trigger_stay", other))

        def on_trigger_exit(self, other):
            self.events.append(("on_trigger_exit", other))

    scene = Scene()
    first = scene.create_object("First")
    first.add_component(BoxCollider({"is_trigger": is_trigger}))
    first_script = ScriptComponent()
    first_script._instance = EventRecorder()
    first.add_component(first_script)

    second = scene.create_object("Second")
    second.add_component(BoxCollider())
    second_script = ScriptComponent()
    second_script._instance = EventRecorder()
    second.add_component(second_script)

    physics = PhysicsSystem(scene, gravity=(0, 0))
    physics.step(1 / 60)
    physics.step(1 / 60)

    second.transform.set("position", [1000, 0])
    physics.step(1 / 60)

    expected_names = [
        f"{event_prefix}_enter",
        f"{event_prefix}_stay",
        f"{event_prefix}_exit",
    ]
    assert [name for name, _ in first_script._instance.events] == expected_names
    assert [name for name, _ in second_script._instance.events] == expected_names
    assert all(other is second for _, other in first_script._instance.events)
    assert all(other is first for _, other in second_script._instance.events)
