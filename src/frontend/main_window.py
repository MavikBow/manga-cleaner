import os
import cv2
import numpy as np
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QSplitter, QFileDialog,
                             QMenu, QMessageBox, QGraphicsView, QProgressBar, QInputDialog)
from PySide6.QtGui import QShortcut, QKeySequence, QImage
from PySide6.QtCore import Qt, QTimer, QThread
from src.frontend.widgets import FileListWidget, ToolGroup, BrushSlider, HardwareMonitor
from src.frontend.canvas import MangaCanvas
from src.frontend.help_system import HelpSystem
from src.utils.system_info import SystemMonitor
from src.utils.history import HistoryManager
from src.utils.config import Config
from src.utils.logger import logger
from src.backend.workers import AIWorker
from src.backend.photoshop import PhotoshopBridge
from src.backend.batch_engine import BatchEngine
from src.backend.ai_manager import AIManager

#/////////////////////////////////#
#     STUDIO MAIN CONTROLLER      #
#/////////////////////////////////#

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{Config.APP_NAME} v{Config.VERSION}")
        self.resize(1500, 900)
        
        self.monitor = SystemMonitor()
        self.history = HistoryManager(Config.MAX_HISTORY)
        self.batch_engine = BatchEngine()
        self.worker_thread = None
        self.is_batching = False
        self.is_currently_erasing = False
        
        self.init_ui()
        self.setup_shortcuts()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(2000)
        logger.info("--- STUDIO INTERFACE READY ---")

    def init_ui(self):
        self.central = QWidget()
        self.setCentralWidget(self.central)
        main_lay = QVBoxLayout(self.central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        #/////////////////////////////////#
        #           NAVIGATION            #
        #/////////////////////////////////#
        self.nav = QFrame()
        self.nav.setObjectName("NavBar")
        self.nav.setFixedHeight(60)
        nav_lay = QHBoxLayout(self.nav)
        
        title = QLabel(f"{Config.APP_NAME.upper()} {Config.VERSION}")
        title.setStyleSheet(f"color: {Config.COLOR_ACCENT}; font-weight: bold; font-size: 18px;")
        
        self.hw_mon = HardwareMonitor()
        
        btn_help = QPushButton("?")
        btn_help.setFixedSize(30, 30)
        btn_help.clicked.connect(lambda: HelpSystem.show_guide(self))
        
        btn_open = QPushButton("IMPORT FOLDER")
        btn_open.clicked.connect(self.on_open_folder)
        
        btn_ps = QPushButton("PS BRIDGE")
        btn_ps.clicked.connect(self.on_photoshop_bridge)
        
        self.btn_export = QPushButton("EXPORT ▼")
        self.btn_export.setObjectName("PrimaryBtn")
        exp_menu = QMenu(self)
        exp_menu.addAction("Export as JPG").triggered.connect(lambda: self.on_export("jpg"))
        exp_menu.addAction("Export as PNG").triggered.connect(lambda: self.on_export("png"))
        self.btn_export.setMenu(exp_menu)

        nav_lay.addWidget(title)
        nav_lay.addStretch()
        nav_lay.addWidget(self.hw_mon)
        nav_lay.addSpacing(10)
        nav_lay.addWidget(btn_help)
        nav_lay.addWidget(btn_open)
        nav_lay.addWidget(btn_ps)
        nav_lay.addWidget(self.btn_export)
        main_lay.addWidget(self.nav)

        split = QSplitter(Qt.Horizontal)
        
        #/////////////////////////////////#
        #          SIDE PANELS            #
        #/////////////////////////////////#
        self.lp = QFrame()
        self.lp.setObjectName("SidePanel")
        lp_lay = QVBoxLayout(self.lp)
        self.file_list = FileListWidget()
        self.file_list.itemClicked.connect(self.on_file_clicked)
        self.btn_batch = QPushButton("RUN BATCH PROCESS")
        self.btn_batch.setObjectName("ActionBtn")
        self.btn_batch.clicked.connect(self.on_start_batch)
        lp_lay.addWidget(QLabel("PROJECT ASSETS"))
        lp_lay.addWidget(self.file_list)
        lp_lay.addWidget(self.btn_batch)
        
        self.canvas = MangaCanvas()
        self.canvas.mask_changed.connect(lambda: self.history.push_mask_state(self.canvas.mask))
        self.canvas.tool_state_updated.connect(self.on_eraser_toggle_ui)
        
        self.rp = QFrame()
        self.rp.setObjectName("SidePanel")
        rp_lay = QVBoxLayout(self.rp)
        
        self.mode_lbl = QLabel("MODE: PAINTING")
        self.mode_lbl.setStyleSheet(f"color: {Config.COLOR_ACCENT}; font-weight: bold; font-size: 10px;")
        rp_lay.addWidget(self.mode_lbl)
        
        self.tools = ToolGroup("Drawing Tools", ["MOVE", "BRUSH", "ERASER", "RECT", "LASSO", "CLEAR"])
        self.tools.buttons["MOVE"].clicked.connect(lambda: self.set_tool("NONE"))
        self.tools.buttons["BRUSH"].clicked.connect(lambda: self.set_tool("BRUSH"))
        self.tools.buttons["ERASER"].clicked.connect(lambda: self.set_tool("ERASER"))
        self.tools.buttons["RECT"].clicked.connect(lambda: self.set_tool("RECT"))
        self.tools.buttons["LASSO"].clicked.connect(lambda: self.set_tool("LASSO"))
        self.tools.buttons["CLEAR"].clicked.connect(self.canvas.clear_mask)
        
        self.b_slider = BrushSlider("BRUSH SIZE", 40, 1, 300, self.canvas.set_brush_size)
        self.t_slider = BrushSlider("MAX TILE SIZE", 2048, 512, 4096, is_tile=True)
        
        btn_scan = QPushButton("DETECTION SCAN [D]")
        btn_scan.setObjectName("ActionBtn")
        btn_scan.clicked.connect(self.on_auto_scan)
        
        self.btn_clean = QPushButton("EXECUTE CLEAN [C]")
        self.btn_clean.setObjectName("PrimaryBtn")
        self.btn_clean.setFixedHeight(45)
        self.btn_clean.clicked.connect(self.on_lama_clean)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        
        rp_lay.addWidget(self.tools)
        rp_lay.addWidget(self.b_slider)
        rp_lay.addSpacing(20)
        rp_lay.addWidget(btn_scan)
        rp_lay.addWidget(self.t_slider)
        rp_lay.addWidget(self.btn_clean)
        rp_lay.addStretch()
        rp_lay.addWidget(self.progress_bar)
        
        split.addWidget(self.lp)
        split.addWidget(self.canvas)
        split.addWidget(self.rp)
        split.setSizes([220, 1000, 240])
        main_lay.addWidget(split, 1)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("B"), self).activated.connect(lambda: self.set_tool("BRUSH"))
        QShortcut(QKeySequence("R"), self).activated.connect(lambda: self.set_tool("RECT"))
        QShortcut(QKeySequence("L"), self).activated.connect(lambda: self.set_tool("LASSO"))
        QShortcut(QKeySequence("Space"), self).activated.connect(lambda: self.set_tool("NONE"))
        
        QShortcut(QKeySequence("D"), self).activated.connect(self.on_auto_scan)
        QShortcut(QKeySequence("C"), self).activated.connect(self.on_lama_clean)
        
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.on_undo_image)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(self.on_redo_image)
        QShortcut(QKeySequence("Alt+Z"), self).activated.connect(self.on_undo_mask)
        QShortcut(QKeySequence("Alt+Shift+Z"), self).activated.connect(self.on_redo_mask)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self.canvas.toggle_eraser()
        super().keyPressEvent(event)

    def on_eraser_toggle_ui(self, is_eraser):
        self.is_currently_erasing = is_eraser
        
        if is_eraser:
            self.set_tool("ERASER")
        else:
            self.set_tool("BRUSH")

    def set_tool(self, tool):
        if tool not in ["NONE", "ERASER"] and getattr(self, 'is_currently_erasing', False):
            self.canvas.toggle_eraser()
        
        self.canvas.current_tool = tool
        for btn in self.tools.buttons.values(): 
            btn.setChecked(False)
        
        if tool == "NONE":
            self.canvas.setDragMode(QGraphicsView.ScrollHandDrag)
            self.canvas.cursor_item.hide()
            self.tools.buttons["MOVE"].setChecked(True)
            self.mode_lbl.setText("MODE: MOVING")
            self.mode_lbl.setStyleSheet("color: #888888; font-weight: bold;")
            
        else:
            self.canvas.setDragMode(QGraphicsView.NoDrag)
            self.canvas.cursor_item.show()
            
            mapping = {"BRUSH": "BRUSH", "ERASER": "ERASER", "RECT": "RECT", "LASSO": "LASSO"}
            if tool in mapping: 
                self.tools.buttons[mapping[tool]].setChecked(True)
            
            if tool == "ERASER":
                self.mode_lbl.setText("MODE: ERASING")
                self.mode_lbl.setStyleSheet("color: #00d4ff; font-weight: bold;")
            else:
                self.mode_lbl.setText("MODE: PAINTING")
                self.mode_lbl.setStyleSheet(f"color: {Config.COLOR_ACCENT}; font-weight: bold;")

    #/////////////////////////////////#
    #      HISTORY OPERATIONS         #
    #/////////////////////////////////#

    def on_undo_image(self):
        res = self.history.pop_image_undo(self.canvas.cv_img)
        if res:
            x, y, p = res
            self.canvas.cv_img[y:y+p.shape[0], x:x+p.shape[1]] = p
            self.canvas.set_image(self.canvas.cv_img)

    def on_redo_image(self):
        res = self.history.pop_image_redo(self.canvas.cv_img)
        if res:
            x, y, p = res
            self.canvas.cv_img[y:y+p.shape[0], x:x+p.shape[1]] = p
            self.canvas.set_image(self.canvas.cv_img)

    def on_undo_mask(self):
        res = self.history.pop_mask_undo(self.canvas.mask)
        if res:
            self.canvas.mask = res
            self.canvas.update_mask_display()

    def on_redo_mask(self):
        res = self.history.pop_mask_redo(self.canvas.mask)
        if res:
            self.canvas.mask = res
            self.canvas.update_mask_display()

    #/////////////////////////////////#
    #      AI EXECUTION PIPELINE      #
    #/////////////////////////////////#

    def on_task_finished(self, result, patches):
        if patches: 
            for x, y, p in patches: self.history.push_image_action(x, y, p)
            self.canvas.set_image(result)
            self.canvas.clear_mask()
            
            if self.is_batching:
                self.stop_thread()
                is_last = self.batch_engine.save_current(self.canvas.cv_img)
                if is_last: self.finalize_batch()
                else: self.step_batch()
                return
        else: 
            h, w = result.shape[:2]
            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            rgba[result > 0] = [255, 0, 0, 160] 
            self.canvas.mask = QImage(rgba.data, w, h, w*4, QImage.Format_ARGB32).copy()
            self.canvas.update_mask_display()
            if self.is_batching:
                self.stop_thread()
                self.on_lama_clean()
                return

        self.stop_thread()

    def on_auto_scan(self):
        if self.canvas.cv_img is None or self.worker_thread: return
        self.run_thread("ocr", self.canvas.cv_img)

    def on_lama_clean(self):
        if self.canvas.cv_img is None or self.worker_thread: return
        ptr = self.canvas.mask.bits()
        mask_np = np.frombuffer(ptr, np.uint8).reshape((self.canvas.mask.height(), self.canvas.mask.width(), 4))
        mask_gray = mask_np[:, :, 3].copy()
        
        t_size = self.t_slider.slider.value() * 512
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.run_thread("clean", self.canvas.cv_img, mask_gray, t_size)

    def run_thread(self, task, *args):
        self.setCursor(Qt.WaitCursor)
        self.worker_thread = QThread()
        self.worker = AIWorker()
        self.worker.moveToThread(self.worker_thread)
        if task == "ocr": self.worker_thread.started.connect(lambda: self.worker.run_ocr(args[0], "ENG"))
        else: self.worker_thread.started.connect(lambda: self.worker.run_clean(args[0], args[1], args[2]))
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_task_finished)
        self.worker.error.connect(self.on_task_error)
        self.worker_thread.start()

    def on_task_error(self, message):
        self.stop_thread()
        self.is_batching = False
        AIManager.set_persistence(False)
        QMessageBox.critical(self, "Hardware Error", message)

    def stop_thread(self):
        self.setCursor(Qt.ArrowCursor)
        self.progress_bar.setVisible(False)
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None

    #/////////////////////////////////#
    #    BATCH & PHOTOSHOP BRIDGE     #
    #/////////////////////////////////#

    def on_start_batch(self):
        if self.file_list.count() == 0: return
        fmt, ok = QInputDialog.getItem(self, "Batch Setup", "Format:", ["jpg", "png", "photoshop"], 0, False)
        if not ok: return
        paths = [self.file_list.item(i).data(Qt.UserRole) for i in range(self.file_list.count())]
        self.batch_engine.initialize_batch(paths, fmt)
        AIManager.set_persistence(True)
        self.is_batching = True
        self.step_batch()

    def step_batch(self):
        path = self.batch_engine.get_next()
        if path:
            img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
            self.canvas.set_image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            self.on_auto_scan()

    def finalize_batch(self):
        self.is_batching = False
        AIManager.set_persistence(False)
        AIManager.flush()
        
        if self.batch_engine.export_format == "photoshop":
            self.setCursor(Qt.WaitCursor)
            PhotoshopBridge.open_batch_in_ps(self.batch_engine.files, self.batch_engine.output_dir)
            self.setCursor(Qt.ArrowCursor)
            
        QMessageBox.information(self, "Batch Complete", f"Saved to: {self.batch_engine.output_dir}")

    #/////////////////////////////////#
    #        FILE OPERATIONS          #
    #/////////////////////////////////#

    def on_open_folder(self):
        p = QFileDialog.getExistingDirectory(self, "Select Folder")
        if p:
            self.file_list.clear()
            for f in sorted(os.listdir(p)):
                if f.lower().endswith(('.jpg','.jpeg','.png','.webp')):
                    self.file_list.add_file(os.path.join(p, f))

    def on_file_clicked(self, it):
        path_real = it.data(Qt.UserRole)
        img_data = np.fromfile(path_real, dtype=np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

        if img is not None:
            self.history = HistoryManager(Config.MAX_HISTORY)
            self.canvas.set_image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        else:
            QMessageBox.warning(self, "Load Error", f"The file is corrupted or cannot be processed:\n{os.path.basename(path_real)}")
            logger.error(f"Failed to decode image: {path_real}")

    def on_export(self, fmt):
        if self.canvas.cv_img is None: return
        path, _ = QFileDialog.getSaveFileName(self, "Export", "", f"{fmt.upper()} (*.{fmt})")
        if path:
            img_bgr = cv2.cvtColor(self.canvas.cv_img, cv2.COLOR_RGB2BGR)
            ext = os.path.splitext(path)[1]
            is_success, im_buf_arr = cv2.imencode(ext, img_bgr)
            if is_success:
                im_buf_arr.tofile(path)

    def on_photoshop_bridge(self):
        if self.canvas.cv_img is None: return
        it = self.file_list.currentItem()
        if not it: return
        orig = cv2.cvtColor(cv2.imread(it.data(Qt.UserRole)), cv2.COLOR_BGR2RGB)
        PhotoshopBridge.send_to_ps(orig, self.canvas.cv_img)

    def update_telemetry(self):
        ram, gpu = self.monitor.get_stats()
        self.hw_mon.lbl.setText(f"{'GPU' if gpu else 'CPU'} | RAM: {ram}MB")
        self.hw_mon.bar.setValue(min(ram // 40, 100))