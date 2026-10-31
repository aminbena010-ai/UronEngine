"""Diálogo de build con salida en vivo (PyInstaller)."""
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QCheckBox,
    QPlainTextEdit, QFileDialog, QDialogButtonBox, QLabel,
)
from PyQt6.QtCore import QProcess

from uron.build import pyinstaller_command


class BuildDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.process = None
        self.setWindowTitle(f"Build {project.name}")
        self.resize(720, 480)
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.output_edit = QLineEdit(os.path.join(project.folder, "build"))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(QLabel("Output:"))
        row.addWidget(self.output_edit, 1)
        row.addWidget(browse)
        layout.addLayout(row)

        self.onefile = QCheckBox("Single executable (--onefile)")
        self.onefile.setChecked(True)
        layout.addWidget(self.onefile)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, 1)

        self.buttons = QDialogButtonBox()
        self.build_btn = self.buttons.addButton("Build", QDialogButtonBox.ButtonRole.ActionRole)
        self.close_btn = self.buttons.addButton("Close", QDialogButtonBox.ButtonRole.RejectRole)
        self.build_btn.clicked.connect(self._build)
        self.close_btn.clicked.connect(self._close)
        layout.addWidget(self.buttons)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Output folder", self.output_edit.text())
        if folder:
            self.output_edit.setText(folder)

    def _append(self, text):
        self.log_view.appendPlainText(text.rstrip())

    def _build(self):
        if self.process is not None:
            return
        output = self.output_edit.text().strip()
        if not output:
            return
        project = self.project
        project.internal_ensure()
        
        # Usamos la función del motor para construir el comando
        cmd = pyinstaller_command(project, output, onefile=self.onefile.isChecked())
        self.log_view.clear()
        self._append("$ " + " ".join(cmd))
        
        self.process = QProcess(self)
        self.process.setWorkingDirectory(project.folder)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.finished.connect(self._finished)
        self.process.start(cmd[0], cmd[1:])
        
        if not self.process.waitForStarted(3000):
            self._append("No se pudo iniciar PyInstaller.")
            self.process = None

    def _read(self):
        if self.process is None: return
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        for line in data.splitlines():
            self._append(line)

    def _finished(self, code, _status=None):
        self._read()
        self._append(f"\nBuild terminado con código {code}")
        self.process = None

    def _close(self):
        if self.process is not None:
            self.process.terminate()
        self.reject()

    def closeEvent(self, event):
        if self.process is not None:
            self.process.terminate()
        super().closeEvent(event)