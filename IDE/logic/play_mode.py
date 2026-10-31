"""Play mode integrado del editor (QProcess + control por stdin)."""
import os
import sys

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal


class PlayMode(QObject):
    output = pyqtSignal(str)
    stateChanged = pyqtSignal(str)      # running | paused | stopped
    processEnded = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.state = "stopped"

    def is_running(self):
        return self.process is not None and \
            self.process.state() != QProcess.ProcessState.NotRunning

    def start(self, scene_path, project):
        if self.is_running():
            self.stop()
        
        # Ruta al runtime (subimos 2 niveles desde IDE/logic/ a la raíz)
        runtime = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "runtime", "runtime.py"))
        
        py = sys.executable
        
        self.process = QProcess(self)
        self.process.setWorkingDirectory(project.folder)
        
        # Configurar entorno para OpenGL/SDL
        env = QProcessEnvironment.systemEnvironment()
        if env.contains("DISPLAY"):
            if not env.contains("SDL_VIDEODRIVER"):
                env.insert("SDL_VIDEODRIVER", "x11")
            if not env.contains("QT_QPA_PLATFORM"):
                env.insert("QT_QPA_PLATFORM", "xcb")
        self.process.setProcessEnvironment(env)
        
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.readyReadStandardError.connect(self._read_output)
        self.process.finished.connect(self._on_finished)
        
        self.process.start(py, [runtime, scene_path, project.folder])
        
        if not self.process.waitForStarted(3000):
            self.output.emit("[Play] No se pudo iniciar el runtime.")
            self.process = None
            self.state = "stopped"
            self.stateChanged.emit("stopped")
            return False
            
        self.state = "running"
        self.stateChanged.emit("running")
        self.output.emit("[Play] Runtime iniciado")
        return True

    def _read_output(self):
        if self.process is None: return
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        for line in data.splitlines():
            if line.strip():
                self.output.emit(line.rstrip())

    def _on_finished(self, code, _status=None):
        self._read_output()
        self.output.emit(f"[Play] Runtime terminó (código {code})")
        self.process = None
        self.state = "stopped"
        self.stateChanged.emit("stopped")
        self.processEnded.emit(int(code) if isinstance(code, int) else 0)

    def send(self, command):
        if self.process is None: return False
        try:
            self.process.write((command + "\n").encode("utf-8"))
            self.process.waitForBytesWritten(200)
            return True
        except Exception:
            return False

    def pause(self):
        if self.send("pause"):
            self.state = "paused"
            self.stateChanged.emit(self.state)

    def resume(self):
        if self.send("resume"):
            self.state = "running"
            self.stateChanged.emit(self.state)

    def step(self):
        if self.send("step"):
            self.state = "paused"
            self.stateChanged.emit(self.state)

    def stop(self):
        if self.process is None:
            self.state = "stopped"
            self.stateChanged.emit("stopped")
            return
        self.send("stop")
        if not self.process.waitForFinished(1500):
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()
                self.process.waitForFinished(500)
        self.process = None
        self.state = "stopped"
        self.stateChanged.emit("stopped")