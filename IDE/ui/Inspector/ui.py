"""Inspector generado dinámicamente con estilo colapsable."""
import json
import os
import subprocess

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QDoubleSpinBox, QSpinBox, QCheckBox, QComboBox,
    QPushButton, QLabel, QFileDialog, QScrollArea, QDialog,
    QListWidget, QListWidgetItem, QDialogButtonBox, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt

from IDE.ui.Inspector.config import IMAGE_EXT, SCRIPT_EDITORS, HIDDEN_COMPONENTS
from IDE.ui.Inspector.logic import (
    set_prop_on_objects, set_enabled_on_objects, set_active_on_objects, set_script_prop
)
from IDE.ui.theme import BG_INPUT

def _to_rel_path(path, project):
    if not path or not project: return path
    if os.path.isabs(path):
        try:
            rel = os.path.relpath(path, project.folder).replace(os.sep, "/")
            if not rel.startswith(".."): return rel
        except ValueError: pass
    return path

class AddComponentDialog(QDialog):
    def __init__(self, component_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Component")
        self.setMinimumSize(360, 420)
        self._selected = None
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search components…")
        layout.addWidget(self.search)
        self.list = QListWidget()
        for name in component_names:
            QListWidgetItem(name, self.list)
        layout.addWidget(self.list, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.search.textChanged.connect(self._filter)
        self.list.itemDoubleClicked.connect(lambda _: self._accept())

    def _filter(self, text):
        text = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(text) and text not in item.text().lower())

    def _accept(self):
        item = self.list.currentItem()
        if item is None or item.isHidden(): return
        self._selected = item.text()
        self.accept()

    def selected_component(self):
        return self._selected


class Inspector(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        outer.addWidget(self._scroll)
        
        self._content = QWidget()
        self._scroll.setWidget(self._content)
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(8)
        
        self._current = None
        self._current_list = []
        self._project = None
        self._building = False
        self._show_placeholder("No object selected")

    def set_project(self, project):
        self._project = project

    def show_object(self, game_object):
        self.show_objects([game_object] if game_object is not None else [])

    def show_objects(self, game_objects):
        self.clear()
        objects = [o for o in (game_objects or []) if o is not None]
        self._current_list = objects
        self._current = objects[0] if objects else None
        if not objects:
            self._show_placeholder("No object selected")
            return

        self._building = True
        multi = len(objects) > 1
        
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 10)
        
        name_edit = QLineEdit("(multiple)" if multi else objects[0].name)
        name_edit.setEnabled(not multi)
        name_edit.editingFinished.connect(lambda: self._commit_name(name_edit))
        
        active = QCheckBox()
        active.setTristate(len({bool(o.active) for o in objects}) > 1)
        active.setChecked(objects[0].active)
        active.toggled.connect(self._set_active)
        
        h_layout.addWidget(QLabel("Name:"))
        h_layout.addWidget(name_edit, 1)
        h_layout.addWidget(QLabel("Active:"))
        h_layout.addWidget(active)
        self._layout.addWidget(header)

        common = None
        for obj in objects:
            types = {c.type_name for c in obj.components if c.type_name != "Transform"}
            common = types if common is None else (common & types)
        common = common or set()

        for comp in objects[0].components:
            if comp.type_name == "Transform" or comp.type_name in common:
                self._build_component_group(comp)

        add_btn = QPushButton("Add Component")
        add_btn.setStyleSheet(f"background-color: {BG_INPUT}; font-weight: bold; padding: 8px; border: 1px solid #3e3e42;")
        add_btn.clicked.connect(self._open_add_component)
        self._layout.addSpacing(10)
        self._layout.addWidget(add_btn)
        self._layout.addStretch()
        self._building = False

    def refresh(self):
        self.show_objects(self._current_list)

    def clear(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _show_placeholder(self, text):
        self._building = True
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #858585; font-style: italic;")
        self._layout.addWidget(label)
        self._layout.addStretch()
        self._building = False

    def _build_component_group(self, comp):
        if comp.type_name == "Script":
            return self._build_script_group(comp)
        
        group = QGroupBox(comp.type_name)
        group.setCheckable(True)
        group.setChecked(True)
        
        def toggle_group(checked):
            for i in range(group.layout().count()):
                w = group.layout().itemAt(i).widget()
                if w: w.setVisible(checked)
        group.toggled.connect(toggle_group)
        
        form = QFormLayout(group)
        form.setSpacing(10)

        if comp.type_name != "Transform":
            enabled = QCheckBox()
            enabled.setChecked(comp.enabled)
            enabled.toggled.connect(lambda v, c=comp: self._set_enabled(c, v))
            form.addRow("Enabled", enabled)

        for field in comp.fields:
            try:
                widget = self._make_widget(comp, field)
            except Exception:
                widget = None
            if widget is not None:
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                form.addRow(field.title, widget)

        if comp.removable:
            btn = QPushButton("Remove Component")
            btn.setStyleSheet("color: #e74c3c; border: none; background: transparent; text-align: left;")
            btn.clicked.connect(lambda _, c=comp: self._remove_component(c))
            form.addRow(btn)

        self._layout.addWidget(group)

    def _build_script_group(self, comp):
        group = QGroupBox("Script")
        form = QFormLayout(group)

        project = getattr(self, "_project", None)
        script_files = project.list_scripts() if project else []

        dropdown = QComboBox()
        dropdown.addItem("(none)", "")
        for f in script_files:
            dropdown.addItem(f, f)
        
        current_path = comp.get("path", "")
        if current_path:
            current_name = os.path.basename(current_path)
            for i in range(dropdown.count()):
                if dropdown.itemData(i) == current_name:
                    dropdown.setCurrentIndex(i)
                    break

        def on_changed(_):
            rel = dropdown.currentData()
            if not rel: return
            class_name = os.path.splitext(os.path.basename(rel))[0]
            class_name = "".join(part.capitalize() for part in class_name.split("_"))
            comp.set("path", f"scripts/{rel}")
            comp.set("class_name", class_name)
            comp.set("properties_json", "{}")
            self.refresh()
            self.changed.emit()

        dropdown.currentIndexChanged.connect(on_changed)
        form.addRow("Script", dropdown)

        if current_path and project:
            try:
                from uron.api.scripting import ScriptLoader
                abs_path = os.path.join(project.folder, current_path)
                cls = ScriptLoader.load_class(abs_path, comp.get("class_name", ""))
                props = ScriptLoader.discover_exposed_properties(cls)
            except Exception as e:
                print(f"[Inspector] Error cargando script: {e}")
                props = {}
                
            try:
                current_props = json.loads(comp.get("properties_json", "{}"))
            except Exception:
                current_props = {}
                
            for name, (kind, default) in props.items():
                value = current_props.get(name, default)
                if kind == "float":
                    w = QDoubleSpinBox(); w.setRange(-1e6, 1e6); w.setDecimals(3)
                    w.setValue(float(value))
                    w.valueChanged.connect(lambda v, n=name: self._set_sp(comp, n, float(v)))
                elif kind == "int":
                    w = QSpinBox(); w.setRange(-1e6, 1e6); w.setValue(int(value))
                    w.valueChanged.connect(lambda v, n=name: self._set_sp(comp, n, int(v)))
                elif kind == "bool":
                    w = QCheckBox(); w.setChecked(bool(value))
                    w.toggled.connect(lambda v, n=name: self._set_sp(comp, n, bool(v)))
                else:
                    w = QLineEdit(str(value))
                    w.editingFinished.connect(lambda e=w, n=name: self._set_sp(comp, n, e.text()))
                form.addRow(name, w)

        if comp.removable:
            btn = QPushButton("Remove Script")
            btn.clicked.connect(lambda _, c=comp: self._remove_component(c))
            form.addRow(btn)

        self._layout.addWidget(group)

    def _set_sp(self, comp, name, value):
        set_script_prop(comp, name, value)
        self.changed.emit()

    def _make_widget(self, comp, field):
        k = field.kind
        value = comp.get(field.name)
        
        if k == "float":
            w = QDoubleSpinBox(); w.setRange(field.minimum, field.maximum)
            w.setSingleStep(field.step); w.setDecimals(3); w.setValue(float(value))
            w.valueChanged.connect(lambda v, c=comp, f=field: self._set(c, f, v))
            return w
        if k == "int":
            w = QSpinBox(); w.setRange(int(field.minimum), int(field.maximum))
            w.setValue(int(value))
            w.valueChanged.connect(lambda v, c=comp, f=field: self._set(c, f, v))
            return w
        if k == "bool":
            w = QCheckBox(); w.setChecked(bool(value))
            w.toggled.connect(lambda v, c=comp, f=field: self._set(c, f, v))
            return w
        if k in ("string", "color"):
            w = QLineEdit(str(value))
            if k == "color": w.setPlaceholderText("#rrggbb")
            w.editingFinished.connect(lambda e=w, c=comp, f=field: self._set(c, f, e.text()))
            return w
        if k == "image":
            container = QWidget()
            lay = QHBoxLayout(container); lay.setContentsMargins(0,0,0,0)
            edit = QLineEdit(str(value)); edit.editingFinished.connect(lambda e=edit, c=comp, f=field: self._set(c, f, e.text()))
            btn = QPushButton("…"); btn.setFixedWidth(30)
            def pick():
                path, _ = QFileDialog.getOpenFileName(self, "Select", "", "Images (*.png *.jpg)")
                if path:
                    edit.setText(path)
                    self._set(comp, field, _to_rel_path(path, self._project))
            btn.clicked.connect(pick)
            lay.addWidget(edit); lay.addWidget(btn)
            return container
        if k == "vec2":
            container = QWidget()
            lay = QHBoxLayout(container); lay.setContentsMargins(0,0,0,0)
            x = QDoubleSpinBox(); x.setRange(field.minimum, field.maximum); x.setValue(float(value[0]))
            y = QDoubleSpinBox(); y.setRange(field.minimum, field.maximum); y.setValue(float(value[1]))
            x.valueChanged.connect(lambda _: self._set(comp, field, [x.value(), y.value()]))
            y.valueChanged.connect(lambda _: self._set(comp, field, [x.value(), y.value()]))
            lay.addWidget(QLabel("X")); lay.addWidget(x)
            lay.addWidget(QLabel("Y")); lay.addWidget(y)
            return container
        if k == "enum":
            w = QComboBox(); w.addItems(list(field.choices))
            w.setCurrentText(str(value))
            w.currentTextChanged.connect(lambda v, c=comp, f=field: self._set(c, f, v))
            return w
            
        w = QLineEdit(str(value))
        w.editingFinished.connect(lambda e=w, c=comp, f=field: self._set(c, f, e.text()))
        return w

    def _set(self, comp, field, value):
        if self._building: return
        comp.set(field.name, value)
        set_prop_on_objects(self._current_list[1:], comp.type_name, field.name, value)
        self.changed.emit()

    def _set_enabled(self, comp, value):
        if self._building: return
        comp.enabled = bool(value)
        set_enabled_on_objects(self._current_list[1:], comp.type_name, value)
        self.changed.emit()

    def _set_active(self, value):
        if self._building or self._current is None: return
        set_active_on_objects(self._current_list, value)
        self.changed.emit()

    def _commit_name(self, edit):
        if self._building or self._current is None: return
        text = edit.text().strip() or "GameObject"
        if text != self._current.name:
            self._current.name = text
            self.changed.emit()

    def _remove_component(self, comp):
        if self._current is None: return
        if self._current.remove_component_instance(comp):
            self.refresh()
            self.changed.emit()

    def _open_add_component(self):
        from uron.core.components import COMPONENT_REGISTRY
        names = sorted(n for n in COMPONENT_REGISTRY if n not in HIDDEN_COMPONENTS)
        dialog = AddComponentDialog(names, self)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        cls = COMPONENT_REGISTRY.get(dialog.selected_component())
        if cls:
            added = False
            for obj in self._current_list:
                if obj.get_component(cls.type_name) is not None and cls.unique:
                    continue
                obj.add_component(cls())
                added = True
            if added:
                self.refresh()
                self.changed.emit()
