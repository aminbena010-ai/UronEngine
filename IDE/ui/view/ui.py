"""Vista de escena 2D con gizmos, cuadrícula y menú contextual."""
import math
import os

from PyQt6.QtWidgets import (
    QMenu, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsItem
)
from PyQt6.QtGui import (
    QBrush, QPen, QColor, QPixmap, QPainter, QTransform, QPolygonF
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal

from uron.render.camera import camera_frame, find_active_camera
from uron.core.util import parse_color
from IDE.logic.tools import Tool

_URON_PROJECT_FOLDER = None

COLOR_X = QColor("#ff5252")
COLOR_Y = QColor("#52ff7a")
COLOR_ROT = QColor("#52a0ff")
COLOR_SCALE = QColor("#ffd166")
AXIS_LENGTH = 80.0
AXIS_THICKNESS = 8.0
ROT_RADIUS = 70.0
ROT_THICKNESS = 10.0
SCALE_BOX = 20.0
ZOOM_MIN = 0.05
ZOOM_MAX = 20.0
GIZMO_NONE = 0
GIZMO_MOVE_X = 1
GIZMO_MOVE_Y = 2
GIZMO_ROTATE = 3
GIZMO_SCALE = 4

def qcolor_from_hex(value, default="#ffffff"):
    r, g, b, a = parse_color(value, parse_color(default))
    return QColor(r, g, b, a)

class SceneObjectItem(QGraphicsRectItem):
    def __init__(self, game_object):
        super().__init__()
        self.game_object = game_object
        self._pixmap = None
        self._updating_from_model = False
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.refresh_from_model()

    def refresh_from_model(self):
        self._updating_from_model = True
        try:
            self._refresh_from_model_impl()
        finally:
            self._updating_from_model = False

    def _refresh_from_model_impl(self):
        tr = self.game_object.transform
        if tr is None: return
        scene, project_folder = _URON_PROJECT_FOLDER, None
        if self.scene() is not None:
            for view in self.scene().views():
                if hasattr(view, "_scene_model"):
                    scene = view._scene_model
                    project_folder = getattr(view, "project_folder", None)
                    break
        if scene is not None:
            world = scene.world_transform(self.game_object)
            pos, scale, rot = [world["world_x"], world["world_y"]], [world["world_scale_x"], world["world_scale_y"]], world["world_rotation"]
        else:
            pos, scale, rot = tr.get("position"), tr.get("scale"), tr.get("rotation")

        is_container = self.game_object.get_component("Container") is not None
        prim_rect = self.game_object.get_component("PrimitiveRect")
        prim_circ = self.game_object.get_component("PrimitiveCircle")
        text_comp = self.game_object.get_component("TextRenderer")
        sprite = self.game_object.get_component("SpriteRenderer")

        if is_container and not sprite and not prim_rect and not prim_circ and not text_comp:
            w, h = 40.0, 40.0
            self.setRect(QRectF(-w/2, -h/2, w, h))
            self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            self.setPen(QPen(QColor("#8b75ff"), 1, Qt.PenStyle.DashLine))
            self._pixmap = None
        elif prim_rect and not sprite:
            size = prim_rect.get("size")
            w, h = max(1.0, float(size[0])), max(1.0, float(size[1]))
            self._pixmap = None
            self.setRect(QRectF(-w/2, -h/2, w, h))
            self.setBrush(QBrush(qcolor_from_hex(prim_rect.get("color", "#4dd0e1"))))
            self.setPen(QPen(QColor("#d8d4ff"), 1))
        elif prim_circ and not sprite:
            r_units = max(1.0, float(prim_circ.get("radius", 50)))
            self._pixmap = None
            self.setRect(QRectF(-r_units, -r_units, r_units*2, r_units*2))
            self.setBrush(QBrush(qcolor_from_hex(prim_circ.get("color", "#ff7043"))))
            self.setPen(QPen(QColor("#d8d4ff"), 1))
        elif text_comp and not sprite and not prim_rect and not prim_circ:
            text, font_size = str(text_comp.get("text", "")), int(text_comp.get("font_size", 24))
            w, h = max(40.0, len(text) * font_size * 0.6), max(30.0, font_size * 1.4)
            self._pixmap = None
            self.setRect(QRectF(-w/2, -h/2, w, h))
            self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            self.setPen(QPen(QColor("#ffd166"), 1, Qt.PenStyle.DashLine))
        elif sprite:
            size = sprite.get("size")
            w, h = max(1.0, float(size[0])), max(1.0, float(size[1]))
            img = sprite.get("image")
            self._pixmap = None
            if img:
                # 1. Si la ruta es relativa, buscamos la carpeta del proyecto
                if not os.path.isabs(img):
                    folder = None
                    
                    # A. Intentar obtenerla de la escena
                    if scene is not None:
                        folder = getattr(scene, "project_folder", None)
                    
                    # B. Si no está, intentar obtenerla del View
                    if not folder and self.scene() and self.scene().views():
                        v = self.scene().views()[0]
                        folder = getattr(v, "project_folder", None)
                        
                    # C. Si aún no está, buscarla subiendo desde la carpeta de escenas
                    if not folder and self.game_object:
                        # Si el objeto pertenece a una escena guardada, su carpeta es la del proyecto
                        pass # Lo resolvemos más abajo
                    
                    # D. Si tenemos carpeta, unimos la ruta
                    if folder:
                        img = os.path.join(folder, img)
                    else:
                        # E. Si nada funciona, usar la ruta absoluta por defecto
                        img = os.path.join("/home/amine/Documentos/Uron/MiJuego", img)
                
                if os.path.isfile(img):
                    pm = QPixmap(img)
                    if not pm.isNull():
                        mode = Qt.TransformationMode.SmoothTransformation if sprite.get("filter") == "Linear" else Qt.TransformationMode.FastTransformation
                        pm = pm.scaled(int(w), int(h), Qt.AspectRatioMode.IgnoreAspectRatio, mode)
                        if sprite.get("flip_x"): pm = pm.transformed(QTransform().scale(-1, 1))
                        if sprite.get("flip_y"): pm = pm.transformed(QTransform().scale(1, -1))
                        self._pixmap = pm
                    else: print(f"[View Debug] Error: PyQt no pudo cargar la imagen: {img}")
                else: print(f"[View Debug] Error: No se encuentra el archivo en: {img}")
            self.setRect(QRectF(-w/2, -h/2, w, h))
            self.setBrush(QBrush(qcolor_from_hex(sprite.get("color", "#ffffff"))))
            self.setPen(QPen(Qt.PenStyle.NoPen) if self._pixmap else QPen(QColor("#d8d4ff"), 1))
        else:
            w, h = 100.0, 70.0
            self._pixmap = None
            self.setRect(QRectF(-w/2, -h/2, w, h))
            self.setBrush(QBrush(QColor("#8b75ff")))
            self.setPen(QPen(QColor("#d8d4ff"), 1))

        self.setTransform(QTransform())
        self.setPos(pos[0], pos[1])
        self.setRotation(rot)
        sx, sy = max(1e-3, abs(scale[0])), max(1e-3, abs(scale[1]))
        if abs(sx - 1.0) > 1e-3 or abs(sy - 1.0) > 1e-3: self.setTransform(QTransform().scale(sx, sy))

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()
        prim_circle = self.game_object.get_component("PrimitiveCircle")
        text_comp = self.game_object.get_component("TextRenderer")
        is_container = self.game_object.get_component("Container") is not None
        if self._pixmap is not None: painter.drawPixmap(rect.toRect(), self._pixmap)
        elif prim_circle is not None: painter.setBrush(self.brush()); painter.setPen(self.pen()); painter.drawEllipse(rect)
        elif text_comp is not None:
            painter.setBrush(QBrush(QColor(40, 40, 50, 200))); painter.setPen(QPen(QColor("#ffd166"), 1, Qt.PenStyle.DashLine)); painter.drawRect(rect)
            painter.setPen(QPen(QColor(text_comp.get("color", "#ffffff"))))
            font = painter.font(); font.setPointSize(max(6, min(48, int(text_comp.get("font_size", 24) / 2)))); painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(text_comp.get("text", "")))
        elif is_container: painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(self.pen()); painter.drawRect(rect)
        else: painter.setBrush(self.brush()); painter.setPen(self.pen()); painter.drawRect(rect)
        if self.isSelected(): painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QColor("#ffd166"), 2)); painter.drawRect(rect)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self._updating_from_model: return value
            tr = self.game_object.transform
            if tr is None: return value
            view = next((v for v in self.scene().views() if hasattr(v, "_scene_model")), None) if self.scene() else None
            wx, wy = float(value.x()), float(value.y())
            if view and getattr(view, "snap_enabled", False):
                wx, wy = round(wx / max(1, view.snap_size)) * view.snap_size, round(wy / max(1, view.snap_size)) * view.snap_size
            model = view._scene_model if view else None
            if model: local = model.world_to_local_point(self.game_object, wx, wy); tr.set("position", [round(local[0], 2), round(local[1], 2)])
            else: tr.set("position", [round(wx, 2), round(wy, 2)])
            if view: view._gizmo_origin = (round(wx, 2), round(wy, 2)); view.viewport().update()
            if abs(wx - value.x()) > 1e-6 or abs(wy - value.y()) > 1e-6:
                self._updating_from_model = True
                try: QGraphicsRectItem.setPos(self, wx, wy)
                except Exception: pass
                finally: self._updating_from_model = False
        return value

