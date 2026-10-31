"""Estado del Inspector (sin dependencias de Qt)."""

class InspectorState:
    """Mantiene el estado lógico de los objetos seleccionados."""
    
    def __init__(self, project=None):
        self.project = project
        self.current_objects = []
        self.current = None

    def set_project(self, project):
        self.project = project

    def set_objects(self, objects):
        """Establece la lista de objetos seleccionados."""
        self.current_objects = [o for o in (objects or []) if o is not None]
        self.current = self.current_objects[0] if self.current_objects else None

    def is_multi(self):
        """Devuelve True si hay más de un objeto seleccionado."""
        return len(self.current_objects) > 1

    def common_components(self):
        """Devuelve los componentes que comparten todos los objetos seleccionados."""
        if not self.current_objects:
            return set()
        sets = [{c.type_name for c in o.components if c.type_name != "Transform"}
                for o in self.current_objects]
        common = sets[0]
        for s in sets[1:]:
            common &= s
        return common