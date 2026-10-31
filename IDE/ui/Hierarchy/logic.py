"""Operaciones de modelo para la jerarquía (sin dependencias de Qt)."""
from IDE.ui.Hierarchy.config import COMPONENT_PRIORITY


def dominant_component(obj):
    """Devuelve el nombre del componente más importante del objeto para elegir el icono."""
    for t in COMPONENT_PRIORITY:
        if obj.get_component(t) is not None:
            return t
    return "empty"


def list_scripts(project):
    """Devuelve la lista de scripts disponibles en el proyecto."""
    return project.list_scripts() if project is not None else []


def get_object_by_id(scene, object_id):
    """Busca un objeto en la escena por su ID."""
    return scene.find(object_id) if scene else None