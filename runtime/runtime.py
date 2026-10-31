"""URON Runtime: carga escena, ejecuta scripts y renderiza con pygame/OpenGL."""
import json
import math
import os
import queue
import sys
import threading

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ["PYOPENGL_PLATFORM"] = "glx" # Fix para Linux

if os.environ.get("DISPLAY") and not os.environ.get("SDL_VIDEODRIVER"):
    os.environ["SDL_VIDEODRIVER"] = "x11"

import pygame
from OpenGL.GL import (
    GL_BLEND, GL_COLOR_BUFFER_BIT, GL_LINEAR, GL_LINE_LOOP, GL_LINES,
    GL_MODELVIEW, GL_NEAREST, GL_ONE_MINUS_SRC_ALPHA, GL_PROJECTION, GL_QUADS,
    GL_RGBA, GL_SRC_ALPHA, GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER, GL_TRIANGLE_FAN, GL_UNSIGNED_BYTE,
    glBegin, glBindTexture, glBlendFunc, glClear, glClearColor, glColor4f,
    glDisable, glEnable, glEnd, glGenTextures, glLineWidth, glLoadIdentity,
    glMatrixMode, glOrtho, glPopMatrix, glPushMatrix, glRotatef, glTexCoord2f,
    glTexImage2D, glTexParameteri, glTranslatef, glVertex2f, glViewport,
)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from uron.core.scene import Scene
from uron.core.layers import layers
from uron.core.physics import PhysicsSystem
from uron.core.util import parse_color
from uron.render.camera import CameraSystem
from uron.api.scripting import (
    Audio, Camera, Input, Physics, Time, draw, reload_changed_scripts,
)

TEXT_CACHE_LIMIT = 128


def resolve_asset(project_folder, path):
    if not path:
        return None
    path = str(path)
    if os.path.isabs(path) and os.path.isfile(path):
        return path
        
    base = project_folder or os.getcwd()
    full = os.path.join(base, path)
    if os.path.isfile(full):
        return full
        
    if hasattr(sys, "_MEIPASS"):
        base_mei = os.path.join(sys._MEIPASS, "game")
        full_mei = os.path.join(base_mei, path)
        if os.path.isfile(full_mei):
            return full_mei
            
    return None


def _load_settings(project_folder):
    defaults = {
        "window": {"width": 1100, "height": 700, "resizable": True},
        "runtime": {"target_fps": 60, "physics_fps": 60},
    }
    if not project_folder:
        return defaults
    path = os.path.join(project_folder, ".uron", "settings.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return defaults
    for section, values in (data or {}).items():
        if isinstance(values, dict) and isinstance(defaults.get(section), dict):
            defaults[section].update(values)
        else:
            defaults[section] = values
    return defaults


class TextureCache:
    def __init__(self, project_folder=None):
        self._cache = {}
        self.project_folder = project_folder

    def get(self, path, filter_mode="Linear"):
        full = resolve_asset(self.project_folder, path)
        if not full:
            return None
        key = (os.path.abspath(full), filter_mode)
        if key in self._cache:
            return self._cache[key]
        try:
            surf = pygame.image.load(full).convert_alpha()
        except Exception:
            self._cache[key] = None
            return None
        data = pygame.image.tostring(surf, "RGBA", True)
        w, h = surf.get_width(), surf.get_height()
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        filt = GL_NEAREST if filter_mode == "Nearest" else GL_LINEAR
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, filt)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, filt)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        self._cache[key] = tex_id
        return tex_id

_TEXT_CACHE = {}

def _text_texture(text, font_size, color):
    text = str(text)
    if not text: return None
    font_size = max(1, int(font_size))
    rgba = parse_color(color, (255, 255, 255, 255))
    key = (text, font_size, rgba)
    entry = _TEXT_CACHE.get(key)
    if entry is not None: return entry
    if len(_TEXT_CACHE) >= TEXT_CACHE_LIMIT:
        oldest = next(iter(_TEXT_CACHE))
        _TEXT_CACHE.pop(oldest, None)
    try:
        if not pygame.font.get_init(): pygame.font.init()
        font = pygame.font.SysFont(None, font_size)
        surf = font.render(text, True, rgba[:3])
        w, h = surf.get_width(), surf.get_height()
        if w <= 0 or h <= 0: return None
        data = pygame.image.tostring(surf, "RGBA", True)
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        entry = (tex_id, w, h)
        _TEXT_CACHE[key] = entry
        return entry
    except Exception as exc:
        print(f"[Runtime] Error de texto: {exc}")
        return None

