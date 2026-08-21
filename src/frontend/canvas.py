import os
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, 
                             QGraphicsPathItem, QGraphicsEllipseItem, QLabel)
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBrush, QPainterPath, QIcon
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
import numpy as np
from src.utils.paths import Paths

#/////////////////////////////////#
#   MULTI-TOOL CANVAS ENGINE      #
#/////////////////////////////////#

class MangaCanvas(QGraphicsView):
    mask_changed = Signal()
    tool_state_updated = Signal(bool)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        # --- GENERATE CHECKERBOARD BACKGROUND ---
        grid_size = 10
        checkerboard = QPixmap(grid_size * 2, grid_size * 2)
        checkerboard.fill(QColor(255, 255, 255))
        painter = QPainter(checkerboard)
        painter.fillRect(0, 0, grid_size, grid_size, QColor(200, 200, 200))
        painter.fillRect(grid_size, grid_size, grid_size, grid_size, QColor(200, 200, 200))
        painter.end()
        self.setBackgroundBrush(QBrush(checkerboard))

        self.image_item = QGraphicsPixmapItem()
        self.mask_item = QGraphicsPixmapItem()
        self.mask_item.setOpacity(60 / 100.0)
        self.scene.addItem(self.image_item)
        self.scene.addItem(self.mask_item)

        self.cursor_item = QGraphicsEllipseItem()
        self.cursor_item.setZValue(1000)
        self.scene.addItem(self.cursor_item)

        self.current_tool = "NONE"
        self.brush_size = 40
        self.is_drawing = False
        self.is_eraser = False 
        self.is_locked = False  
        
        self.last_pt = QPointF()
        self.start_pt = QPointF()
        self.last_drawn_pt = None # Remembers position for Shift+Click straight lines
        self.lasso_path = QPainterPath()
        self.preview_item = QGraphicsPathItem()
        self.preview_item.setPen(QPen(QColor(0, 212, 255, 200), 2, Qt.DashLine))
        self.scene.addItem(self.preview_item)

        # --- BIG CORNER LOCK OVERLAY ---
        self.lock_overlay = QLabel(self)
        lock_path = os.path.join(Paths.BASE_DIR, "assets", "icon_lock.svg")
        if os.path.exists(lock_path):
            self.lock_overlay.setPixmap(QIcon(lock_path).pixmap(48, 48))
        self.lock_overlay.setStyleSheet("background: transparent;")
        self.lock_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)  # Prevent blocking panning
        self.lock_overlay.hide()

        self.cv_img = None
        self.mask = None
        self.setMouseTracking(True)
        self.update_cursor_visuals()

    def resizeEvent(self, event):
        """Keep the lock overlay perfectly positioned in the top right"""
        super().resizeEvent(event)
        self.lock_overlay.move(self.width() - self.lock_overlay.width() - 20, 20)

    def set_locked(self, locked: bool):
        """Toggles the lock state and manages the visual cursor & overlay"""
        self.is_locked = locked
        if locked:
            self.cursor_item.hide()
            self.lock_overlay.show()
        else:
            self.lock_overlay.hide()
            if self.current_tool != "NONE":
                self.cursor_item.show()

    def drawBackground(self, painter, rect):
        painter.save()
        painter.resetTransform()
        painter.fillRect(self.viewport().rect(), QColor(11, 11, 14))
        painter.restore()

        # Draw the non-scaling checkerboard strictly behind the image bounds
        if self.cv_img is not None:
            painter.save()
            painter.setClipRect(self.sceneRect()) # Clip rendering to the image's boundaries
            painter.resetTransform()              # Strip the zoom/pan scaling from the painter
            painter.fillRect(self.viewport().rect(), self.backgroundBrush())
            painter.restore()

    def toggle_eraser(self):
        self.is_eraser = not self.is_eraser
        self.update_cursor_visuals()
        self.tool_state_updated.emit(self.is_eraser)

    def update_cursor_visuals(self):
        if self.is_eraser or self.current_tool == "ERASER":
            self.cursor_item.setPen(QPen(QColor(0, 212, 255, 200), 1))
            self.cursor_item.setBrush(QBrush(QColor(0, 212, 255, 60)))
        else:
            self.cursor_item.setPen(QPen(QColor(255, 0, 0, 200), 1))
            self.cursor_item.setBrush(QBrush(QColor(255, 0, 0, 60)))
        
        r = self.brush_size / 2
        self.cursor_item.setRect(-r, -r, self.brush_size, self.brush_size)

    def set_brush_size(self, size):
        self.brush_size = size
        self.update_cursor_visuals()

    def set_image(self, cv_img):
        self.cv_img = cv_img
        self.last_drawn_pt = None # Reset straight line anchor on new image
        h, w = cv_img.shape[:2]
        # Support RGBA rendering if transparency is present
        if len(cv_img.shape) == 3 and cv_img.shape[2] == 4:
            q_img = QImage(cv_img.data, w, h, w*4, QImage.Format_RGBA8888)
        else:
            q_img = QImage(cv_img.data, w, h, w*3, QImage.Format_RGB888)
        self.image_item.setPixmap(QPixmap.fromImage(q_img))
        self.mask = QImage(w, h, QImage.Format_ARGB32)
        self.mask.fill(Qt.transparent)
        self.update_mask_display()
        self.scene.setSceneRect(0, 0, w, h)

    def update_mask_display(self):
        if self.mask: self.mask_item.setPixmap(QPixmap.fromImage(self.mask))

    def wheelEvent(self, event):
        zoom = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(zoom, zoom)

    def mousePressEvent(self, event):
        # Always allow moving/panning regardless of lock state
        if self.current_tool == "NONE" or event.button() == Qt.RightButton:
            super().mousePressEvent(event)
        elif self.is_locked:
            # If the mask is locked by AI, silently reject all drawing inputs
            return
        elif event.button() == Qt.LeftButton and self.mask:
            self.mask_changed.emit()
            self.is_drawing = True
            curr_pt = self.mapToScene(event.pos())
            
            is_brush_tool = self.current_tool in ["BRUSH", "ERASER"] or self.is_eraser
            
            # Photoshop Shift+Click Straight Line Feature
            if is_brush_tool and (event.modifiers() & Qt.ShiftModifier) and self.last_drawn_pt is not None:
                self.paint_mask_stroke(self.last_drawn_pt, curr_pt)
                self.last_pt = curr_pt
                self.last_drawn_pt = curr_pt
            else:
                self.start_pt = curr_pt
                self.last_pt = curr_pt
                
                if self.current_tool == "LASSO": 
                    self.lasso_path = QPainterPath(self.start_pt)
                elif is_brush_tool:
                    # Instantly paint a dot on a single click without needing to move
                    self.paint_mask_stroke(curr_pt, curr_pt)
                    self.last_drawn_pt = curr_pt

    def mouseMoveEvent(self, event):
        curr_pt = self.mapToScene(event.pos())
        self.cursor_item.setPos(curr_pt)
        if self.is_drawing:
            if self.current_tool in ["BRUSH", "ERASER"] or self.is_eraser:
                self.paint_mask_stroke(self.last_pt, curr_pt)
                self.last_pt = curr_pt
                self.last_drawn_pt = curr_pt
            elif self.current_tool == "RECT":
                path = QPainterPath()
                path.addRect(QRectF(self.start_pt, curr_pt).normalized())
                self.preview_item.setPath(path)
            elif self.current_tool == "LASSO":
                self.lasso_path.lineTo(curr_pt)
                self.preview_item.setPath(self.lasso_path)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_drawing:
            curr_pt = self.mapToScene(event.pos())
            if self.current_tool == "RECT": self.paint_mask_rect(self.start_pt, curr_pt)
            elif self.current_tool == "LASSO": self.paint_mask_lasso()
            self.is_drawing = False
            self.preview_item.setPath(QPainterPath())
        super().mouseReleaseEvent(event)

    def get_painter(self):
        painter = QPainter(self.mask)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.current_tool == "ERASER" or self.is_eraser:
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            color = Qt.transparent
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            color = QColor(255, 0, 0, 255)
            
        return painter, color

    def paint_mask_stroke(self, p1, p2):
        painter, color = self.get_painter()
        painter.setPen(QPen(color, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(p1, p2)
        painter.end()
        self.update_mask_display()

    def paint_mask_rect(self, p1, p2):
        painter, color = self.get_painter()
        painter.fillRect(QRectF(p1, p2).normalized(), QBrush(color))
        painter.end()
        self.update_mask_display()

    def paint_mask_lasso(self):
        painter, color = self.get_painter()
        painter.fillPath(self.lasso_path, QBrush(color))
        painter.end()
        self.update_mask_display()

    def set_mask_opacity(self, opacity_percent):
        # Purely cosmetic: Adjusts the UI layer visibility, leaving math matrix intact
        if self.mask_item:
            self.mask_item.setOpacity(opacity_percent / 100.0)

    def clear_mask(self):
        if self.is_locked: return  # Block clearing if AI is working
        if self.mask:
            self.mask_changed.emit()
            self.mask.fill(Qt.transparent)
            self.update_mask_display()
            self.last_drawn_pt = None # Reset anchor when mask is explicitly cleared
