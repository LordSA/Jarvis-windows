from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QFrame, 
                             QPushButton, QMessageBox, QDialog, QHBoxLayout)
from PyQt6.QtCore import (Qt, QPropertyAnimation, QRect, QEasingCurve, 
                          pyqtSignal, QObject, pyqtProperty)
from PyQt6.QtGui import (QPainter, QColor, QPen, QBrush)
import json
import os
import ctypes
from ctypes import wintypes

class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ('AccentState', ctypes.c_int),
        ('AccentFlags', ctypes.c_int),
        ('GradientColor', ctypes.c_int),
        ('AnimationId', ctypes.c_int)
    ]

class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ('Attribute', ctypes.c_int),
        ('Data', ctypes.POINTER(ACCENT_POLICY)),
        ('SizeOfData', ctypes.c_size_t)
    ]

class JarvisOverlay(QWidget):
    """Main borderless overlay showing a Siri-style pulsing glow with Acrylic blur."""
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

        # Apply Acrylic Blur (Windows Native)
        self.apply_blur_effect()

        # Glow animation property
        self._glow_radius = 40
        self.setup_animation()

        # Labels for feedback
        self.status_label = QLabel("Jarvis V1", self)
        self.status_label.setStyleSheet("color: white; font-family: 'Segoe UI Semibold'; font-size: 14px; background: transparent;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setGeometry(0, 200, 300, 40)

        self.last_query_label = QLabel("", self)
        self.last_query_label.setStyleSheet("color: #00B9FF; font-family: 'Segoe UI'; font-size: 12px; background: transparent;")
        self.last_query_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.last_query_label.setGeometry(0, 230, 300, 40)

    def apply_blur_effect(self):
        """Applies the Windows Acrylic Blur effect using ctypes."""
        try:
            hwnd = self.winId().__int__()
            user32 = ctypes.windll.user32
            
            accent = ACCENT_POLICY()
            accent.AccentState = 3 # ACCENT_ENABLE_BLURBEHIND (or 4 for Acrylic)
            accent.GradientColor = 0x00000000 # Transparent
            
            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attribute = 19 # WCA_ACCENT_POLICY
            data.Data = ctypes.pointer(accent)
            data.SizeOfData = ctypes.sizeof(accent)
            
            user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
        except Exception as e:
            print(f"Blur error: {e}")

    @pyqtProperty(int)
    def glow_radius(self):
        return self._glow_radius

    @glow_radius.setter
    def glow_radius(self, value):
        self._glow_radius = value
        self.update()

    def setup_animation(self):
        self.animation = QPropertyAnimation(self, b"glow_radius")
        self.animation.setDuration(1200)
        self.animation.setStartValue(40)
        self.animation.setEndValue(75)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.animation.setLoopCount(-1) 
        self.animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_x, center_y = self.width() // 2, self.height() // 2
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Outer pulsing glow
        glow_color = QColor(0, 185, 255, 60)
        painter.setBrush(QBrush(glow_color))
        painter.drawEllipse(center_x - self._glow_radius, center_y - self._glow_radius, 
                            self._glow_radius * 2, self._glow_radius * 2)
        
        # Middle ring
        mid_color = QColor(0, 185, 255, 120)
        painter.setBrush(QBrush(mid_color))
        painter.drawEllipse(center_x - 50, center_y - 50, 100, 100)

        # inner solid circle
        inner_color = QColor(0, 185, 255, 230)
        painter.setBrush(QBrush(inner_color))
        painter.drawEllipse(center_x - 35, center_y - 35, 70, 70)

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