def _apply_projection(width, height, ortho_size):
    glViewport(0, 0, max(1, width), max(1, height))
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    height = max(1, height)
    aspect = max(1, width) / height
    half_h = max(0.001, float(ortho_size))
    half_w = half_h * aspect
    # IMPORTANTE: half_h positivo y luego negativo para que Y vaya hacia abajo
    glOrtho(-half_w, half_w, half_h, -half_h, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def _apply_screen_projection(width, height):
    glViewport(0, 0, max(1, width), max(1, height))
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, max(1, width), max(1, height), 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def _apply_camera_transform(camera):
    glLoadIdentity()
    glTranslatef(-float(camera.x), -float(camera.y), 0.0)
    if abs(camera.rotation) > 1e-9:
        glRotatef(-float(camera.rotation), 0.0, 0.0, 1.0)


def _draw_sprite(obj, textures, world):
    sprite = obj.get_component("SpriteRenderer")
    if sprite is None or not sprite.enabled: return
    size = sprite.get("size")
    sx = world["world_scale_x"] if world["world_scale_x"] else 1.0
    sy = world["world_scale_y"] if world["world_scale_y"] else 1.0
    w = max(0.0001, float(size[0])) * sx
    h = max(0.0001, float(size[1])) * sy
    color = parse_color(sprite.get("color"), (255, 255, 255, 255))
    r, g, b, a = (c / 255.0 for c in color)
    flip_x = bool(sprite.get("flip_x"))
    flip_y = bool(sprite.get("flip_y"))
    tex_id = textures.get(sprite.get("image"), sprite.get("filter", "Linear"))
    
    glPushMatrix()
    glTranslatef(float(world["world_x"]), float(world["world_y"]), 0.0)
    glRotatef(-float(world["world_rotation"]), 0.0, 0.0, 1.0)
    glColor4f(r, g, b, a)
    hw, hh = w / 2.0, h / 2.0
    
    if tex_id is not None:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        u0, u1 = (1.0, 0.0) if flip_x else (0.0, 1.0)
        # Invertimos V (texturas en OpenGL) para que se vea bien con Y hacia abajo
        v0, v1 = (0.0, 1.0) if flip_y else (1.0, 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(u0, v0); glVertex2f(-hw, -hh)
        glTexCoord2f(u1, v0); glVertex2f(hw, -hh)
        glTexCoord2f(u1, v1); glVertex2f(hw, hh)
        glTexCoord2f(u0, v1); glVertex2f(-hw, hh)
        glEnd()
        glDisable(GL_TEXTURE_2D)
    else:
        glBegin(GL_QUADS)
        glVertex2f(-hw, -hh); glVertex2f(hw, -hh)
        glVertex2f(hw, hh); glVertex2f(-hw, hh)
        glEnd()
    glPopMatrix()

def _draw_primitive_rect(obj, world):
    comp = obj.get_component("PrimitiveRect")
    if comp is None or not comp.enabled: return
    size = comp.get("size")
    w = float(size[0]) * world["world_scale_x"]
    h = float(size[1]) * world["world_scale_y"]
    color = parse_color(comp.get("color"), (77, 208, 225, 255))
    r, g, b, a = (c / 255.0 for c in color)
    filled = bool(comp.get("filled"))
    hw, hh = w / 2.0, h / 2.0
    glPushMatrix()
    glTranslatef(world["world_x"], world["world_y"], 0.0)
    glRotatef(-world["world_rotation"], 0.0, 0.0, 1.0)
    glColor4f(r, g, b, a)
    glBegin(GL_QUADS if filled else GL_LINE_LOOP)
    glVertex2f(-hw, -hh); glVertex2f(hw, -hh)
    glVertex2f(hw, hh); glVertex2f(-hw, hh)
    glEnd()
    glPopMatrix()

def _draw_primitive_circle(obj, world):
    comp = obj.get_component("PrimitiveCircle")
    if comp is None or not comp.enabled: return
    radius = float(comp.get("radius", 50)) * max(abs(world["world_scale_x"]), abs(world["world_scale_y"]))
    color = parse_color(comp.get("color"), (255, 112, 67, 255))
    r, g, b, a = (c / 255.0 for c in color)
    filled = bool(comp.get("filled"))
    glPushMatrix()
    glTranslatef(world["world_x"], world["world_y"], 0.0)
    glColor4f(r, g, b, a)
    segments = 32
    if filled:
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(0.0, 0.0)
        for i in range(segments + 1):
            ang = 2 * math.pi * i / segments
            glVertex2f(math.cos(ang) * radius, math.sin(ang) * radius)
        glEnd()
    else:
        glBegin(GL_LINE_LOOP)
        for i in range(segments):
            ang = 2 * math.pi * i / segments
            glVertex2f(math.cos(ang) * radius, math.sin(ang) * radius)
        glEnd()
    glPopMatrix()

def _draw_text(obj, world):
    comp = obj.get_component("TextRenderer")
    if comp is None or not comp.enabled: return
    text = str(comp.get("text", ""))
    if not text: return
    entry = _text_texture(text, comp.get("font_size", 24), comp.get("color", "#ffffff"))
    if entry is None: return
    tex_id, w, h = entry
    hw, hh = w / 2.0, h / 2.0
    glPushMatrix()
    glTranslatef(world["world_x"], world["world_y"], 0.0)
    glRotatef(-world["world_rotation"], 0.0, 0.0, 1.0)
    glColor4f(1.0, 1.0, 1.0, 1.0)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 1.0); glVertex2f(-hw, -hh)
    glTexCoord2f(1.0, 1.0); glVertex2f(hw, -hh)
    glTexCoord2f(1.0, 0.0); glVertex2f(hw, hh)
    glTexCoord2f(0.0, 0.0); glVertex2f(-hw, hh)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glPopMatrix()


def _render_draw_command(kind, args, kwargs):
    color = kwargs.get("color", "#ffffff")
    r, g, b, a = (c / 255.0 for c in parse_color(color))
    if kind == "rect":
        x, y, w, h = args
        glPushMatrix()
        glTranslatef(float(x), float(y), 0.0)
        glColor4f(r, g, b, a)
        hw, hh = float(w) / 2.0, float(h) / 2.0
        glBegin(GL_QUADS if kwargs.get("fill", True) else GL_LINE_LOOP)
        glVertex2f(-hw, -hh); glVertex2f(hw, -hh)
        glVertex2f(hw, hh); glVertex2f(-hw, hh)
        glEnd()
        glPopMatrix()
    elif kind == "circle":
        x, y, radius = args
        glPushMatrix()
        glTranslatef(float(x), float(y), 0.0)
        glColor4f(r, g, b, a)
        segments = int(kwargs.get("segments", 32))
        if kwargs.get("fill", True):
            glBegin(GL_TRIANGLE_FAN)
            glVertex2f(0.0, 0.0)
            for i in range(segments + 1):
                ang = 2 * math.pi * i / segments
                glVertex2f(math.cos(ang) * radius, math.sin(ang) * radius)
            glEnd()
        else:
            glBegin(GL_LINE_LOOP)
            for i in range(segments):
                ang = 2 * math.pi * i / segments
                glVertex2f(math.cos(ang) * radius, math.sin(ang) * radius)
            glEnd()
        glPopMatrix()
    elif kind == "line":
        x1, y1, x2, y2 = args
        glColor4f(r, g, b, a)
        glBegin(GL_LINES)
        glVertex2f(float(x1), float(y1)); glVertex2f(float(x2), float(y2))
        glEnd()
    elif kind == "text":
        text, x, y = args
        entry = _text_texture(text, kwargs.get("size", 18), color)
        if entry is None: return
        tex_id, w, h = entry
        glPushMatrix()
        glTranslatef(float(x), float(y), 0.0)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0); glVertex2f(0.0, 0.0)
        glTexCoord2f(1.0, 1.0); glVertex2f(w, 0.0)
        glTexCoord2f(1.0, 0.0); glVertex2f(w, h)
        glTexCoord2f(0.0, 0.0); glVertex2f(0.0, h)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

