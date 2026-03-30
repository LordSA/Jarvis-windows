import sys
import os
import ctypes
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt

# Ensure local imports work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from ui.overlay import JarvisOverlay
from core.engine import JarvisEngine

# DPI Awareness fix for Windows 10/11
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

class CustomDialog(QDialog):
    """Specific modal dialog triggered on confirmation."""
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jarvis Permission")
        self.setFixedSize(320, 160)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: #1A1A1A; border: 2px solid #00B9FF; color: white;")
        
        layout = QVBoxLayout(self)
        self.label = QLabel(message)
        self.label.setStyleSheet("font-size: 14px; border: none;")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        btn_layout = QHBoxLayout()
        self.yes_btn = QPushButton("Confirm")
        self.yes_btn.setStyleSheet("background: #00B9FF; color: black; font-weight: bold; border: none; padding: 10px;")
        
        self.no_btn = QPushButton("Cancel")
        self.no_btn.setStyleSheet("background: #444; color: white; border: none; padding: 10px;")
        
        btn_layout.addWidget(self.yes_btn)
        btn_layout.addWidget(self.no_btn)
        layout.addLayout(btn_layout)

        self.yes_btn.clicked.connect(self.accept)
        self.no_btn.clicked.connect(self.reject)

def main():
    app = QApplication(sys.argv)
    
    # UI Setup
    overlay = JarvisOverlay()
    overlay.show()
    
    # Engine Setup (Running in background)
    engine = JarvisEngine("config/settings.json")
    
    # Signals/Slots Connections
    engine.status_changed.connect(overlay.set_status)
    engine.query_heard.connect(overlay.set_query)
    
    def handle_confirmation(message, callback):
        """Displays dialog and sends results back to callback."""
        # Use simple synchronous call since we're in the UI thread
        dialog = CustomDialog(message, overlay)
        result = dialog.exec()
        callback(result == QDialog.DialogCode.Accepted)

    engine.request_confirmation.connect(handle_confirmation)

    engine.start() # Start listening
    
    result = app.exec()
    engine.stop()
    sys.exit(result)

if __name__ == "__main__":
    main()
