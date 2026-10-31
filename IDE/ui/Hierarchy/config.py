"""Configuración visual y constantes del panel Hierarchy."""

MIME_TYPE = "application/x-uron-gameobject"

# Colores para los iconos según el componente principal
ICON_COLORS = {
    "Container":       "#8b75ff", # Morado
    "SpriteRenderer":  "#4dd0e1", # Cian
    "PrimitiveRect":   "#4dd0e1", # Cian
    "PrimitiveCircle": "#ff7043", # Naranja
    "TextRenderer":    "#ffffff", # Blanco
    "Camera":          "#ffd166", # Amarillo
    "Script":          "#52ff7a", # Verde
    "empty":           "#858585", # Gris
}

# Forma del icono según el componente
ICON_SHAPES = {
    "SpriteRenderer":  "circle",
    "Camera":          "diamond",
    "PrimitiveCircle": "circle",
}

# Prioridad para elegir qué icono mostrar si el objeto tiene varios componentes
COMPONENT_PRIORITY = (
    "Camera", "PrimitiveCircle", "PrimitiveRect", "SpriteRenderer",
    "TextRenderer", "Script", "Container",
)