import os
from PySide6.QtWidgets import (QListWidget, QListWidgetItem, QWidget, QVBoxLayout, 
                             QPushButton, QLabel, QFrame, QSlider, QHBoxLayout)
from PySide6.QtCore import Qt, Signal
from src.utils.config import Config

#/////////////////////////////////#
#     STUDIO COMPONENT LIBRARY    #
#/////////////////////////////////#

class FileListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background: {Config.COLOR_PANEL}; border: none;")

    def add_file(self, full_path: str):
        item = QListWidgetItem(os.path.basename(full_path))
        item.setData(Qt.UserRole, full_path)
        self.addItem(item)

class ToolGroup(QFrame):
    def __init__(self, title, button_configs):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(5, 5, 5, 5)
        lay.setSpacing(4)
        
        lbl = QLabel(title.upper())
        lbl.setStyleSheet(f"color: {Config.COLOR_TEXT_DIM}; font-size: 9px; font-weight: bold;")
        lay.addWidget(lbl)
        
        self.buttons = {}
        checkable = ["MOVE", "BRUSH", "ERASER", "RECT", "LASSO"]
        
        for name in button_configs:
            btn = QPushButton(name)
            if name in checkable: 
                btn.setCheckable(True)
                btn.setAutoExclusive(True) 
            self.buttons[name] = btn
            lay.addWidget(btn)

class HardwareMonitor(QFrame):
    def __init__(self):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        
        self.lbl = QLabel("SYSTEM IDLE")
        self.lbl.setStyleSheet(f"color: {Config.COLOR_ACCENT}; font-weight: bold; font-size: 10px;")
        
        self.bar = QSlider(Qt.Horizontal)
        self.bar.setRange(0, 100)
        self.bar.setFixedWidth(100)
        self.bar.setEnabled(False)
        
        lay.addWidget(self.lbl)
        lay.addWidget(self.bar)

class BrushSlider(QWidget):
    def __init__(self, label, default, minimum, maximum, callback=None, is_tile=False):
        super().__init__()
        self.is_tile = is_tile
        self.base_label = label
        lay = QVBoxLayout(self)
        
        self.display = QLabel("")
        self.display.setStyleSheet(f"color: {Config.COLOR_TEXT_DIM}; font-size: 10px;")
        
        self.slider = QSlider(Qt.Horizontal)
        if is_tile:
            self.slider.setRange(1, 8) 
            self.slider.setValue(default // 512)
        else:
            self.slider.setRange(minimum, maximum)
            self.slider.setValue(default)
            
        self.slider.valueChanged.connect(self.update_text)
        if callback: self.slider.valueChanged.connect(callback)
            
        lay.addWidget(self.display)
        lay.addWidget(self.slider)
        self.update_text(self.slider.value())

    def update_text(self, val):
        if self.is_tile:
            self.display.setText(f"{self.base_label}: {val * 512}px")
        else:
            self.display.setText(f"{self.base_label}: {val}px")