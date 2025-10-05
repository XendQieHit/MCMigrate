from PySide6 import QtWidgets, QtGui, QtCore
import sys, math

class Arrow(QtWidgets.QWidget):
    def __init__(self, start_item: QtWidgets.QWidget, end_item: QtWidgets.QWidget, color: QtGui.QColor | str, parent=None):
        super().__init__(parent)
        self.start_item = start_item
        self.end_item = end_item
        self.color = QtGui.QColor(color)
        
        # 定义原始箭头（标准尺寸 80x40）
        self._original_arrow = QtGui.QPolygonF([
            QtCore.QPointF(0.0, 10.0),
            QtCore.QPointF(50.0, 10.0),
            QtCore.QPointF(50.0, 0.0),
            QtCore.QPointF(80.0, 20.0),
            QtCore.QPointF(50.0, 40.0),
            QtCore.QPointF(50.0, 30.0),
            QtCore.QPointF(0.0, 30.0)
        ])
        
        # 不再固定大小！让布局控制
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        
        self.percent = 1.0
        self.angle = 0.0

    def sizeHint(self):
        # 建议默认比例 2:1 (宽:高)
        return QtCore.QSize(80, 40)

    def minimumSizeHint(self):
        return QtCore.QSize(20, 10)  # 允许缩小到很小

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # 获取当前 widget 的宽高
        w = self.width()
        h = self.height()
        
        if w <= 0 or h <= 0:
            return

        # 计算缩放比例（保持原始宽高比 80:40 = 2:1）
        orig_w = 80.0
        orig_h = 40.0
        
        scale_x = w / orig_w
        scale_y = h / orig_h
        
        # 可选：强制等比例缩放（取较小的比例）
        scale = min(scale_x, scale_y)
        scaled_w = orig_w * scale
        scaled_h = orig_h * scale
        
        # 计算居中偏移
        dx = (w - scaled_w) / 2
        dy = (h - scaled_h) / 2

        # 构建变换：先缩放，再平移到居中位置
        transform = QtGui.QTransform()
        transform.translate(dx, dy)
        transform.scale(scale, scale)
        
        # 应用变换到原始箭头
        scaled_arrow = transform.map(self._original_arrow)

        # 绘制
        painter.setPen(QtGui.QPen(self.color, max(1, 2 * scale)))  # 笔触也缩放
        painter.setBrush(QtGui.QBrush(self.color))
        painter.drawPolygon(scaled_arrow)

        painter.end()

class LoadingRingText(QtWidgets.QWidget):
    def __init__(self, color_ring: QtGui.QColor, color_text: QtGui.QColor, pen_width = 6, parent: QtWidgets.QWidget=None):
        super().__init__(parent=parent)
        self.color_ring = color_ring
        self.color_text = color_text
        self.pen_width = pen_width
        self.percent = 1.0
        if parent:
            print(1)
            self.setFixedSize(QtCore.QSize(parent.width()*0.7, parent.height()*0.7))
            boundary = min(self.parentWidget().rect().width(), self.parentWidget().rect().height())
            self.rect().setRect(0, 0, boundary*0.8, boundary*0.8)
        else: 
            self.setFixedSize(75, 75)
            self.rect().setRect(0, 0, 75, 75)
            print(2)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        pen = QtGui.QPen(self.color_ring, self.pen_width)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(self.rect().marginsRemoved(QtCore.QMargins(4, 4, 4, 4)), 90 * 16, -int(360 * self.percent * 16))

        painter.setFont(QtGui.QFont("Arial", self.size().width() // 5.5, QtGui.QFont.Bold))
        painter.setPen(QtGui.QPen(self.color_text))
        painter.drawText(self.rect(), QtCore.Qt.AlignCenter, f"{int(self.percent*100)}%")

        # Rect render(debug)
        # painter.setPen(QtGui.QPen(QtGui.QColor("#000000"), 1))
        # painter.drawRect(self.rect().marginsRemoved(QtCore.QMargins(4, 4, 4, 4)))
        # painter.setPen(QtGui.QPen(QtGui.QColor('#44aaba'), 1))
        # painter.drawRect(self.rect())

        painter.end()
    
    def change_percent(self, percent: float):
        self.percent = percent
        self.update()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout()

    ring = LoadingRingText(QtGui.QColor("#4CAF50"), QtGui.QColor("#8EBAB7"))
    ring.setFixedSize(40, 40)
    layout.addWidget(ring, 0, QtCore.Qt.AlignCenter)

    window.setLayout(layout)
    window.resize(400, 300)
    window.show()
    sys.exit(app.exec())