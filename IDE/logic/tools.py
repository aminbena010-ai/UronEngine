"""Herramientas del editor. Cambian el modo de interacción del ratón en la vista."""
from enum import Enum

class Tool(Enum):
    SELECT = "select"
    MOVE = "move"
    ROTATE = "rotate"
    SCALE = "scale"

    @property
    def label(self):
        return {
            Tool.SELECT: "Select",
            Tool.MOVE: "Move",
            Tool.ROTATE: "Rotate",
            Tool.SCALE: "Scale",
        }[self]

    @property
    def shortcut(self):
        return {
            Tool.SELECT: "Q",
            Tool.MOVE: "W",
            Tool.ROTATE: "E",
            Tool.SCALE: "R",
        }[self]