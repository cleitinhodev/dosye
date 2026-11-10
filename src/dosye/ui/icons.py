"""Small vector icons for buttons (drawn with QPainter, crisp at any DPI)."""
import math

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QPainterPath

_cache = {}


def _pen(c, w=1.8):
    return QPen(QColor(c), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)


def _draw(name, p, c):
    p.setPen(_pen(c)); p.setBrush(Qt.NoBrush)
    if name == "sparkle":
        def star(cx, cy, s):
            path = QPainterPath(); path.moveTo(cx, cy - s)
            for dx, dy in ((s, 0), (0, s), (-s, 0), (0, -s)):
                path.quadTo(cx, cy, cx + dx, cy + dy)
            p.setBrush(QColor(c)); p.drawPath(path)
        star(9, 11, 6.5); star(17, 5.5, 3.2); star(17.5, 17, 2.6)
    elif name == "open":
        p.drawPolyline([QPointF(3, 18), QPointF(3, 5.5), QPointF(8.5, 5.5), QPointF(10.5, 7.5), QPointF(18, 7.5), QPointF(18, 10)])
        p.drawPolygon([QPointF(3, 18), QPointF(6.5, 10.5), QPointF(21, 10.5), QPointF(17.5, 18)])
    elif name == "save":
        p.drawRoundedRect(QRectF(4, 4, 16, 16), 2.5, 2.5)
        p.drawRect(QRectF(8, 4, 8, 5)); p.drawRoundedRect(QRectF(7.5, 13, 9, 7), 1, 1)
    elif name == "reset":
        p.drawArc(QRectF(4.5, 4.5, 15, 15), 100 * 16, 290 * 16)
        p.setBrush(QColor(c)); p.drawPolygon([QPointF(3.5, 3.5), QPointF(10, 4.2), QPointF(5.2, 9.2)])
    elif name == "gear":
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        for i in range(16):
            a = math.pi * 2 * i / 16; r = 8.6 if i % 2 == 0 else 6.6
            pt = QPointF(12 + r * math.cos(a), 12 + r * math.sin(a))
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        path.closeSubpath(); p.drawPath(path); p.drawEllipse(QPointF(12, 12), 2.8, 2.8)
    elif name == "help":
        p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
        path = QPainterPath(); path.moveTo(9.2, 9.6); path.cubicTo(9.2, 6.4, 14.8, 6.4, 14.8, 9.6)
        path.cubicTo(14.8, 11.8, 12, 11.8, 12, 14); p.drawPath(path)
        p.setBrush(QColor(c)); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(12, 17), 1.2, 1.2)
    elif name == "info":
        p.drawEllipse(QPointF(12, 12), 8.5, 8.5); p.drawLine(QPointF(12, 11), QPointF(12, 16.5))
        p.setBrush(QColor(c)); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(12, 7.6), 1.2, 1.2)
    elif name == "heart":
        path = QPainterPath(); path.moveTo(12, 19.5)
        path.cubicTo(3, 13.5, 3.5, 5, 8.5, 5); path.cubicTo(10.5, 5, 11.6, 6.3, 12, 7.4)
        path.cubicTo(12.4, 6.3, 13.5, 5, 15.5, 5); path.cubicTo(20.5, 5, 21, 13.5, 12, 19.5)
        p.setBrush(QColor(c)); p.setPen(Qt.NoPen); p.drawPath(path)
    elif name == "export":
        p.drawLine(QPointF(12, 4), QPointF(12, 14.5)); p.drawPolyline([QPointF(7.5, 10.5), QPointF(12, 15), QPointF(16.5, 10.5)])
        p.drawPolyline([QPointF(4.5, 15), QPointF(4.5, 19.5), QPointF(19.5, 19.5), QPointF(19.5, 15)])
    elif name in ("folder_plus", "folder_minus"):
        p.drawPolyline([QPointF(3, 18.5), QPointF(3, 5.5), QPointF(9, 5.5), QPointF(11, 7.5), QPointF(21, 7.5), QPointF(21, 18.5), QPointF(3, 18.5)])
        p.drawLine(QPointF(9, 13), QPointF(15, 13))
        if name == "folder_plus":
            p.drawLine(QPointF(12, 10), QPointF(12, 16))
    elif name == "image":
        p.drawRoundedRect(QRectF(3.5, 5, 17, 14), 2.5, 2.5)
        p.drawPolyline([QPointF(5, 17), QPointF(10, 11.5), QPointF(13.5, 15), QPointF(15.5, 13), QPointF(19, 16.5)])
        p.drawEllipse(QPointF(15.5, 9), 1.6, 1.6)
    elif name == "search":
        p.drawEllipse(QPointF(10.5, 10.5), 6, 6); p.drawLine(QPointF(15, 15), QPointF(20, 20))
    elif name == "globe":
        p.drawEllipse(QPointF(12, 12), 8.5, 8.5); p.drawEllipse(QRectF(8, 3.5, 8, 17))
        p.drawLine(QPointF(3.5, 12), QPointF(20.5, 12))
    elif name == "github":
        p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
        path = QPainterPath(); path.moveTo(9.5, 20); path.lineTo(9.5, 16.5); path.cubicTo(6, 16, 6.5, 12, 8, 10.5)
        path.lineTo(7.8, 7.6); path.lineTo(10, 8.8); path.cubicTo(11.3, 8.4, 12.7, 8.4, 14, 8.8); path.lineTo(16.2, 7.6)
        path.lineTo(16, 10.5); path.cubicTo(17.5, 12, 18, 16, 14.5, 16.5); path.lineTo(14.5, 20); p.drawPath(path)
    elif name == "scale":   # license
        p.drawLine(QPointF(12, 4), QPointF(12, 20)); p.drawLine(QPointF(7, 20), QPointF(17, 20)); p.drawLine(QPointF(5, 7), QPointF(19, 7))
        p.drawPolyline([QPointF(5, 7), QPointF(2.8, 13), QPointF(7.2, 13), QPointF(5, 7)])
        p.drawPolyline([QPointF(19, 7), QPointF(16.8, 13), QPointF(21.2, 13), QPointF(19, 7)])


def icon(name, color="#ECEBFF", size=24):
    key = (name, color, size)
    if key not in _cache:
        ic = QIcon()
        for scale in (1, 2):
            pm = QPixmap(size * scale, size * scale); pm.fill(Qt.transparent); pm.setDevicePixelRatio(scale)
            p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
            p.scale(size / 24.0, size / 24.0)
            _draw(name, p, color); p.end()
            ic.addPixmap(pm)
        _cache[key] = ic
    return _cache[key]
