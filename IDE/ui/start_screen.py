"""Pantalla inicial (estilo Unity): New / Open / Recent."""
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem,
    QLabel, QFileDialog, QMessageBox, QFormLayout, QLineEdit, QCheckBox,
    QDialogButtonBox, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from uron.core.project import UronProject, NotAProjectError, ANCHOR_NAME
from IDE.logic import recent as recent_mod

class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New URON Project")
        self.setMinimumWidth(560)
        self._project = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit("MiJuego")
        form.addRow("Name:", self.name_edit)

        row = QHBoxLayout()
        self.loc_edit = QLineEdit(os.path.expanduser("~/Documentos"))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.loc_edit, 1)
        row.addWidget(browse)
        w = QWidget(); w.setLayout(row)
        form.addRow("Location:", w)

        layout.addLayout(form)

        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._create)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose location", self.loc_edit.text())
        if folder:
            self.loc_edit.setText(folder)

    def _create(self):
        name = self.name_edit.text().strip()
        loc = self.loc_edit.text().strip()
        if not name or not loc:
            QMessageBox.warning(self, "New Project", "Escribe un nombre y una ubicación.")
            return
        if not os.path.isdir(loc):
            QMessageBox.warning(self, "New Project", f"La carpeta no existe:\n{loc}")
            return
        try:
            proj = UronProject.create(loc, name)
        except Exception as e:
            QMessageBox.critical(self, "New Project", str(e))
            return
        self._project = proj
        self.accept()

    def project(self):
        return self._project


class StartScreen(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("URON Engine")
        self.setMinimumSize(560, 500)
        self._project = None

        layout = QVBoxLayout(self)

        title = QLabel("URON Engine")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont(); f.setPointSize(26); f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)

        sub = QLabel("2D Game Development Environment")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)
        layout.addSpacing(16)

        new_btn = QPushButton("New Project…")
        new_btn.clicked.connect(self._new)
        layout.addWidget(new_btn)

        open_btn = QPushButton("Open Project…")
        open_btn.clicked.connect(self._open)
        layout.addWidget(open_btn)

        layout.addWidget(QLabel("Recent Projects"))
        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self._open_recent)
        layout.addWidget(self.recent_list, 1)

        quit_btn = QPushButton("Quit")
        quit_btn.clicked.connect(self.reject)
        layout.addWidget(quit_btn)

        self._fill_recent()

    def _fill_recent(self):
        self.recent_list.clear()
        for folder in recent_mod.load():
            item = QListWidgetItem(f"{os.path.basename(folder)}    —    {folder}")
            item.setData(Qt.ItemDataRole.UserRole, folder)
            self.recent_list.addItem(item)

    def _new(self):
        dlg = NewProjectDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            proj = dlg.project()
            if proj:
                recent_mod.push(proj.folder)
                self._project = proj
                self.accept()

    def _open(self):
        anchor, _ = QFileDialog.getOpenFileName(
            self, "Open URON project — select project.uron", os.path.expanduser("~"),
            "URON Project (project.uron)")
        if not anchor:
            folder = QFileDialog.getExistingDirectory(self, "Open URON project folder")
            if not folder: return
            anchor = folder
        try:
            proj = UronProject.open(anchor)
        except NotAProjectError as e:
            QMessageBox.warning(self, "Open Project", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Open Project", str(e))
            return
        recent_mod.push(proj.folder)
        self._project = proj
        self.accept()

    def _open_recent(self, item):
        folder = item.data(Qt.ItemDataRole.UserRole)
        try:
            proj = UronProject.open(folder)
        except NotAProjectError as e:
            QMessageBox.warning(self, "Open Project", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Open Project", str(e))
            return
        recent_mod.push(proj.folder)
        self._project = proj
        self.accept()

    def project(self):
        return self._project