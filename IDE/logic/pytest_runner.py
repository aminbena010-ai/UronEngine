"""Runs the project's tests in the terminal that launched the IDE."""
import os
import sys

from PyQt6.QtCore import QObject, QProcess, pyqtSignal


class PytestRunner(QObject):
    started = pyqtSignal()
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(
            QProcess.ProcessChannelMode.ForwardedChannels
        )
        self.process.started.connect(self.started.emit)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)

    def is_running(self):
        return self.process is not None and \
            self.process.state() != QProcess.ProcessState.NotRunning

    def start(self, project_folder):
        if self.is_running():
            return False
        if not os.path.isdir(project_folder):
            self.failed.emit(f"Project folder does not exist: {project_folder}")
            return False

        self.process.setWorkingDirectory(os.path.abspath(project_folder))
        self.process.start(
            sys.executable,
            ["-u", "-m", "pytest", "-vv", "-s"],
        )
        return True

    def stop(self):
        if not self.is_running():
            return
        self.process.terminate()
        if not self.process.waitForFinished(1500):
            self.process.kill()
            self.process.waitForFinished(500)

    def _on_finished(self, exit_code, _exit_status):
        self.finished.emit(int(exit_code))

    def _on_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.failed.emit(self.process.errorString())
