"""Estado del panel Hierarchy (sin dependencias de Qt)."""

class HierarchyState:
    """Mantiene el estado lógico de la jerarquía."""
    def __init__(self, project=None):
        self.project = project
        self.scene = None
        self.selected_id = None

    def set_project(self, project):
        self.project = project

    def set_scene(self, scene):
        self.scene = scene

    def set_selected(self, object_id):
        self.selected_id = object_id

    def roots(self):
        """Devuelve los objetos raíz (sin padre)."""
        return self.scene.get_root_objects() if self.scene else []

    def children_of(self, object_id):
        """Devuelve los hijos directos de un objeto."""
        return self.scene.children_of(object_id) if self.scene else []