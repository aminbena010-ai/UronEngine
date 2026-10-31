"""Panel Console: visor de logs con colores."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from IDE.ui.console.mod import ConsoleState

class ConsolePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = ConsoleState()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        # Estilo VS Code
        self.text.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e; 
                color: #d4d4d4; 
                border: none; 
                font-family: "Consolas", "Ubuntu Mono", monospace;
                font-size: 13px;
                padding: 4px;
            }
        """)
        layout.addWidget(self.text)

    def log(self, message):
        """Añade un mensaje con color según su tipo."""
        self.state.add(message)
        if "Error" in message or "ERROR" in message:
            color = "#f48771" # Rojo
        elif "Warn" in message or "WARN" in message:
            color = "#dcdcaa" # Amarillo
        else:
            color = "#d4d4d4" # Blanco/Gris
            
        self.text.append(f'<span style="color:{color};">{message}</span>')
        # Auto-scroll al final
        sb = self.text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear(self):
        self.state.clear()
        self.text.clear()