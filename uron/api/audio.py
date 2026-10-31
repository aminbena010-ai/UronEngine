"""Sistema de audio para los scripts."""
import os

class _Audio:
    _project_folder = None
    _sounds = {}
    _channels = []
    _volume = 1.0

    @classmethod
    def configure(cls, project_folder):
        cls._project_folder = project_folder

    @classmethod
    def _resolve(cls, path):
        if not path: return None
        if os.path.isabs(path): return path
        base = cls._project_folder or os.getcwd()
        return os.path.join(base, path)

    @classmethod
    def play(cls, path, loop=False, volume=1.0):
        try:
            import pygame
            if not pygame.mixer.get_init(): pygame.mixer.init()
            full = cls._resolve(path)
            if not full or not os.path.isfile(full):
                print(f"[Audio] No existe: {path}")
                return None
            sound = cls._sounds.get(full)
            if sound is None:
                sound = pygame.mixer.Sound(full)
                cls._sounds[full] = sound
            sound.set_volume(max(0.0, min(1.0, float(volume) * cls._volume)))
            channel = sound.play(loops=-1 if loop else 0)
            if channel is not None:
                cls._channels = [c for c in cls._channels if c.get_busy()]
                cls._channels.append(channel)
            return channel
        except Exception as exc:
            print(f"[Audio] Error: {exc}")
            return None

    @classmethod
    def stop(cls, handle=None):
        try:
            if handle is not None:
                handle.stop()
                return
            for channel in cls._channels: channel.stop()
            cls._channels.clear()
        except Exception:
            pass

    @classmethod
    def stop_all(cls):
        cls.stop()

    @classmethod
    def set_volume(cls, volume):
        cls._volume = max(0.0, min(1.0, float(volume)))

Audio = _Audio()