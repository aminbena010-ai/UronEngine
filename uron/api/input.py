"""Sistema de entrada de teclado y ratón para los scripts."""
import pygame

class Keys:
    """Códigos de tecla compatibles con pygame/SDL."""
    # Letras
    a = A = 97; b = B = 98; c = C = 99; d = D = 100; e = E = 101
    f = F = 102; g = G = 103; h = H = 104; i = I = 105; j = J = 106
    k = K = 107; l = L = 108; m = M = 109; n = N = 110; o = O = 111
    p = P = 112; q = Q = 113; r = R = 114; s = S = 115; t = T = 116
    u = U = 117; v = V = 118; w = W = 119; x = X = 120; y = Y = 121
    z = Z = 122
    # Números
    K0 = 48; K1 = 49; K2 = 50; K3 = 51; K4 = 52
    K5 = 53; K6 = 54; K7 = 55; K8 = 56; K9 = 57
    # Control
    SPACE = 32; ENTER = 13; RETURN = 13; ESC = 27; ESCAPE = 27
    TAB = 9; BACKSPACE = 8; DELETE = 127; INSERT = 1073741897
    HOME = 1073741898; END = 1073741901
    PAGEUP = 1073741899; PAGEDOWN = 1073741902
    # Flechas
    LEFT = 1073741904; RIGHT = 1073741903
    UP = 1073741906; DOWN = 1073741905
    # Modificadores
    LSHIFT = 1073742049; RSHIFT = 1073742053
    LCTRL = 1073742048; RCTRL = 1073742052
    LALT = 1073742050; RALT = 1073742054
    # Función
    F1 = 1073741882; F2 = 1073741883; F3 = 1073741884; F4 = 1073741885
    F5 = 1073741886; F6 = 1073741887; F7 = 1073741888; F8 = 1073741889
    F9 = 1073741890; F10 = 1073741891; F11 = 1073741892; F12 = 1073741893
    # Botones del ratón
    MOUSE_LEFT = 0; MOUSE_MIDDLE = 1; MOUSE_RIGHT = 2


def _resolve_key(key):
    if isinstance(key, str):
        return getattr(Keys, key, getattr(Keys, key.upper(), None))
    return key

class Input:
    _keys = set()
    _just_pressed = set()
    _just_released = set()
    
    _mouse_buttons = set()
    _mouse_just_pressed = set()
    _mouse_just_released = set()
    _mouse_pos = (0.0, 0.0)
    _mouse_delta = (0.0, 0.0)
    _mouse_wheel = 0.0
    
    _gamepad_buttons = set()
    _gamepad_axes = {}

    # --- Teclado ---
    @classmethod
    def key(cls, keycode):
        return _resolve_key(keycode) in cls._keys

    @classmethod
    def key_down(cls, keycode):
        return _resolve_key(keycode) in cls._just_pressed

    @classmethod
    def key_up(cls, keycode):
        return _resolve_key(keycode) in cls._just_released

    @classmethod
    def axis(cls, negative, positive):
        """Devuelve -1, 0 o 1 según dos teclas (ideal para WASD/flechas)."""
        neg = 1 if cls.key(negative) else 0
        pos = 1 if cls.key(positive) else 0
        return pos - neg

    # --- Ratón ---
    @classmethod
    def mouse_button(cls, button=0):
        return button in cls._mouse_buttons

    @classmethod
    def mouse_button_down(cls, button=0):
        return button in cls._mouse_just_pressed

    @classmethod
    def mouse_button_up(cls, button=0):
        return button in cls._mouse_just_released

    @classmethod
    def mouse_pos(cls):
        return cls._mouse_pos

    @classmethod
    def mouse_delta(cls):
        return cls._mouse_delta

    @classmethod
    def mouse_wheel(cls):
        return cls._mouse_wheel

    # --- Gamepad ---
    @classmethod
    def gamepad_axis(cls, axis=0):
        return float(cls._gamepad_axes.get(int(axis), 0.0))

    @classmethod
    def gamepad_button(cls, button=0):
        return int(button) in cls._gamepad_buttons

    # --- Internos del motor (llamados desde el runtime) ---
    @classmethod
    def _begin_frame(cls):
        cls._just_pressed = set()
        cls._just_released = set()
        cls._mouse_just_pressed = set()
        cls._mouse_just_released = set()
        cls._mouse_wheel = 0.0
        cls._mouse_delta = (0.0, 0.0)

    @classmethod
    def _set_key(cls, keycode, down):
        if down:
            if keycode not in cls._keys: cls._just_pressed.add(keycode)
            cls._keys.add(keycode)
        else:
            if keycode in cls._keys: cls._just_released.add(keycode)
            cls._keys.discard(keycode)

    @classmethod
    def _set_mouse_button(cls, button, down):
        if down:
            if button not in cls._mouse_buttons: cls._mouse_just_pressed.add(button)
            cls._mouse_buttons.add(button)
        else:
            if button in cls._mouse_buttons: cls._mouse_just_released.add(button)
            cls._mouse_buttons.discard(button)