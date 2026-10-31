"""Diálogo de preferencias del editor y del runtime."""
import copy
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout, QTabWidget, QWidget,
    QSpinBox, QCheckBox, QLineEdit,
)

class PreferencesDialog(QDialog):
    def __init__(self, project, editor_cfg, settings, keybinds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(520)
        self.project = project

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Editor
        editor_tab = QWidget()
        editor_form = QFormLayout(editor_tab)
        grid = editor_cfg.get("grid", {}) if isinstance(editor_cfg, dict) else {}
        snap = editor_cfg.get("snap", {}) if isinstance(editor_cfg, dict) else {}
        
        self.grid_size = QSpinBox(); self.grid_size.setRange(1, 512)
        self.grid_size.setValue(int(grid.get("size", 32)))
        self.grid_visible = QCheckBox()
        self.grid_visible.setChecked(bool(grid.get("visible", True)))
        self.snap_enabled = QCheckBox()
        self.snap_enabled.setChecked(bool(snap.get("enabled", False)))
        self.snap_size = QSpinBox(); self.snap_size.setRange(1, 512)
        self.snap_size.setValue(int(snap.get("size", self.grid_size.value())))
        
        editor_form.addRow("Grid size", self.grid_size)
        editor_form.addRow("Show grid", self.grid_visible)
        editor_form.addRow("Snap enabled", self.snap_enabled)
        editor_form.addRow("Snap size", self.snap_size)
        tabs.addTab(editor_tab, "Editor")

        # Runtime
        runtime_tab = QWidget()
        runtime_form = QFormLayout(runtime_tab)
        window = settings.get("window", {})
        runtime = settings.get("runtime", {})
        
        self.win_width = QSpinBox(); self.win_width.setRange(320, 7680)
        self.win_width.setValue(int(window.get("width", 1100)))
        self.win_height = QSpinBox(); self.win_height.setRange(240, 4320)
        self.win_height.setValue(int(window.get("height", 700)))
        self.resizable = QCheckBox()
        self.resizable.setChecked(bool(window.get("resizable", True)))
        self.target_fps = QSpinBox(); self.target_fps.setRange(1, 500)
        self.target_fps.setValue(int(runtime.get("target_fps", 60)))
        self.physics_fps = QSpinBox(); self.physics_fps.setRange(1, 500)
        self.physics_fps.setValue(int(runtime.get("physics_fps", 60)))
        
        runtime_form.addRow("Window width", self.win_width)
        runtime_form.addRow("Window height", self.win_height)
        runtime_form.addRow("Resizable", self.resizable)
        runtime_form.addRow("Target FPS", self.target_fps)
        runtime_form.addRow("Physics FPS", self.physics_fps)
        tabs.addTab(runtime_tab, "Runtime")

        # Keybinds
        keys_tab = QWidget()
        keys_form = QFormLayout(keys_tab)
        self._key_edits = {}
        for name in ("select", "move", "rotate", "scale", "play", "save", "open"):
            edit = QLineEdit(str(keybinds.get(name, "")))
            keys_form.addRow(name.title(), edit)
            self._key_edits[name] = edit
        tabs.addTab(keys_tab, "Keybinds")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return {
            "editor_cfg": {
                "grid": {"size": self.grid_size.value(), "visible": self.grid_visible.isChecked()},
                "snap": {"enabled": self.snap_enabled.isChecked(), "size": self.snap_size.value()},
            },
            "settings": {
                "window": {"width": self.win_width.value(), "height": self.win_height.value(), "resizable": self.resizable.isChecked()},
                "runtime": {"target_fps": self.target_fps.value(), "physics_fps": self.physics_fps.value()},
            },
            "keybinds": {name: edit.text().strip() for name, edit in self._key_edits.items()},
        }