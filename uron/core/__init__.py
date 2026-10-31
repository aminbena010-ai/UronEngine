"""Núcleo de URON: utilidades, componentes y modelo de escena (sin dependencias externas)."""

from .util import parse_color, format_color, normalize_color, is_finite
from .components import (
    Field, Component, MissingComponent, Transform,
    SpriteRenderer, Camera, Rotator, PrimitiveRect, PrimitiveCircle, TextRenderer, Container,
    BoxCollider, CircleCollider, RigidBody,
    COMPONENT_REGISTRY, register_component,
)
from .scene import GameObject, Scene
from .project import UronProject, NotAProjectError, ANCHOR_NAME

__all__ = [
    "parse_color", "format_color", "normalize_color", "is_finite",
    "Field", "Component", "MissingComponent", "Transform",
    "SpriteRenderer", "Camera", "Rotator", "PrimitiveRect", "PrimitiveCircle", "TextRenderer", "Container",
    "BoxCollider", "CircleCollider", "RigidBody",
    "COMPONENT_REGISTRY", "register_component",
    "GameObject", "Scene",
    "UronProject", "NotAProjectError", "ANCHOR_NAME",
]