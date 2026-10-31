"""Estado del panel Project (sin dependencias de Qt)."""
import os
from IDE.ui.proyect.config import IMAGE_EXT

class ProjectState:
    """Mantiene el estado lógico del explorador de archivos."""
    
    def __init__(self, project):
        self.project = project
        self.selected_path = None

    def set_selected(self, path):
        self.selected_path = path

    def is_image(self, path):
        """Devuelve True si el archivo es una imagen válida."""
        return bool(path) and path.lower().endswith(IMAGE_EXT)

    def is_scene(self, path):
        """Devuelve True si es una escena de URON."""
        return bool(path) and path.endswith(".uron.json")

    def is_prefab(self, path):
        """Devuelve True si es un prefab de URON."""
        return bool(path) and path.endswith(".uron.prefab")

    def get_assets_dir(self):
        return self.project.sprites_dir() if self.project else ""