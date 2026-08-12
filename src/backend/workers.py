import time
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from PySide6.QtCore import QObject, Signal, Slot
from src.backend.processor import ImageProcessor

# Keep a single background process alive so models stay in VRAM
_pool = None
def get_pool():
    global _pool
    if _pool is None:
        _pool = ProcessPoolExecutor(max_workers=1)
    return _pool

# Top-level functions so Windows can send them to the background process
def _run_ocr_process(cv_img, language):
    return ImageProcessor.run_ocr_logic(cv_img, language)

def _run_clean_process(cv_img, mask_img, max_tile_w, queue):
    def cb(prog):
        queue.put(prog)
    return ImageProcessor.run_clean_logic(cv_img, mask_img, max_tile_w, progress_callback=cb)


#/////////////////////////////////#
#     AI ASYNC TASK WORKER        #
#/////////////////////////////////#

class AIWorker(QObject):
    finished = Signal(object, object)
    progress = Signal(int)
    error = Signal(str)

    def __init__(self, task=None, args=None):
        super().__init__()
        self.task = task
        self.args = args
        self.manager = multiprocessing.Manager()

    @Slot()
    def process(self):
        if self.task == "ocr":
            self.run_ocr(self.args[0], "ENG")
        elif self.task == "clean":
            self.run_clean(self.args[0], self.args[1], self.args[2])

    def run_ocr(self, cv_img, language):
        try:
            future = get_pool().submit(_run_ocr_process, cv_img, language)
            
            # Poll the background process without blocking the GUI
            while not future.done():
                time.sleep(0.05)
                
            self.finished.emit(future.result(), None)
        except Exception as e:
            self.error.emit(str(e))

    def run_clean(self, cv_img, mask_img, max_tile_w):
        try:
            q = self.manager.Queue()
            future = get_pool().submit(_run_clean_process, cv_img, mask_img, max_tile_w, q)
            
            # Poll the background process and update UI progress
            while not future.done():
                while not q.empty():
                    self.progress.emit(q.get())
                time.sleep(0.05)
                
            res = future.result()
            self.finished.emit(res[0], res[1])
        except Exception as e:
            self.error.emit(str(e))
