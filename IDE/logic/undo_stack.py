"""Undo/Redo con snapshots de escena (Memento)."""
import copy

class UndoStack:
    def __init__(self, scene_ref, max_history=50):
        self.scene_ref = scene_ref
        self._max = max_history
        self._history = []
        self._index = -1

    def push(self, coalesce_key=None, force=False):
        if self.scene_ref is None:
            return
        snapshot = copy.deepcopy(self.scene_ref.to_dict())
        if self._index >= 0 and self._history[self._index] == snapshot:
            return
        if self._index < len(self._history) - 1:
            self._history = self._history[:self._index + 1]
        self._history.append(snapshot)
        self._index = len(self._history) - 1
        if len(self._history) > self._max:
            drop = len(self._history) - self._max
            self._history = self._history[drop:]
            self._index -= drop

    def can_undo(self):
        return self._index > 0
    def can_redo(self):
        return self._index >= 0 and self._index < len(self._history) - 1

    def undo(self):
        if not self.can_undo(): return False
        self._index -= 1
        self._restore(self._history[self._index])
        return True

    def redo(self):
        if not self.can_redo(): return False
        self._index += 1
        self._restore(self._history[self._index])
        return True

    def _restore(self, snapshot):
        from uron.core.scene import Scene
        restored = Scene.from_dict(copy.deepcopy(snapshot))
        self.scene_ref.name = restored.name
        self.scene_ref.objects = restored.objects

    def reset(self):
        self._history = []
        self._index = -1

    def initial_state(self):
        self.reset()
        self.push(force=True)