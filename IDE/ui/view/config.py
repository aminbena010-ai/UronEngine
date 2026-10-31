"""Configuración visual de la vista de escena."""
from PyQt6.QtGui import QColor

# Colores de los Gizmos (como en Unity/Godot)
COLOR_X     = QColor("#ff5252") # Rojo (Mover X)
COLOR_Y     = QColor("#52ff7a") # Verde (Mover Y)
COLOR_ROT   = QColor("#52a0ff") # Azul (Rotar)
COLOR_SCALE = QColor("#ffd166") # Amarillo (Escalar)

# Tamaños de los Gizmos
AXIS_LENGTH     = 80.0
AXIS_THICKNESS  = 8.0
ROT_RADIUS      = 70.0
ROT_THICKNESS   = 10.0
SCALE_BOX       = 20.0

# Límites de Zoom
ZOOM_MIN = 0.05
ZOOM_MAX = 20.0

# Modos de Gizmo
GIZMO_NONE   = 0
GIZMO_MOVE_X = 1
GIZMO_MOVE_Y = 2
GIZMO_ROTATE = 3
GIZMO_SCALE  = 4