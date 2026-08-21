from PySide6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QTextEdit, QPushButton
from src.utils.system_info import SystemMonitor

#/////////////////////////////////#
#    STUDIO KNOWLEDGE BASE        #
#/////////////////////////////////#

class HelpSystem(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manga-Cleaner Studio Manual")
        self.resize(600, 480)
        self.setStyleSheet("background-color: #121217; color: #e0e0e0; font-family: 'Segoe UI';")
        
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        
        # TAB 1: SHORTCUTS
        tab1 = QTextEdit()
        tab1.setReadOnly(True)
        tab1.setHtml(
            "<h3>⌨️ Keyboard Shortcuts</h3>"
            "<table border='0' cellpadding='5'>"
            "<tr><td><b>[O]</b></td><td>Auto-Detect Text Bubbles (OCR)</td></tr>"
            "<tr><td><b>[T]</b></td><td>Auto-Detect Transparent Areas</td></tr>"
            "<tr><td><b>[C]</b></td><td>Execute AI Clean (Inpainting)</td></tr>"
            "<tr><td><b>[B] / [E] / [M]</b></td><td>Brush / Eraser / Move Tools</td></tr>"
            "<tr><td><b>[R] / [L]</b></td><td>Rect / Lasso Tools</td></tr>"
            "<tr><td><b>[Shift] + Click</b></td><td>Draw straight line between points</td></tr>"
            "<tr><td><b>Alt + Right-Click Drag</b></td><td><b>Dynamically Resize Brush</b> (Left: Smaller, Right: Bigger)</td></tr>"
            "<tr><td><b>Hold [Alt]</b></td><td><b>Erase Mode</b> (Quick-toggle for Brush, Rect, and Lasso)</td></tr>"
            "<tr><td><b>Hold [Space]</b></td><td><b>Quick Toggle</b> Pan/Move Image</td></tr>"
            "<tr><td><hr></td><td><hr></td></tr>"
            "<tr><td><b>[Ctrl + Z]</b></td><td>Undo AI Clean (Image)</td></tr>"
            "<tr><td><b>[Alt + Z]</b></td><td>Undo Manual Mask Painting</td></tr>"
            "</table>"
        )
        
        # TAB 2: BATCH GUIDE
        tab2 = QTextEdit()
        tab2.setReadOnly(True)
        tab2.setHtml(
            "<h3>📦 Batch Processing</h3>"
            "<p>1. Import a folder of manga chapters.</p>"
            "<p>2. Click <b>RUN BATCH PROCESS</b> and choose your format.</p>"
            "<p>3. The app will cycle through: <i>Load -> Detect -> Clean -> Save</i>.</p>"
            "<p>4. Cleaned pages are saved in the <b>/processed/</b> folder.</p>"
            "<p><i>Note: laptops without CUDA GPU may take longer to finish.</i></p>"
        )

        # TAB 3: HARDWARE
        specs = SystemMonitor.get_detailed_specs()
        tab3 = QTextEdit()
        tab3.setReadOnly(True)
        tab3.setHtml(
            "<h3>💻 System Diagnostics</h3>"
            f"<p><b>Engine Found:</b> {specs['engine']}</p>"
            f"<p><b>RAM Detected:</b> {specs['ram']} GB</p>"
            "<hr>"
            "<p><b>VRAM Optimization:</b> Each patch is processed in 512px chunks to minimize GPU pressure.</p>"
            "<p><b>Persistence:</b> During batching, AI models stay loaded to maximize processing speed.</p>"
        )
        
        tabs.addTab(tab1, "Shortcuts")
        tabs.addTab(tab2, "Batching")
        tabs.addTab(tab3, "Hardware")
        layout.addWidget(tabs)
        
        close_btn = QPushButton("CLOSE")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    @staticmethod
    def show_guide(parent):
        dialog = HelpSystem(parent)
        dialog.exec()