def _draw_script_commands(camera):
    commands = draw.consume()
    for kind, args, kwargs in commands:
        if kwargs.get("screen", False): continue
        _render_draw_command(kind, args, kwargs)
    return [(kind, args, kwargs) for kind, args, kwargs in commands if kwargs.get("screen", False)]

def _start_command_reader(commands):
    def worker():
        try:
            for line in sys.stdin:
                cmd = line.strip().lower()
                if cmd: commands.put(cmd)
                if cmd == "stop": return
        except Exception: return
    threading.Thread(target=worker, daemon=True).start()

def _poll_joystick():
    try:
        joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        for js in joysticks:
            if not js.get_init(): js.init()
        return joysticks
    except Exception: return []

def _update_input(gamepads):
    pressed = pygame.key.get_pressed()
    new_keys = {i for i in range(len(pressed)) if pressed[i]}
    just_pressed = new_keys - Input._keys
    just_released = Input._keys - new_keys
    Input._keys = new_keys
    Input._just_pressed |= just_pressed
    Input._just_released |= just_released

    mouse_buttons = pygame.mouse.get_pressed()
    new_buttons = {i for i in range(len(mouse_buttons)) if mouse_buttons[i]}
    Input._mouse_just_pressed |= (new_buttons - Input._mouse_buttons)
    Input._mouse_just_released |= (Input._mouse_buttons - new_buttons)
    Input._mouse_buttons = new_buttons

    pos = pygame.mouse.get_pos()
    old = Input._mouse_pos
    Input._mouse_delta = (pos[0] - old[0], pos[1] - old[1])
    Input._mouse_pos = (float(pos[0]), float(pos[1]))

    Input._gamepad_buttons = set()
    Input._gamepad_axes = {}
    for pad in gamepads:
        try:
            for b in range(pad.get_numbuttons()):
                if pad.get_button(b): Input._gamepad_buttons.add(b)
            for a in range(pad.get_numaxes()):
                Input._gamepad_axes[a] = pad.get_axis(a)
        except Exception: continue

