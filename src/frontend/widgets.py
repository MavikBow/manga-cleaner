import os
import PySide6.QtSvg  # CRITICAL: Forces Qt to load the SVG image format plugin!
from PySide6.QtWidgets import (QListWidget, QListWidgetItem, QWidget, QVBoxLayout, 
                             QPushButton, QLabel, QFrame, QSlider, QHBoxLayout,
                             QStyledItemDelegate)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QIcon
from src.utils.config import Config
from src.utils.paths import Paths

#/////////////////////////////////#
#    STUDIO COMPONENT LIBRARY     #
#/////////////////////////////////#

class FileListDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icons = {}

    def _get_icon(self, state_name: str) -> QIcon:
        """Caches and returns the SVG icon for the given state"""
        if state_name not in self.icons:
            icon_path = os.path.join(Paths.BASE_DIR, "assets", f"icon_{state_name}.svg")
            if os.path.exists(icon_path):
                self.icons[state_name] = QIcon(icon_path)
            else:
                self.icons[state_name] = QIcon() # Fallback to prevent crash if SVG is missing
        return self.icons[state_name]

    def paint(self, painter, option, index):
        # 1. Paint standard background, highlight, checkbox, and text
        super().paint(painter, option, index)
        
        # 2. Extract our custom status flag from the item
        state_name = index.data(Qt.UserRole + 1)
        if state_name:
            icon = self._get_icon(state_name)
            if not icon.isNull():
                icon_size = 18
                
                # 3. Calculate position: strict right align (stuck to the wall with tiny 4px gap)
                x = option.rect.right() - icon_size - 4
                y = option.rect.top() + (option.rect.height() - icon_size) // 2
                rect = QRect(x, y, icon_size, icon_size)
                
                # 4. Draw icon strictly in Normal mode so selection highlight doesn't color-tint it!
                icon.paint(painter, rect, Qt.AlignCenter, QIcon.Normal, QIcon.On)

class FileListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background: {Config.COLOR_PANEL}; border: none;")
        self.setItemDelegate(FileListDelegate(self))

    def add_file(self, full_path: str):
        item = QListWidgetItem(os.path.basename(full_path))
        item.setData(Qt.UserRole, full_path)
        item.setData(Qt.UserRole + 1, "unmodified")  # Custom role for our delegate logic
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Unchecked)
        self.addItem(item)

    def update_item_state(self, full_path: str, state_name: str):
        """Updates the background state for the delegate to redraw"""
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.UserRole) == full_path:
                item.setData(Qt.UserRole + 1, state_name)
                break

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

class LabeledSlider(QWidget):
    def __init__(self, label, default, minimum, maximum, callback=None, is_tile=False, suffix="px"):
        super().__init__()
        self.is_tile = is_tile
        self.suffix = suffix
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
            self.display.setText(f"{self.base_label}: {val}{self.suffix}")
