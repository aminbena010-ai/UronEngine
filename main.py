"""URON Engine 0.5 — Punto de entrada principal del IDE."""
import os
import sys

# Añadir la raíz del proyecto al PATH para que los imports funcionen
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _check_dependencies():
    """Comprueba que las librerías necesarias estén instaladas."""
    missing = []
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        missing.append("PyQt6")
    try:
        import pygame  # noqa: F401
    except ImportError:
        missing.append("pygame")
    try:
        import OpenGL  # noqa: F401
    except ImportError:
        missing.append("PyOpenGL")

    if missing:
        print("\n" + "="*50)
        print("❌ Faltan dependencias:", ", ".join(missing))
        print("Instálalas con:  pip install -r requirements.txt")
        print("O individualmente: pip install PyQt6 pygame PyOpenGL")
        print("="*50 + "\n")
        raise SystemExit(1)


def _prepare_environment():
    """Configura variables de entorno para evitar warnings y problemas gráficos."""
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    
    # Configuración para Linux (X11)
    if os.environ.get("QT_QPA_PLATFORM"):
        return
    if os.environ.get("DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"


def main():
    # 1. Preparar entorno y comprobar dependencias
    _prepare_environment()
    _check_dependencies()

    # 2. Importar PyQt6 y los módulos del IDE
    from PyQt6.QtWidgets import QApplication, QDialog
    from IDE.ui.theme import STYLESHEET
    from IDE.ui.start_screen import StartScreen
    from IDE.ui.IM import MainWindow
    from uron.core.version import ENGINE_VERSION

    # 3. Crear la aplicación Qt
    app = QApplication(sys.argv)
    app.setApplicationName("URON Engine")
    app.setApplicationDisplayName(f"URON Engine {ENGINE_VERSION}")
    app.setStyle("Fusion")
    
    # Aplicar el tema oscuro global
    app.setStyleSheet(STYLESHEET)

    # 4. Bucle principal de la aplicación
    project = None
    scene_path = None
    while True:
        if project is None:
            # Mostrar pantalla de inicio (New / Open / Recent)
            start = StartScreen()
            if start.exec() != QDialog.DialogCode.Accepted:
                break  # El usuario cerró la ventana o le dio a Salir

            project = start.project()
            if project is None:
                break

        # Mostrar la ventana principal del IDE con el proyecto cargado
        window = MainWindow(project, scene_path)
        window.show()
        app.exec()  # Bloquea hasta que se cierre la ventana

        # Si la ventana se cerró sin volver a la pantalla de inicio, salimos
        if window.isVisible():
            break
        if window.restart_requested:
            project = window.project
            scene_path = window.current_scene_path
        else:
            project = None
            scene_path = None

    sys.exit(0)


if __name__ == "__main__":
    main()