def _handle_events(physics_debug, width, height):
    running = True
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False
            elif event.key == pygame.K_F1: physics_debug = not physics_debug
        elif event.type == pygame.MOUSEWHEEL:
            Input._mouse_wheel += float(event.y)
        elif event.type == pygame.VIDEORESIZE:
            width, height = max(1, event.w), max(1, event.h)
    return running, physics_debug, width, height

def run_scene(scene_path, project_folder=None, width=None, height=None, target_fps=None):
    scene_path = os.path.abspath(scene_path)
    if project_folder is None: project_folder = os.path.dirname(scene_path)
    project_folder = os.path.abspath(project_folder)
    
    settings = _load_settings(project_folder)
    window_cfg = settings.get("window", {})
    runtime_cfg = settings.get("runtime", {})
    width = int(width or window_cfg.get("width", 1100))
    height = int(height or window_cfg.get("height", 700))
    target_fps = int(target_fps or runtime_cfg.get("target_fps", 60))
    physics_fps = max(1, int(runtime_cfg.get("physics_fps", 60)))
    resizable = bool(window_cfg.get("resizable", True))

    layers.reset()
    scene = Scene.load(scene_path)

    Audio.configure(project_folder)
    for obj in scene.objects:
        for comp in obj.get_components("Script"):
            comp.instantiate(obj, scene, project_folder)

    pygame.init()
    try: pygame.mixer.init()
    except Exception: pass
    
    pygame.display.set_caption(f"URON Runtime — {scene.name}")
    flags = pygame.OPENGL | pygame.DOUBLEBUF
    if resizable: flags |= pygame.RESIZABLE
    pygame.display.set_mode((max(1, width), max(1, height)), flags)
    
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    textures = TextureCache(project_folder)
    physics_system = PhysicsSystem(scene)
    physics_system.fixed_dt = 1.0 / physics_fps
    Physics.configure(physics_system)
    
    camera_system = CameraSystem(scene)
    camera_system.update(0.0, force=True)
    Camera.configure(camera_system)
    
    _apply_projection(width, height, camera_system.ortho_size)

    physics_debug = False
    paused = False
    step_once = False
    running = True
    accumulator = 0.0
    reload_timer = 0.0
    commands = queue.Queue()
    _start_command_reader(commands)
    gamepads = _poll_joystick()
    clock = pygame.time.Clock()

    scene.start()
    print(f"[Runtime] URON 0.5 — {scene.name} ({width}x{height} @ {target_fps}fps)")

    while running:
        real_dt = clock.tick(max(1, target_fps)) / 1000.0
        real_dt = min(real_dt, 0.1)
        Input._begin_frame()

        running, physics_debug, width, height = _handle_events(physics_debug, width, height)
        _update_input(gamepads)

        while True:
            try: command = commands.get_nowait()
            except queue.Empty: break
            if command == "pause":
                paused = True
            elif command in ("resume", "play"):
                paused = False
            elif command == "step":
                paused = True; step_once = True
            elif command == "reload":
                count = reload_changed_scripts(scene, project_folder)
            elif command == "stop":
                running = False

        simulate = (not paused) or step_once
        if simulate:
            StepTime = Time
            StepTime.fixed_dt = physics_system.fixed_dt
            StepTime.dt = real_dt * StepTime.time_scale
            StepTime.elapsed += StepTime.dt
            StepTime.frame_count += 1

            if paused and step_once: accumulator = StepTime.fixed_dt
            else: accumulator += StepTime.dt
                
            steps = 0
            while accumulator >= StepTime.fixed_dt and steps < 8:
                physics_system.step(StepTime.fixed_dt)
                accumulator -= StepTime.fixed_dt
                steps += 1
            if steps >= 8: accumulator = 0.0

            scene.update(StepTime.dt)
            step_once = False

            reload_timer += real_dt
            if reload_timer >= 0.75:
                reload_timer = 0.0
                count = reload_changed_scripts(scene, project_folder)

        camera_system.update(real_dt, force=(camera_system.object_id is None))
        _apply_projection(width, height, camera_system.ortho_size)

        bg = camera_system.background
        glClearColor(bg[0] / 255.0, bg[1] / 255.0, bg[2] / 255.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        _apply_camera_transform(camera_system)

        aspect = width / max(1, height)
        half_w = camera_system.ortho_size * aspect
        half_h = camera_system.ortho_size

        renderables = []
        for obj in scene.objects:
            if not obj.active or getattr(obj, "_destroy_pending", False): continue
            layer = "Midground"
            sort_order = 0
            has_render = False
            for comp_type in ("SpriteRenderer", "PrimitiveRect", "PrimitiveCircle", "TextRenderer"):
                comp = obj.get_component(comp_type)
                if comp is not None and comp.enabled:
                    has_render = True
                    layer = comp.get("layer", "Midground")
                    sort_order = comp.get("sorting_order", 0)
                    break
            if not has_render: continue
            
            world = scene.world_transform(obj)
            if abs(world["world_x"] - camera_system.x) > half_w + 200: continue
            if abs(world["world_y"] - camera_system.y) > half_h + 200: continue
            renderables.append((obj, layer, sort_order, world))

        renderables.sort(key=lambda t: (layers.render_order(t[1]), t[2]))
        for obj, _layer, _sort, world in renderables:
            _draw_sprite(obj, textures, world)
            _draw_primitive_rect(obj, world)
            _draw_primitive_circle(obj, world)
            _draw_text(obj, world)

        screen_commands = _draw_script_commands(camera_system)
        if screen_commands:
            _apply_screen_projection(width, height)
            for kind, args, kwargs in screen_commands:
                _render_draw_command(kind, args, kwargs)

        pygame.display.flip()

    pygame.quit()

def main(argv):
    if len(argv) < 2:
        print("Usage: runtime.py scene.uron.json [project_folder]")
        raise SystemExit(2)
    scene_path = argv[1]
    project_folder = argv[2] if len(argv) >= 3 else None
    run_scene(scene_path, project_folder)

if __name__ == "__main__":
    main(sys.argv)
