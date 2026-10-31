"""Sistema de tiempo del juego y utilidades de espera."""

class Wait:
    """Objeto para usar con `yield` dentro de update() para hacer pausas."""
    def __init__(self, seconds=0.0):
        self.seconds = max(0.0, float(seconds))

class Time:
    dt = 0.0
    fixed_dt = 1.0 / 60.0
    elapsed = 0.0
    time_scale = 1.0
    frame_count = 0

    @classmethod
    def wait(cls, seconds):
        return Wait(seconds)

    @classmethod
    def now(cls):
        return cls.elapsed

    @classmethod
    def _wait_seconds(cls, value):
        if isinstance(value, Wait):
            return value.seconds
        if value is None:
            return 0.0
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return 0.0