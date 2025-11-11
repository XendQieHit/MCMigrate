from PySide6 import QtWidgets, QtGui, QtCore
import sys, math

def size_adapt(parent: QtWidgets.QWidget | None, size: int | None, default_size: int) -> int:
    if parent:
        return min(parent.width(), parent.height())
    else: return size if size else default_size

class Pending(QtWidgets.QWidget):
    def __init__(self, color: QtGui.QColor | str, size=24, parent=None):
        super().__init__(parent)
        self.color = QtGui.QColor(color)
        self.dot_diameter = 5
        self.setFixedSize(3 * self.dot_diameter + 20, self.dot_diameter + 10)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        brush = QtGui.QBrush(self.color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(brush)
        for i in range(3):
            x = i * (self.dot_diameter+5) + 5
            painter.drawEllipse(x, self.dot_diameter/2 + 2.5, self.dot_diameter, self.dot_diameter)
        painter.setPen(QtGui.QPen(self.color))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.end()

# 错误❌
class Failed(QtWidgets.QWidget):
    def __init__(self, color: QtGui.QColor | str, size=24, parent=None):
        super().__init__(parent)
        self.color = QtGui.QColor(color)
        self._size = size_adapt(parent, size, 24)
        self.setFixedSize(self._size, self._size)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(self.color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(4, 4, self._size - 4, self._size - 4)
        painter.drawLine(self._size - 4, 4, 4, self._size - 4)
        painter.end()

# 完成✔
class Completed(QtWidgets.QWidget):
    def __init__(self, color: QtGui.QColor | str, size=24, parent=None):
        super().__init__(parent)
        self.color = QtGui.QColor(color)
        self._size = size_adapt(parent, size, 24)
        self.setFixedSize(self._size, self._size)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(self.color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(4, self._size//2, self._size//2, self._size - 4)
        painter.drawLine(self._size//2, self._size - 4, self._size - 4, 4)
        painter.end()

# 终止键图标
class Terminate(QtWidgets.QLabel):
    def __init__(self, color: QtGui.QColor, pen_width: int = 4, size: int = None, parent: QtWidgets.QWidget = None):
        super().__init__(parent=parent)
        self.color = color
        self.pen_width = pen_width
        self._size = size_adapt(parent, size, 24)
        self.setFixedSize(self._size, self._size)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        # 设置画笔
        pen = QtGui.QPen(self.color)
        pen.setWidth(self.pen_width)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)  # 仅描边，不填充

        # 获取绘制区域
        rect = self.rect()
        margin = self.pen_width
        inner_rect = rect.adjusted(margin, margin, -margin, -margin)
        center = inner_rect.center()
        radius = min(inner_rect.width(), inner_rect.height()) // 2 - 2

        if radius <= 0:
            return

        # 1. 绘制圆环（去掉顶部一段，形成“缺口”）
        # 圆环从 45° 到 315°（即绕一圈但留出顶部60度缺口）
        start_angle = 135 * 16  # Qt 使用 1/16 度为单位
        span_angle = 270 * 16  # 270度的弧
        margin_arc = inner_rect.width()*0.05
        painter.drawArc(inner_rect.adjusted(margin_arc, margin_arc, -margin_arc, -margin_arc), start_angle, span_angle)

        # 2. 绘制顶部竖线（电源按钮的经典“棒”）
        line_length = radius * 0.7
        top_y = center.y() - radius
        line_top = QtCore.QPointF(rect.width()/2, top_y)
        line_bottom = QtCore.QPointF(rect.width()/2, top_y + line_length)
        painter.drawLine(line_top, line_bottom)

    def sizeHint(self):
        return QtCore.QSize(self._size, self._size)

    def minimumSizeHint(self):
        return self.sizeHint()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget()
    window.resize(400, 300)
    window.setLayout(QtWidgets.QHBoxLayout())
    window.layout().addWidget(Pending("#2196F3"), 0, QtCore.Qt.AlignCenter)
    window.layout().addWidget(Failed("#F44336"), 0, QtCore.Qt.AlignCenter)
    window.layout().addWidget(Completed("#4CAF50"), 0, QtCore.Qt.AlignCenter)
    window.layout().addWidget(Terminate("#2196F3", size=36), 0, QtCore.Qt.AlignCenter)
    window.show()
    sys.exit(app.exec())