"""Modelo de la consola (buffer de líneas)."""
from IDE.ui.console.config import MAX_LINES

class ConsoleState:
    def __init__(self):
        self.lines = []

    def add(self, message):
        self.lines.append(str(message))
        if len(self.lines) > MAX_LINES:
            self.lines = self.lines[-MAX_LINES:]

    def clear(self):
        self.lines.clear()