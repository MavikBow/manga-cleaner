from PySide6.QtCore import QObject, Signal, Slot
import numpy as np
from src.backend.processor import ImageProcessor

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

    @Slot()
    def process(self):
        if self.task == "ocr":
            self.run_ocr(self.args[0], "ENG")
        elif self.task == "clean":
            self.run_clean(self.args[0], self.args[1], self.args[2])

    def run_ocr(self, cv_img, language):
        try:
            mask = ImageProcessor.run_ocr_logic(cv_img, language)
            self.finished.emit(mask, None)
        except Exception as e:
            self.error.emit(str(e))

    def run_clean(self, cv_img, mask_img, max_tile_w):
        try:
            result, patches = ImageProcessor.run_clean_logic(
                cv_img, 
                mask_img, 
                max_tile_w, 
                progress_callback=self.progress.emit
            )
            self.finished.emit(result, patches)
        except Exception as e:
            self.error.emit(str(e))
