import os
import cv2
import tempfile
import numpy as np
from src.utils.logger import logger

#/////////////////////////////////#
#     PHOTOSHOP COM INTEROP       #
#/////////////////////////////////#

class PhotoshopBridge:
    @staticmethod
    def send_to_ps(original_rgb: np.ndarray, cleaned_rgb: np.ndarray) -> str:
        """Single page transfer (Manual Mode)"""
        try:
            import win32com.client
            ps = win32com.client.Dispatch("Photoshop.Application")
            
            temp_path = tempfile.gettempdir()
            orig_file = os.path.join(temp_path, "mc_transfer_orig.png")
            clean_file = os.path.join(temp_path, "mc_transfer_clean.png")
            
            if len(original_rgb.shape) == 3 and original_rgb.shape[2] == 4:
                cv2.imwrite(orig_file, cv2.cvtColor(original_rgb, cv2.COLOR_RGBA2BGRA))
            else:
                cv2.imwrite(orig_file, cv2.cvtColor(original_rgb, cv2.COLOR_RGB2BGR))

            if len(cleaned_rgb.shape) == 3 and cleaned_rgb.shape[2] == 4:
                cv2.imwrite(clean_file, cv2.cvtColor(cleaned_rgb, cv2.COLOR_RGBA2BGRA))
            else:
                cv2.imwrite(clean_file, cv2.cvtColor(cleaned_rgb, cv2.COLOR_RGB2BGR))

            ps.Open(orig_file)
            doc = ps.ActiveDocument
            doc.ActiveLayer.Name = "Original"

            ps.Open(clean_file)
            ps.ActiveDocument.Selection.SelectAll()
            ps.ActiveDocument.Selection.Copy()
            ps.ActiveDocument.Close(2) 

            doc.Paste()
            doc.ActiveLayer.Name = "MangaCleaner_Result"
            return "Success"
        except Exception as e:
            logger.error(f"[X] Photoshop Bridge Exception:", exc_info=True)
            return str(e)

    @staticmethod
    def open_batch_in_ps(orig_paths: list, clean_dir: str):
        """Opens entire batch as layers after AI finishes"""
        try:
            import win32com.client
            ps = win32com.client.Dispatch("Photoshop.Application")
            logger.info(f"[+] Initializing Photoshop Batch for {len(orig_paths)} pages...")

            for i, orig_path in enumerate(orig_paths):
                
                ps.Open(orig_path)
                doc = ps.ActiveDocument
                doc.ActiveLayer.Name = f"Page_{i+1}_Original"
                
                clean_name = os.path.splitext(os.path.basename(orig_path))[0] + "_cleaned.jpg"
                clean_path = os.path.join(clean_dir, clean_name)
                
                if os.path.exists(clean_path):
                    ps.Open(clean_path)
                    ps.ActiveDocument.Selection.SelectAll()
                    ps.ActiveDocument.Selection.Copy()
                    ps.ActiveDocument.Close(2)
                    
                    doc.Paste()
                    doc.ActiveLayer.Name = f"Page_{i+1}_Cleaned"
                
                logger.info(f"    - Page {i+1} merged in PS")
            
            return True
        except Exception as e:
            logger.error(f"[X] Photoshop Batch Failed: {e}")
            return False
