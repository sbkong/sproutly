"""
ROI 편집 캔버스

배경 이미지 위에 ROI 박스 표시 + 마우스로 이동/리사이즈
"""
import logging
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import QWidget

from sproutly.rois import Roi

log = logging.getLogger('sproutly.roi_canvas')

MIN_BOX_SIZE = 10

HANDLE_HIT_SIZE = 12


@dataclass
class _DragState:
    mode: str  # 'move' | 'resize'
    roi_index: int
    corner: Optional[str] = None  # 'tl' | 'tr' | 'bl' | 'br'
    start_canvas: QPointF = None  # 드래그 시작 시 마우스 좌표 (캔버스)
    start_rect: tuple = None  # 드래그 시작 시 박스 좌표 (이미지)


class RoiCanvas(QWidget):
    selection_changed = Signal(str)  # ROI 이름
    roi_changed = Signal(str)
    roi_deleted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 450)
        self.setMouseTracking(True)

        self._pixmap: Optional[QPixmap] = None
        self._image_w = 1
        self._image_h = 1

        self._rois: list[Roi] = []
        self._selected_index: int = -1

        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0

        self._drag: Optional[_DragState] = None

        self._show_labels = True

    def set_show_labels(self, show: bool):
        self._show_labels = show
        self.update()

    def set_image(self, image_path: str):
        pm = QPixmap(image_path)
        if pm.isNull():
            log.warning(f"이미지 로드 실패: {image_path}")
            return
        self._pixmap = pm
        self._image_w = pm.width()
        self._image_h = pm.height()
        self._calc_transform()
        self.update()

    def set_rois(self, rois: list[Roi]):
        self._rois = [Roi(r.name, r.x1, r.y1, r.x2, r.y2) for r in rois]
        self._selected_index = -1
        self.update()

    def get_rois(self) -> list[Roi]:
        return [Roi(r.name, r.x1, r.y1, r.x2, r.y2) for r in self._rois]

    def select_roi(self, name: str):
        for i, r in enumerate(self._rois):
            if r.name == name:
                self._selected_index = i
                self.update()
                self.selection_changed.emit(name)
                return
        self._selected_index = -1
        self.update()
        self.selection_changed.emit('')

    def update_selected_rect(self, x1: int, y1: int, x2: int, y2: int):
        if self._selected_index < 0:
            return
        r = self._rois[self._selected_index]
        r.x1, r.y1, r.x2, r.y2 = x1, y1, x2, y2
        self.update()
        self.roi_changed.emit(r.name)

    def _calc_transform(self):
        if not self._pixmap:
            return
        cw, ch = self.width(), self.height()
        iw, ih = self._image_w, self._image_h
        if iw == 0 or ih == 0:
            return
        self._scale = min(cw / iw, ch / ih)
        disp_w = iw * self._scale
        disp_h = ih * self._scale
        self._offset_x = (cw - disp_w) / 2
        self._offset_y = (ch - disp_h) / 2

    def _canvas_to_image(self, x: float, y: float) -> tuple[int, int]:
        ix = (x - self._offset_x) / self._scale
        iy = (y - self._offset_y) / self._scale
        return int(round(ix)), int(round(iy))

    def _image_to_canvas(self, x: int, y: int) -> tuple[float, float]:
        return (x * self._scale + self._offset_x,
                y * self._scale + self._offset_y)

    def _roi_canvas_rect(self, roi: Roi) -> QRectF:
        x1, y1 = self._image_to_canvas(roi.x1, roi.y1)
        x2, y2 = self._image_to_canvas(roi.x2, roi.y2)
        return QRectF(x1, y1, x2 - x1, y2 - y1)

    def _hit_test(self, pos: QPointF) -> tuple[int, str]:
        """
        return: (roi_index, action)
        action: 'corner_tl' | 'corner_tr' | 'corner_bl' | 'corner_br' | 'move' | 'none'
        """
        x, y = pos.x(), pos.y()

        if self._selected_index >= 0:
            r = self._rois[self._selected_index]
            rect = self._roi_canvas_rect(r)
            corner = self._corner_hit(rect, x, y)
            if corner:
                return self._selected_index, f'corner_{corner}'

        for i in range(len(self._rois) - 1, -1, -1):
            r = self._rois[i]
            rect = self._roi_canvas_rect(r)
            if rect.contains(x, y):
                return i, 'move'

        return -1, 'none'

    def _corner_hit(self, rect: QRectF, x: float, y: float) -> Optional[str]:
        h = HANDLE_HIT_SIZE / 2
        corners = {
            'tl': (rect.left(), rect.top()),
            'tr': (rect.right(), rect.top()),
            'bl': (rect.left(), rect.bottom()),
            'br': (rect.right(), rect.bottom()),
        }
        for name, (cx, cy) in corners.items():
            if abs(x - cx) <= h and abs(y - cy) <= h:
                return name
        return None

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self._pixmap:
            return
        pos = event.position()
        idx, action = self._hit_test(pos)

        if action == 'none':
            if self._selected_index != -1:
                self._selected_index = -1
                self.selection_changed.emit('')
                self.update()
            return

        if action.startswith('corner_'):
            corner = action.split('_')[1]
            r = self._rois[idx]
            self._drag = _DragState(
                mode='resize',
                roi_index=idx,
                corner=corner,
                start_canvas=pos,
                start_rect=(r.x1, r.y1, r.x2, r.y2),
            )
        elif action == 'move':
            r = self._rois[idx]
            self._drag = _DragState(
                mode='move',
                roi_index=idx,
                start_canvas=pos,
                start_rect=(r.x1, r.y1, r.x2, r.y2),
            )

        if self._selected_index != idx:
            self._selected_index = idx
            self.selection_changed.emit(self._rois[idx].name)
        self.update()

    def mouseMoveEvent(self, event):
        if not self._pixmap:
            return
        pos = event.position()

        if self._drag:
            self._apply_drag(pos)
            return

        idx, action = self._hit_test(pos)
        if action.startswith('corner_'):
            corner = action.split('_')[1]
            if corner in ('tl', 'br'):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif action == 'move':
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _apply_drag(self, pos: QPointF):
        d = self._drag
        r = self._rois[d.roi_index]

        dx_canvas = pos.x() - d.start_canvas.x()
        dy_canvas = pos.y() - d.start_canvas.y()
        dx = int(round(dx_canvas / self._scale))
        dy = int(round(dy_canvas / self._scale))

        x1, y1, x2, y2 = d.start_rect

        if d.mode == 'move':
            new_x1 = x1 + dx
            new_y1 = y1 + dy
            new_x2 = x2 + dx
            new_y2 = y2 + dy
            w = x2 - x1
            h = y2 - y1
            new_x1 = max(0, min(self._image_w - w, new_x1))
            new_y1 = max(0, min(self._image_h - h, new_y1))
            r.x1 = new_x1
            r.y1 = new_y1
            r.x2 = new_x1 + w
            r.y2 = new_y1 + h

        elif d.mode == 'resize':
            corner = d.corner
            nx1, ny1, nx2, ny2 = x1, y1, x2, y2
            if corner == 'tl':
                nx1 = max(0, min(x2 - 1, x1 + dx))
                ny1 = max(0, min(y2 - 1, y1 + dy))
            elif corner == 'tr':
                nx2 = max(x1 + 1, min(self._image_w, x2 + dx))
                ny1 = max(0, min(y2 - 1, y1 + dy))
            elif corner == 'bl':
                nx1 = max(0, min(x2 - 1, x1 + dx))
                ny2 = max(y1 + 1, min(self._image_h, y2 + dy))
            elif corner == 'br':
                nx2 = max(x1 + 1, min(self._image_w, x2 + dx))
                ny2 = max(y1 + 1, min(self._image_h, y2 + dy))
            r.x1, r.y1, r.x2, r.y2 = nx1, ny1, nx2, ny2

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self._drag:
            return

        d = self._drag
        self._drag = None

        r = self._rois[d.roi_index]

        if r.width < MIN_BOX_SIZE or r.height < MIN_BOX_SIZE:
            name = r.name
            del self._rois[d.roi_index]
            self._selected_index = -1
            self.selection_changed.emit('')
            self.roi_deleted.emit(name)
            self.update()
            return

        self.roi_changed.emit(r.name)
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._calc_transform()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#1a1a1a'))

        if not self._pixmap:
            painter.setPen(QColor('#888'))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "이미지 없음")
            return

        target = QRectF(self._offset_x, self._offset_y,
                        self._image_w * self._scale,
                        self._image_h * self._scale)
        painter.drawPixmap(target, self._pixmap, self._pixmap.rect())

        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        for i, r in enumerate(self._rois):
            rect = self._roi_canvas_rect(r)
            is_sel = (i == self._selected_index)

            color = QColor(255, 200, 60, 255) if is_sel else QColor(255, 60, 60, 220)
            pen = QPen(color)
            pen.setWidth(2 if is_sel else 1)
            painter.setPen(pen)
            painter.drawRect(rect)

            if self._show_labels:
                text = r.name
                metrics = painter.fontMetrics()
                tw = metrics.horizontalAdvance(text) + 6
                th = metrics.height() + 2

                if rect.width() < tw or rect.height() < th:
                    pass
                else:
                    lx = int(rect.left()) + 1
                    ly = int(rect.top()) + 1

                    if is_sel:
                        painter.fillRect(lx, ly, tw, th, color)
                        painter.setPen(QColor(0, 0, 0))
                    else:
                        bg = QColor(color)
                        bg.setAlpha(120)
                        painter.fillRect(lx, ly, tw, th, bg)
                        painter.setPen(QColor(255, 255, 255, 200))

                    painter.drawText(lx + 3, ly + metrics.ascent() + 1, text)

            if is_sel:
                hs = HANDLE_HIT_SIZE / 2
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 255, 255))
                for cx, cy in [
                    (rect.left(), rect.top()),
                    (rect.right(), rect.top()),
                    (rect.left(), rect.bottom()),
                    (rect.right(), rect.bottom()),
                ]:
                    painter.drawRect(QRectF(cx - hs, cy - hs,
                                            HANDLE_HIT_SIZE, HANDLE_HIT_SIZE))
                painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.end()