class SceneView(QGraphicsView):
    objectSelected = pyqtSignal(str)
    selectionChanged = pyqtSignal(list)
    objectMoved = pyqtSignal(str)
    zoomChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.setBackgroundBrush(QBrush(QColor("#20232b")))
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.items_by_id, self._scene_model, self.project, self.project_folder = {}, None, None, None
        self.current_tool, self.grid_size, self.show_grid, self.snap_enabled, self.snap_size = Tool.SELECT, 32, True, False, 32
        self._panning, self._pan_start, self._space_pan, self._rubber_banding, self._rubber_start, self._rubber_end = False, QPointF(), False, False, QPointF(), QPointF()
        self._gizmo_mode, self._gizmo_start_pos, self._gizmo_start_rot, self._gizmo_start_scale, self._gizmo_start_obj_pos, self._gizmo_start_angle = GIZMO_NONE, QPointF(), 0.0, [1.0, 1.0], [0.0, 0.0], 0.0
        self._gizmo_origin, self._gizmo_selected_obj, self._gizmo_game_object = (0.0, 0.0), None, None
        self._selection_locked = False
        self.setAcceptDrops(True)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        if not self.show_grid or self.grid_size <= 0: return
        g = self.grid_size; left = int(math.floor(rect.left() / g)) * g; top = int(math.floor(rect.top() / g)) * g
        painter.setPen(QPen(QColor(255, 255, 255, 18), 0))
        x = left
        while x < rect.right(): painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom())); x += g
        y = top
        while y < rect.bottom(): painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y)); y += g
        painter.setPen(QPen(QColor(220, 90, 90, 140), 0)); painter.drawLine(QPointF(0, rect.top()), QPointF(0, rect.bottom()))
        painter.setPen(QPen(QColor(90, 220, 90, 140), 0)); painter.drawLine(QPointF(rect.left(), 0), QPointF(rect.right(), 0))

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        if self._scene_model:
            selected = self._scene_model.find(self.selected_object_id()) if self.selected_object_id() else None
            cam_obj = selected if selected and selected.get_component("Camera") else find_active_camera(self._scene_model)
            if cam_obj:
                info = camera_frame(self._scene_model, self.viewport().width() / max(1, self.viewport().height()))
                unit = 1.0 / (abs(self.transform().m11()) or 1.0)
                painter.save(); painter.translate(info["x"], info["y"]); painter.rotate(info["rotation"])
                painter.setBrush(QBrush(QColor(*info["background"][:3], 40)))
                painter.setPen(QPen(QColor(255, 209, 102, 190), max(1.0, unit), Qt.PenStyle.DashLine))
                painter.drawRect(QRectF(-info["width"]/2, -info["height"]/2, info["width"], info["height"])); painter.restore()

        if self._rubber_banding:
            band = QRectF(self._rubber_start, self._rubber_end).normalized(); painter.save()
            painter.setBrush(QBrush(QColor(82, 160, 255, 45))); painter.setPen(QPen(QColor("#52a0ff"), 1, Qt.PenStyle.DashLine))
            painter.drawRect(band); painter.restore()

        obj, go = self._gizmo_selected_obj, self._gizmo_game_object
        if not obj or not go: return
        if self._scene_model: world = self._scene_model.world_transform(go); ox, oy = world["world_x"], world["world_y"]
        else: pos = obj.get("position"); ox, oy = pos[0], pos[1]
        if self._gizmo_mode != GIZMO_NONE: ox, oy = self._gizmo_origin
        unit = 1.0 / (abs(self.transform().m11()) or 1.0)
        painter.save(); painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setPen(QPen(COLOR_X, AXIS_THICKNESS * unit / 4)); painter.setBrush(QBrush(COLOR_X)); painter.drawLine(QPointF(ox, oy), QPointF(ox + AXIS_LENGTH*unit, oy))
        painter.setPen(QPen(COLOR_Y, AXIS_THICKNESS * unit / 4)); painter.setBrush(QBrush(COLOR_Y)); painter.drawLine(QPointF(ox, oy), QPointF(ox, oy - AXIS_LENGTH*unit))
        painter.setPen(QPen(COLOR_ROT, ROT_THICKNESS * unit / 4)); painter.setBrush(Qt.BrushStyle.NoBrush); painter.drawEllipse(QPointF(ox, oy), ROT_RADIUS*unit, ROT_RADIUS*unit)
        painter.setPen(QPen(COLOR_SCALE, max(1.0, 2 * unit))); painter.setBrush(QBrush(COLOR_SCALE)); painter.drawRect(QRectF(ox + AXIS_LENGTH*unit - SCALE_BOX*unit/2, oy - SCALE_BOX*unit/2, SCALE_BOX*unit, SCALE_BOX*unit))
        painter.restore()

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15; current = abs(self.transform().m11()) or 1.0
        factor = max(ZOOM_MIN, min(ZOOM_MAX, current * factor)) / current
        if abs(factor - 1.0) > 1e-9: self.scale(factor, factor)
        self.zoomChanged.emit(abs(self.transform().m11())); event.accept()

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton) or (event.button() == Qt.MouseButton.LeftButton and self._space_pan):
            self._panning = True; self._pan_start = event.position(); self.setCursor(Qt.CursorShape.ClosedHandCursor); event.accept(); return
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            if self._gizmo_selected_obj:
                ox, oy = (self._scene_model.world_transform(self._gizmo_game_object)["world_x"], self._scene_model.world_transform(self._gizmo_game_object)["world_y"]) if self._scene_model else self._gizmo_selected_obj.get("position")
                unit = 1.0 / (abs(self.transform().m11()) or 1.0)
                if ox <= scene_pos.x() <= ox + AXIS_LENGTH*unit and abs(scene_pos.y() - oy) <= (AXIS_THICKNESS/2+3)*unit: self._gizmo_mode = GIZMO_MOVE_X
                elif oy - AXIS_LENGTH*unit <= scene_pos.y() <= oy and abs(scene_pos.x() - ox) <= (AXIS_THICKNESS/2+3)*unit: self._gizmo_mode = GIZMO_MOVE_Y
                elif abs(math.hypot(scene_pos.x() - ox, scene_pos.y() - oy) - ROT_RADIUS*unit) <= (ROT_THICKNESS/2+4)*unit: self._gizmo_mode = GIZMO_ROTATE
                elif abs(scene_pos.x() - (ox + AXIS_LENGTH*unit)) <= SCALE_BOX*unit/2 and abs(scene_pos.y() - oy) <= SCALE_BOX*unit/2: self._gizmo_mode = GIZMO_SCALE
                if self._gizmo_mode != GIZMO_NONE:
                    self._gizmo_start_pos = scene_pos; self._gizmo_origin = (ox, oy)
                    pos = self._gizmo_selected_obj.get("position"); self._gizmo_start_obj_pos = [pos[0], pos[1]]
                    self._gizmo_start_rot, self._gizmo_start_scale = self._gizmo_selected_obj.get("rotation"), list(self._gizmo_selected_obj.get("scale"))
                    self._gizmo_start_angle = math.atan2(scene_pos.y() - oy, scene_pos.x() - ox); event.accept(); return

            item = self._scene.itemAt(scene_pos, self.transform())
            if item and isinstance(item, SceneObjectItem):
                if not (event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                    self._scene.clearSelection(); item.setSelected(True)
                elif event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier): item.setSelected(not item.isSelected())
                self._on_selection_changed(); super().mousePressEvent(event); return
            if not (event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                self._scene.clearSelection(); self._on_selection_changed()
            self._rubber_banding, self._rubber_start, self._rubber_end = True, scene_pos, scene_pos
            self.viewport().update(); event.accept(); return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position() - self._pan_start; self._pan_start = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept(); return
        if self._rubber_banding:
            self._rubber_end = self.mapToScene(event.position().toPoint()); self.viewport().update(); event.accept(); return
        if self._gizmo_mode != GIZMO_NONE and self._gizmo_selected_obj:
            scene_pos = self.mapToScene(event.position().toPoint())
            def sn(v): return round(v / self.snap_size) * self.snap_size if self.snap_enabled and self.snap_size > 0 else v
            if self._gizmo_mode == GIZMO_MOVE_X:
                dx = scene_pos.x() - self._gizmo_start_pos.x(); wx = sn(self._gizmo_origin[0] + dx); wy = self._gizmo_origin[1]
                local = self._scene_model.world_to_local_point(self._gizmo_game_object, wx, wy) if self._scene_model else [wx, wy]
                self._gizmo_selected_obj.set("position", [round(local[0], 2), round(local[1], 2)])
            elif self._gizmo_mode == GIZMO_MOVE_Y:
                dy = scene_pos.y() - self._gizmo_start_pos.y(); wx = self._gizmo_origin[0]; wy = sn(self._gizmo_origin[1] + dy)
                local = self._scene_model.world_to_local_point(self._gizmo_game_object, wx, wy) if self._scene_model else [wx, wy]
                self._gizmo_selected_obj.set("position", [round(local[0], 2), round(local[1], 2)])
            elif self._gizmo_mode == GIZMO_ROTATE:
                ox, oy = self._gizmo_origin; ang = math.atan2(scene_pos.y() - oy, scene_pos.x() - ox); delta = math.degrees(ang - self._gizmo_start_angle)
                val = self._gizmo_start_rot + delta
                if self.snap_enabled: step = 15.0 if self.snap_size <= 64 else 45.0; val = round(val / step) * step
                self._gizmo_selected_obj.set("rotation", round(val, 2) % 360.0)
            elif self._gizmo_mode == GIZMO_SCALE:
                ox, oy = self._gizmo_origin; sd = math.hypot(self._gizmo_start_pos.x() - ox, self._gizmo_start_pos.y() - oy); cd = math.hypot(scene_pos.x() - ox, scene_pos.y() - oy)
                factor = max(0.05, min(20.0, cd / max(1e-3, sd)))
                self._gizmo_selected_obj.set("scale", [round(self._gizmo_start_scale[0] * factor, 3), round(self._gizmo_start_scale[1] * factor, 3)])
            oid = self._gizmo_game_object.id if self._gizmo_game_object else None
            if oid in self.items_by_id: self.items_by_id[oid].refresh_from_model()
            self.viewport().update(); event.accept(); return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning: self._panning = False; self.setCursor(Qt.CursorShape.OpenHandCursor if self._space_pan else Qt.CursorShape.ArrowCursor); event.accept(); return
        if event.button() == Qt.MouseButton.LeftButton and self._rubber_banding:
            band = QRectF(self._rubber_start, self._rubber_end).normalized(); self._rubber_banding = False
            if band.width() >= 2 or band.height() >= 2:
                if not (event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)): self._scene.clearSelection()
                for item in self._scene.items(band, Qt.ItemSelectionMode.IntersectsItemShape):
                    if isinstance(item, SceneObjectItem): item.setSelected(True)
            self._on_selection_changed(); self.viewport().update(); event.accept(); return
        if event.button() == Qt.MouseButton.LeftButton and self._gizmo_mode != GIZMO_NONE:
            self._gizmo_mode = GIZMO_NONE; self._on_selection_changed(); event.accept(); return
        super().mouseReleaseEvent(event)

    def add_game_object(self, go):
        item = SceneObjectItem(go); self._scene.addItem(item); self.items_by_id[go.id] = item; return item
    def remove_game_object(self, oid):
        item = self.items_by_id.pop(oid, None)
        if item: self._scene.removeItem(item)
    def clear_objects(self):
        self._scene.clear(); self.items_by_id.clear(); self._gizmo_selected_obj = None; self._gizmo_game_object = None
    def refresh_item(self, go):
        item = self.items_by_id.get(go.id)
        if item: item.refresh_from_model()
        if go.transform is self._gizmo_selected_obj: self.viewport().update()
    def refresh_all(self):
        for item in self.items_by_id.values(): item.refresh_from_model()
    def selected_object_id(self):
        ids = self.selected_object_ids(); return ids[0] if ids else None
    def selected_object_ids(self):
        try: return [i.game_object.id for i in self._scene.selectedItems() if isinstance(i, SceneObjectItem)]
        except RuntimeError: return []
    def select_object(self, oid): self.select_objects([oid] if oid else [])
    def select_objects(self, oids):
        self._scene.clearSelection()
        for oid in set(oids or []):
            if oid in self.items_by_id: self.items_by_id[oid].setSelected(True)
        self._on_selection_changed()
    def _on_selection_changed(self):
        if getattr(self, "_selection_locked", False): return
        self._selection_locked = True
        try:
            sel = [i for i in self._scene.selectedItems() if isinstance(i, SceneObjectItem)]
        except RuntimeError:
            sel = []
        if sel:
            obj = sel[0].game_object; self._gizmo_selected_obj, self._gizmo_game_object = obj.transform, obj
            try: self.objectSelected.emit(obj.id); self.selectionChanged.emit([i.game_object.id for i in sel])
            except Exception: pass
        else:
            self._gizmo_selected_obj, self._gizmo_game_object = None, None
            try: self.selectionChanged.emit([])
            except Exception: pass
        self.viewport().update()
        self._selection_locked = False
    def set_scene_model(self, m): self._scene_model = m
    def set_project(self, p): self.project = p; self.project_folder = p.folder if p else None
    def set_tool(self, t): self.current_tool = t
    def set_grid_visible(self, v): self.show_grid = bool(v); self.viewport().update()
    def set_grid_size(self, s): self.grid_size = max(1, int(s)); self.viewport().update()
    def set_snap_enabled(self, v): self.snap_enabled = bool(v)
    def set_snap_size(self, s): self.snap_size = max(1, int(s))
    def reset_zoom(self): self.resetTransform(); self.zoomChanged.emit(abs(self.transform().m11()))
    def zoom_to_fit(self):
        b = self._scene.itemsBoundingRect()
        if not b.isNull(): self.fitInView(b.adjusted(-40, -40, 40, 40), Qt.AspectRatioMode.KeepAspectRatio); self.zoomChanged.emit(abs(self.transform().m11()))
    def focus_object(self, oid):
        item = self.items_by_id.get(oid)
        if item: self.centerOn(item)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pan = True
            if not self._panning: self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept(); return
        super().keyPressEvent(event)
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pan = False
            if not self._panning: self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept(); return
        super().keyReleaseEvent(event)
