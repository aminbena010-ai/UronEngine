"""Ventana principal del IDE URON (MainWindow). Ensambla los paneles y conecta señales."""
import os
import copy
import json

from PyQt6.QtWidgets import (
    QDialog, QMainWindow, QDockWidget, QStatusBar, QToolBar, QMessageBox, QLabel, QFileDialog, QInputDialog
)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt

from uron.core.project import UronProject
from uron.core.scene import Scene, GameObject
from uron.core.version import ENGINE_VERSION
from uron.core.components import (
    SpriteRenderer, Camera, Rotator, PrimitiveRect, PrimitiveCircle,
    TextRenderer, Container, BoxCollider, CircleCollider, RigidBody
)

# Paneles de la UI
from IDE.ui.Hierarchy import HierarchyPanel
from IDE.ui.Inspector import Inspector
from IDE.ui.proyect import ProjectPanel
from IDE.ui.view import SceneView
from IDE.ui.console import ConsolePanel
from IDE.ui.preferences import PreferencesDialog
from IDE.ui.build_dialog import BuildDialog

# Lógica del editor
from IDE.logic import Tool, UndoStack, PlayMode, recent
from IDE.ui.theme import ACCENT_GREEN


class MainWindow(QMainWindow):
    def __init__(self, project: UronProject):
        super().__init__()
        self.project = project
        self.scene = Scene("Main Scene")
        self.undo = UndoStack(self.scene)
        self.play_mode = PlayMode(self)
        
        self.current_scene_path = None
        self._current_object_id = None
        self._selected_ids = []
        self._clipboard = None

        self.setWindowTitle(f"URON Engine {ENGINE_VERSION} — {project.name}")
        self.resize(1440, 900)

        self.view = SceneView()
        self.view.set_project(project)
        self.hierarchy = HierarchyPanel(project)
        self.inspector = Inspector()
        self.inspector.set_project(project)
        self.project_panel = ProjectPanel(project)
        self.console = ConsolePanel()

        self.setCentralWidget(self.view)
        self._dock("Hierarchy", self.hierarchy, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._dock("Inspector", self.inspector, Qt.DockWidgetArea.RightDockWidgetArea)
        self._dock("Project", self.project_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._dock("Console", self.console, Qt.DockWidgetArea.BottomDockWidgetArea)

        self.setStatusBar(QStatusBar())
        self._zoom_label = QLabel("100%")
        self.statusBar().addPermanentWidget(self._zoom_label)

        self._build_toolbar()
        self._build_menus()
        self._connect_signals()

        main_path = project.main_scene_path()
        if os.path.isfile(main_path):
            self._load_scene(main_path)
        else:
            self.current_scene_path = main_path
            self.hierarchy.set_scene(self.scene)
            self.view.set_scene_model(self.scene)

        self.log(f"Project opened: {project.folder}")

    def _dock(self, title, widget, area):
        d = QDockWidget(title, self)
        d.setWidget(widget)
        d.setObjectName(title)
        self.addDockWidget(area, d)
        return d

    def _build_toolbar(self):
        tb = QToolBar("Main Tools")
        tb.setMovable(False)
        self.addToolBar(tb)

        self.act_play = QAction("▶", self)
        self.act_play.setToolTip("Play (F5)")
        self.act_play.triggered.connect(self.toggle_play)
        self.act_pause = QAction("❚❚", self)
        self.act_pause.setToolTip("Pause (F6)")
        self.act_pause.triggered.connect(self.pause_play)
        self.act_pause.setEnabled(False)
        self.act_stop = QAction("■", self)
        self.act_stop.setToolTip("Stop (Shift+F5)")
        self.act_stop.triggered.connect(self.stop_play)
        self.act_stop.setEnabled(False)

        def add_styled_action(action, color=None):
            tb.addAction(action)
            btn = tb.widgetForAction(action)
            if btn and color:
                btn.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold; border: none; padding: 0 10px;")
        
        add_styled_action(self.act_play, ACCENT_GREEN)
        add_styled_action(self.act_pause)
        add_styled_action(self.act_stop)
        
        tb.addSeparator()
        tb.addAction("＋ Empty", self.create_empty)
        tb.addAction("Save Scene", self.save_scene)
        tb.addSeparator()
        for tool in (Tool.SELECT, Tool.MOVE, Tool.ROTATE, Tool.SCALE):
            act = QAction(tool.label, self)
            act.setShortcut(QKeySequence(tool.shortcut))
            act.triggered.connect(lambda _, t=tool: self._set_tool(t))
            tb.addAction(act)

    def _build_menus(self):
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("New Scene", self.new_scene)
        open_act = QAction("Open Scene…", self)
        open_act.setShortcut(QKeySequence("Ctrl+O"))
        open_act.triggered.connect(self.open_scene)
        file_menu.addAction(open_act)
        save_act = QAction("Save Scene", self)
        save_act.setShortcut(QKeySequence("Ctrl+S"))
        save_act.triggered.connect(self.save_scene)
        file_menu.addAction(save_act)
        file_menu.addSeparator()
        file_menu.addAction("Preferences…", self.open_preferences)
        file_menu.addAction("Build Game…", self.build_game)

        edit_menu = self.menuBar().addMenu("&Edit")
        undo_act = QAction("Undo", self)
        undo_act.setShortcut(QKeySequence("Ctrl+Z"))
        undo_act.triggered.connect(self.do_undo)
        edit_menu.addAction(undo_act)
        redo_act = QAction("Redo", self)
        redo_act.setShortcut(QKeySequence("Ctrl+Y"))
        redo_act.triggered.connect(self.do_redo)
        edit_menu.addAction(redo_act)
        edit_menu.addSeparator()
        dup_act = QAction("Duplicate", self)
        dup_act.setShortcut(QKeySequence("Ctrl+D"))
        dup_act.triggered.connect(self.duplicate_selected)
        edit_menu.addAction(dup_act)
        del_act = QAction("Delete", self)
        del_act.setShortcut(QKeySequence("Delete"))
        del_act.triggered.connect(self.delete_selected)
        edit_menu.addAction(del_act)

    def _connect_signals(self):
        self.hierarchy.objectSelected.connect(self._on_select)
        self.hierarchy.deleteRequested.connect(self._delete_by_id)
        self.hierarchy.duplicateRequested.connect(self._duplicate_by_id)
        self.hierarchy.renameRequested.connect(self._rename_by_id)
        self.hierarchy.activeToggled.connect(self._on_active_toggled)
        self.hierarchy.addComponentRequested.connect(self._add_component_by_id)
        self.hierarchy.objectDropped.connect(self._on_reparent)
        self.hierarchy.sceneModified.connect(self.inspector.refresh)
        self.inspector.changed.connect(self._on_inspector_changed)
        self.view.objectSelected.connect(self._on_select)
        self.view.objectMoved.connect(self._on_moved)
        self.view.zoomChanged.connect(lambda z: self._zoom_label.setText(f"{z*100:.0f}%"))
        self.project_panel.sceneRequested.connect(self._load_scene)
        self.project_panel.assetRequested.connect(self._use_asset)
        self.play_mode.output.connect(self.log)
        self.play_mode.stateChanged.connect(self._on_play_state_changed)

    def _load_scene(self, path):
        try:
            self.scene = Scene.load(path)
            self.current_scene_path = path
            self.scene.project_folder = self.project.folder
            self.view.set_project(self.project)
            self.view.set_scene_model(self.scene)
            self.view.clear_objects()
            for o in self.scene.objects:
                self.view.add_game_object(o)
            self.hierarchy.set_scene(self.scene)
            self.inspector.show_object(None)
            self.undo.scene_ref = self.scene
            self.undo.initial_state()
            self.log(f"Loaded: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_select(self, oid):
        if not oid: return
        self._current_object_id = oid
        obj = self.scene.find(oid)
        self.inspector.show_object(obj)
        self.hierarchy.select_by_id(oid)
        self.view.select_object(oid)

    def _on_inspector_changed(self):
        if self._current_object_id:
            obj = self.scene.find(self._current_object_id)
            if obj:
                self.view.refresh_item(obj)
                self.hierarchy.set_scene(self.scene)
                self.undo.push(force=True)

    def _on_moved(self, oid):
        self.undo.push(force=True)
        if self.inspector._current and self.inspector._current.id == oid:
            self.inspector.refresh()

    def _on_active_toggled(self, oid, active):
        obj = self.scene.find(oid)
        if obj and obj.active != active:
            obj.active = active
            self.view.refresh_item(obj)
            self.undo.push(force=True)

    def _on_reparent(self, src_id, dst_id):
        if self.scene.reparent(src_id, dst_id):
            self.undo.push(force=True)
            self.hierarchy.set_scene(self.scene)
            self.view.clear_objects()
            for o in self.scene.objects:
                self.view.add_game_object(o)

    def create_empty(self):
        o = self.scene.create_object(f"GameObject {len(self.scene.objects) + 1}")
        self.view.add_game_object(o)
        self.hierarchy.set_scene(self.scene)
        self.undo.push(force=True)
        self._on_select(o.id)

    def _delete_by_id(self, oid):
        o = self.scene.find(oid)
        if not o: return
        self.scene.remove_object(oid)
        self.view.clear_objects()
        for obj in self.scene.objects:
            self.view.add_game_object(obj)
        self.hierarchy.set_scene(self.scene)
        self.inspector.show_object(None)
        self.undo.push(force=True)
        self.log(f"Deleted {o.name}")

    def delete_selected(self):
        if self._current_object_id:
            self._delete_by_id(self._current_object_id)

    def _duplicate_by_id(self, oid):
        src = self.scene.find(oid)
        if not src: return
        clone = src.clone(new_name=f"{src.name}_copy")
        self.scene.add_object(clone)
        self.view.add_game_object(clone)
        self.hierarchy.set_scene(self.scene)
        self._on_select(clone.id)
        self.undo.push(force=True)

    def duplicate_selected(self):
        if self._current_object_id:
            self._duplicate_by_id(self._current_object_id)

    def _rename_by_id(self, oid, new_name):
        o = self.scene.find(oid)
        if o:
            o.name = new_name
            self.hierarchy.set_scene(self.scene)
            self.undo.push(force=True)

    def _add_component_by_id(self, oid, comp_type):
        o = self.scene.find(oid)
        if not o: return
        mapping = {
            "SpriteRenderer": SpriteRenderer, "Camera": Camera, "Rotator": Rotator,
            "PrimitiveRect": PrimitiveRect, "PrimitiveCircle": PrimitiveCircle,
            "TextRenderer": TextRenderer, "Container": Container,
            "BoxCollider": BoxCollider, "CircleCollider": CircleCollider,
            "RigidBody": RigidBody,
        }
        cls = mapping.get(comp_type)
        if cls:
            o.add_component(cls())
            self.inspector.refresh()
            self.view.refresh_item(o)
            self.undo.push(force=True)

    def _use_asset(self, path):
        if not self._current_object_id: return
        o = self.scene.find(self._current_object_id)
        if not o: return
        sprite = o.get_component("SpriteRenderer")
        if not sprite:
            sprite = o.add_component(SpriteRenderer())
        try:
            rel = os.path.relpath(path, self.project.folder).replace(os.sep, "/")
        except ValueError:
            rel = path
        sprite.set("image", rel)
        self.view.refresh_item(o)
        self.inspector.refresh()
        self.undo.push(force=True)
        self.log(f"Sprite assigned to {o.name}")

    def _set_tool(self, tool):
        self.statusBar().showMessage(f"Tool: {tool.label}", 2000)

    def save_scene(self):
        if not self.current_scene_path:
            return
        try:
            self.scene.make_portable(self.project.folder)
            self.scene.save(self.current_scene_path)
            self.log("Scene saved.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def do_undo(self):
        if self.undo.undo():
            self._refresh_all_ui()
            self.log("Undo")
    def do_redo(self):
        if self.undo.redo():
            self._refresh_all_ui()
            self.log("Redo")

    def _refresh_all_ui(self):
        self.view.clear_objects()
        for o in self.scene.objects:
            self.view.add_game_object(o)
        self.hierarchy.set_scene(self.scene)
        self.inspector.show_object(self.scene.find(self._current_object_id) if self._current_object_id else None)

    def log(self, msg):
        self.console.log(msg)

    def toggle_play(self):
        if self.play_mode.is_running():
            self.stop_play()
        else:
            self.save_scene()
            if self.current_scene_path:
                self.play_mode.start(self.current_scene_path, self.project)

    def pause_play(self):
        if self.play_mode.state == "paused":
            self.play_mode.resume()
        else:
            self.play_mode.pause()

    def stop_play(self):
        self.play_mode.stop()

    def _on_play_state_changed(self, state):
        running = state in ("running", "paused")
        self.act_play.setEnabled(not running)
        self.act_pause.setEnabled(running)
        self.act_stop.setEnabled(running)
        self.act_play.setText("●" if running else "▶")
        self.statusBar().showMessage(f"Play mode: {state}")

    def new_scene(self):
        name, ok = QInputDialog.getText(self, "New Scene", "Scene name:")
        if ok and name.strip():
            try:
                path = self.project.create_scene(name.strip() + ".uron.json")
                self.project_panel.reload()
                self._load_scene(path)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def open_scene(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Scene", self.project.scenes_dir(), "URON Scene (*.uron.json)")
        if path:
            self._load_scene(path)

    def open_preferences(self):
        editor_cfg = self.project.load_editor_cfg()
        settings = self.project.load_settings()
        keybinds = self.project.load_keybinds()
        dialog = PreferencesDialog(self.project, editor_cfg, settings, keybinds, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.values()
            editor_cfg["grid"] = values["editor_cfg"]["grid"]
            editor_cfg["snap"] = values["editor_cfg"]["snap"]
            self.project.save_editor_cfg(editor_cfg)
            settings["window"] = values["settings"]["window"]
            settings["runtime"] = values["settings"]["runtime"]
            self.project.save_settings(settings)
            keybinds = values["keybinds"]
            with open(os.path.join(self.project.cfg_dir(), "keybinds.cfg"), "w") as f:
                json.dump(keybinds, f, indent=2)
            self.view.set_grid_size(editor_cfg["grid"]["size"])
            self.view.set_grid_visible(editor_cfg["grid"]["visible"])
            self.view.set_snap_enabled(editor_cfg["snap"]["enabled"])
            self.view.set_snap_size(editor_cfg["snap"]["size"])
            self.log("Preferences saved.")
        else:
            self.log("Preferences cancelled.")

    def build_game(self):
        dialog = BuildDialog(self.project, self)
        dialog.exec()