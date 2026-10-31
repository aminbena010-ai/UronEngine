"""Lógica de edición del Inspector (sin dependencias de Qt)."""
import json

def set_prop_on_objects(objects, comp_type, field, value):
    """Aplica un cambio de propiedad a varios objetos a la vez."""
    for obj in objects:
        comp = obj.get_component(comp_type)
        if comp is not None:
            comp.set(field, value)

def set_enabled_on_objects(objects, comp_type, enabled):
    """Activa o desactiva un componente en varios objetos."""
    for obj in objects:
        comp = obj.get_component(comp_type)
        if comp is not None:
            comp.enabled = bool(enabled)

def set_active_on_objects(objects, active):
    """Activa o desactiva (el GameObject entero) en varios objetos."""
    for obj in objects:
        obj.active = bool(active)

def set_script_prop(comp, name, value):
    """Modifica una propiedad expuesta de un script y la guarda en JSON."""
    try:
        props = json.loads(comp.get("properties_json", "{}"))
    except Exception:
        props = {}
    props[name] = value
    comp.set("properties_json", json.dumps(props))