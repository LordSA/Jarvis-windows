from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QFrame, 
                             QPushButton, QMessageBox, QDialog, QHBoxLayout)
from PyQt6.QtCore import (Qt, QPropertyAnimation, QRect, QEasingCurve, 
                          pyqtSignal, QObject, pyqtProperty)
from PyQt6.QtGui import (QPainter, QColor, QPen, QBrush)
import json
import os

class JarvisOverlay(QWidget):
    """Main borderless overlay showing a Siri-style pulsing glow."""
    request_confirmation = pyqtSignal(str, object) 

    def __init__(self):
        super().__init__()
        # Window Setup
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | 
                            Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 300)
        
        # Position in bottom-right corner
        screen = self.screen().availableGeometry()
        self.move(screen.width() - self.width() - 20, screen.height() - self.height() - 20)

        # Glow animation property
        self._glow_radius = 40
        self.setup_animation()

        # Labels for feedback
        self.status_label = QLabel("Jarvis V1", self)
        self.status_label.setStyleSheet("color: white; font-family: 'Segoe UI'; font-size: 14px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setGeometry(0, 200, 300, 40)

        self.last_query_label = QLabel("", self)
        self.last_query_label.setStyleSheet("color: #00B9FF; font-family: 'Segoe UI'; font-size: 12px;")
        self.last_query_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.last_query_label.setGeometry(0, 230, 300, 40)

    @pyqtProperty(int)
    def glow_radius(self):
        return self._glow_radius

    @glow_radius.setter
    def glow_radius(self, value):
        self._glow_radius = value
        self.update()

    def setup_animation(self):
        self.animation = QPropertyAnimation(self, b"glow_radius")
        self.animation.setDuration(1500)
        self.animation.setStartValue(40)
        self.animation.setEndValue(70)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.animation.setLoopCount(-1) # Infinite loop
        self.animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw central circle
        center_x, center_y = self.width() // 2, self.height() // 2
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Pulsing Glow
        glow_color = QColor(0, 185, 255, 100)
        painter.setBrush(QBrush(glow_color))
        painter.drawEllipse(center_x - self._glow_radius, center_y - self._glow_radius, 
                            self._glow_radius * 2, self._glow_radius * 2)
        
        # inner solid circle
        inner_color = QColor(0, 185, 255, 200)
        painter.setBrush(QBrush(inner_color))
        painter.drawEllipse(center_x - 30, center_y - 30, 60, 60)

    def set_status(self, text):
        self.status_label.setText(text)

    def set_query(self, query):
        if query:
            self.last_query_label.setText(f"'{query}'")
        else:
            self.last_query_label.setText("")

    def show_confirmation(self, message, callback):
        """Display a custom confirmation dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Confirmation")
        dialog.setFixedSize(300, 150)
        dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        dialog.setStyleSheet("background-color: #2D2D2D; border: 1px solid #00B9FF; color: white;")

        layout = QVBoxLayout(dialog)
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)

        btn_layout = QHBoxLayout()
        yes_btn = QPushButton("Yes")
        yes_btn.setStyleSheet("background: #00B9FF; color: black; border: none; padding: 5px;")
        no_btn = QPushButton("No")
        no_btn.setStyleSheet("background: #555; color: white; border: none; padding: 5px;")

        yes_btn.clicked.connect(lambda: (dialog.accept(), callback(True)))
        no_btn.clicked.connect(lambda: (dialog.reject(), callback(False)))

        btn_layout.addWidget(yes_btn)
        btn_layout.addWidget(no_btn)
        layout.addLayout(btn_layout)

        dialog.show()

# styles.qss - optional standalone file
STYLES = """
QWidget {
    font-family: 'Segoe UI';
}
"""
