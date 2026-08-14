import cv2
import numpy as np
from src.backend.ai_manager import AIManager
from src.utils.logger import logger

#/////////////////////////////////#
#    DYNAMIC ROI CLEANING ENGINE  #
#/////////////////////////////////#

class ImageProcessor:
    @staticmethod
    def run_ocr_logic(cv_img, language="ENG"):
        engine = AIManager.get_ocr()
        if not engine: return np.zeros(cv_img.shape[:2], dtype=np.uint8)

        # Strip alpha channel just for AI Inference
        if len(cv_img.shape) == 3 and cv_img.shape[2] == 4:
            cv_img_rgb = cv_img[:, :, :3]
        else:
            cv_img_rgb = cv_img

        h, w = cv_img_rgb.shape[:2]
        ph, pw = ((h + 31) // 32 * 32), ((w + 31) // 32 * 32)
        pad_h, pad_w = ph - h, pw - w
        
        padded = cv2.copyMakeBorder(cv_img_rgb, 0, pad_h, 0, pad_w, cv2.BORDER_CONSTANT, value=[0,0,0])
        img_data = padded.astype(np.float32) / 255.0
        img_data = np.transpose(img_data, (2, 0, 1))[np.newaxis, :]

        outputs = engine.run(img_data)
        heatmap = outputs[0][0][0]
        heatmap = heatmap[0:h, 0:w]
        
        mask = (heatmap > 0.3).astype(np.uint8) * 255
        
        #/////////////////////////////////#
        #     4% DYNAMIC MASK DILATION    #
        #/////////////////////////////////#
        k_size = max(11, int(w * 0.04)) 
        if k_size % 2 == 0: k_size += 1
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        logger.info(f"[+] OCR Mask Ready: {k_size}px (3% expansion)")
        return mask

    @staticmethod
    def run_clean_logic(cv_img, mask_img, max_tile_size, progress_callback=None):
        engine = AIManager.get_lama()
        if not engine: return cv_img, []

        h, w = cv_img.shape[:2]
        output = cv_img.copy().astype(np.float32)
        history = []

        _, labels, stats, _ = cv2.connectedComponentsWithStats(mask_img, connectivity=8)
        blobs = [stats[i] for i in range(1, len(stats)) if stats[i, 4] > 5]
        
        total = len(blobs)
        processed_mask = np.zeros_like(mask_img)
        
        for idx, blob in enumerate(sorted(blobs, key=lambda x: x[4], reverse=True)):
            bx, by, bw, bh, _ = blob
            if np.all(processed_mask[by:by+bh, bx:bx+bw] == 255): continue

            cx, cy = bx + bw//2, by + bh//2
            x1 = max(0, cx - max_tile_size//2)
            y1 = max(0, cy - max_tile_size//2)
            x2 = min(w, x1 + max_tile_size)
            y2 = min(h, y1 + max_tile_size)
            x1 = max(0, x2 - max_tile_size)
            y1 = max(0, y2 - max_tile_size)

            tile_img = cv_img[y1:y2, x1:x2]
            tile_mask = mask_img[y1:y2, x1:x2]
            th, tw = tile_img.shape[:2]

            # Strip Alpha for AI inference to prevent ONNX crash
            if len(tile_img.shape) == 3 and tile_img.shape[2] == 4:
                tile_img_rgb = tile_img[:, :, :3]
            else:
                tile_img_rgb = tile_img

            #/////////////////////////////////#
            #     SNAP-TO-8 PADDING LOGIC     #
            #/////////////////////////////////#
            ph, pw = ((th + 7) // 8 * 8), ((tw + 7) // 8 * 8)
            pad_h, pad_w = ph - th, pw - tw
            
            inp_img = cv2.copyMakeBorder(tile_img_rgb, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT)
            inp_img = inp_img.astype(np.float32) / 255.0
            inp_img = np.transpose(inp_img, (2, 0, 1))[np.newaxis, :]
            
            inp_mask = cv2.copyMakeBorder(tile_mask, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT)
            inp_mask = (inp_mask > 127).astype(np.float32)[np.newaxis, np.newaxis, :]

            res = engine.run({'image': inp_img, 'mask': inp_mask})[0][0]
            res = np.clip(np.transpose(res, (1, 2, 0)) * 255, 0, 255).astype(np.uint8)
            res = res[0:th, 0:tw]

            history.append((x1, y1, output[y1:y2, x1:x2].copy().astype(np.uint8)))

            # Apply generated pixels and restore Alpha opacity (set alpha = 255)
            if len(output.shape) == 3 and output.shape[2] == 4:
                output[y1:y2, x1:x2, :3] = res.astype(np.float32)
                output[y1:y2, x1:x2, 3] = 255
            else:
                output[y1:y2, x1:x2] = res.astype(np.float32)

            processed_mask[y1:y2, x1:x2] = 255

            if progress_callback: progress_callback(int((idx/total)*100))

        return output.astype(np.uint8), history
