"""Panel Hierarchy: lista de objetos con iconos, jerarquía y drag & drop."""
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt6.QtGui import QDrag, QIcon, QPixmap, QPainter, QColor, QPolygon
import os

from IDE.ui.Hierarchy.config import MIME_TYPE, ICON_COLORS, ICON_SHAPES
from IDE.ui.Hierarchy.logic import dominant_component

def _make_icon(color_hex, shape="square"):
    pm = QPixmap(14, 14)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(color_hex)
    p.setBrush(c)
    p.setPen(Qt.PenStyle.NoPen)
    if shape == "circle": p.drawEllipse(1, 1, 12, 12)
    elif shape == "diamond": p.drawPolygon(QPolygon([QPoint(7, 1), QPoint(13, 7), QPoint(7, 13), QPoint(1, 7)]))
    else: p.drawRect(2, 2, 10, 10)
    p.end()
    return QIcon(pm)

_ICONS_CACHE = None

def get_icons():
    global _ICONS_CACHE
    if _ICONS_CACHE is None:
        _ICONS_CACHE = {k: _make_icon(v, ICON_SHAPES.get(k, "square")) for k, v in ICON_COLORS.items()}
    return _ICONS_CACHE


class HierarchyPanel(QTreeWidget):
    objectSelected = pyqtSignal(str)
    createEmptyRequested = pyqtSignal()
    createSpriteRequested = pyqtSignal()
    createCameraRequested = pyqtSignal()
    deleteRequested = pyqtSignal(str)
    duplicateRequested = pyqtSignal(str)
    renameRequested = pyqtSignal(str, str)
    addComponentRequested = pyqtSignal(str, str)
    addScriptRequested = pyqtSignal(str, str)
    objectDropped = pyqtSignal(str, str)
    activeToggled = pyqtSignal(str, bool)
    sceneModified = pyqtSignal()

    MIME_TYPE = MIME_TYPE

    def __init__(self, project=None, parent=None):
        super().__init__(parent)
        self.project = project
        self._scene = None
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemChanged.connect(self._on_item_changed)

    def set_project(self, project):
        self.project = project

    def set_scene(self, scene):
        self._scene = scene
        self.blockSignals(True)
        self.clear()
        for obj in scene.get_root_objects():
            self._add_recursive(None, obj)
        self.blockSignals(False)

    def _add_recursive(self, parent_item, obj):
        item = QTreeWidgetItem([obj.name])
        item.setData(0, Qt.ItemDataRole.UserRole, obj.id)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEditable)
        item.setCheckState(0, Qt.CheckState.Checked if obj.active else Qt.CheckState.Unchecked)
        item.setIcon(0, get_icons()[dominant_component(obj)])
        if parent_item is None:
            self.addTopLevelItem(item)
        else:
            parent_item.addChild(item)
            parent_item.setExpanded(True)
        for child in self._scene.children_of(obj.id):
            self._add_recursive(item, child)

    def current_object_id(self):
        item = self.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else None

    def selected_object_ids(self):
        return [i.data(0, Qt.ItemDataRole.UserRole) for i in self.selectedItems() if i.data(0, Qt.ItemDataRole.UserRole)]

    def select_by_id(self, object_id):
        for item in self._all_items():
            if item.data(0, Qt.ItemDataRole.UserRole) == object_id:
                self.blockSignals(True)
                self.setCurrentItem(item)
                self.blockSignals(False)
                return

    def _all_items(self):
        stack = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        while stack:
            item = stack.pop()
            yield item
            stack.extend(item.child(i) for i in range(item.childCount()))

    def _on_selection_changed(self):
        oid = self.current_object_id()
        if oid:
            self.objectSelected.emit(oid)

    def _on_item_changed(self, item, col):
        if col == 0:
            oid = item.data(0, Qt.ItemDataRole.UserRole)
            if oid:
                self.activeToggled.emit(oid, item.checkState(0) == Qt.CheckState.Checked)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F2:
            self._rename_current()
            return
        if event.key() == Qt.Key.Key_Delete:
            for oid in self.selected_object_ids():
                self.deleteRequested.emit(oid)
            return
        super().keyPressEvent(event)

    def _rename_current(self, item=None):
        if item is None:
            item = self.currentItem()
        if item is None:
            return
        oid = item.data(0, Qt.ItemDataRole.UserRole)
        if not oid:
            return
        old = item.text(0)
        new, ok = QInputDialog.getText(self, "Rename", "Name:", text=old)
        if ok and new.strip() and new.strip() != old:
            item.setText(0, new.strip())
            self.renameRequested.emit(oid, new.strip())

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        item = self.itemAt(pos)

        menu.addAction("Create Empty", self.createEmptyRequested.emit)
        menu.addAction("Create Sprite", self.createSpriteRequested.emit)
        menu.addAction("Create Camera", self.createCameraRequested.emit)
        menu.addSeparator()

        if item is not None:
            oid = item.data(0, Qt.ItemDataRole.UserRole)
            menu.addAction("Duplicate", lambda: self.duplicateRequested.emit(oid))
            menu.addAction("Delete", lambda: self.deleteRequested.emit(oid))
            menu.addAction("Rename", lambda: self._rename_current(item))
            menu.addSeparator()

            add_comp = menu.addMenu("Add Component")
            for comp_name in ("SpriteRenderer", "PrimitiveRect", "PrimitiveCircle", "TextRenderer", "Camera", "Rotator", "BoxCollider"):
                add_comp.addAction(comp_name, lambda n=comp_name: self.addComponentRequested.emit(oid, n))
            
            if self.project is not None:
                scripts = self.project.list_scripts()
                if scripts:
                    add_script = menu.addMenu("Add Script")
                    for sf in scripts:
                        add_script.addAction(sf, lambda s=sf, o=oid: self._add_script_direct(o, s))

        menu.exec(self.viewport().mapToGlobal(pos))

    def _add_script_direct(self, object_id, script_path):
        if not self._scene: return
        obj = self._scene.find(object_id)
        if not obj: return
        from uron.api.scripting import ScriptComponent
        comp = ScriptComponent()
        fname = os.path.basename(script_path)
        class_name = "".join(p.capitalize() for p in fname.replace(".py","").split("_"))
        comp.set("path", f"scripts/{fname}")
        comp.set("class_name", class_name)
        obj.add_component(comp)
        self.sceneModified.emit()
        self.addScriptRequested.emit(object_id, script_path)

    def startDrag(self, supported_actions):
        items = self.selectedItems()
        if not items: return
        oid = items[0].data(0, Qt.ItemDataRole.UserRole)
        if not oid: return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self.MIME_TYPE, oid.encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(self.MIME_TYPE):
            source_id = bytes(event.mimeData().data(self.MIME_TYPE)).decode("utf-8")
            target_item = self.itemAt(event.position().toPoint())
            target_id = target_item.data(0, Qt.ItemDataRole.UserRole) if target_item else None
            self.objectDropped.emit(source_id, target_id)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)