from PySide6 import QtWidgets, QtGui, QtCore
import sys, math

class Arrow(QtWidgets.QWidget):
    # 保持不变（这是 QWidget，没问题）
    def __init__(self, start_item: QtWidgets.QWidget, end_item: QtWidgets.QWidget, color: QtGui.QColor | str, parent=None, angle=None):
        super().__init__(parent)
        self.start_item = start_item
        self.end_item = end_item
        self.color = QtGui.QColor(color)
        
        self._original_arrow = QtGui.QPolygonF([
            QtCore.QPointF(0.0, 10.0),
            QtCore.QPointF(50.0, 10.0),
            QtCore.QPointF(50.0, 0.0),
            QtCore.QPointF(80.0, 20.0),
            QtCore.QPointF(50.0, 40.0),
            QtCore.QPointF(50.0, 30.0),
            QtCore.QPointF(0.0, 30.0)
        ])
        
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        self.percent = 1.0
        self.angle = angle

    def sizeHint(self):
        return QtCore.QSize(80, 40)

    def minimumSizeHint(self):
        return QtCore.QSize(20, 10)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        orig_w, orig_h = 80.0, 40.0
        scale = min(w / orig_w, h / orig_h)

        # 计算逻辑坐标下的缩放后尺寸
        scaled_w = orig_w * scale
        scaled_h = orig_h * scale

        # widget 中心
        center_x = w / 2.0
        center_y = h / 2.0

        # 构建变换：将原始箭头 -> 缩放 -> 旋转 -> 居中到 widget
        transform = QtGui.QTransform()

        # 1. 平移到 widget 中心
        transform.translate(center_x, center_y)

        # 2. 旋转（绕原点，所以先旋转再缩放/反向平移）
        if self.angle is not None:
            transform.rotate(self.angle)

        # 3. 缩放
        transform.scale(scale, scale)

        # 4. 平移回原始箭头中心的负值（使旋转中心在箭头中心）
        transform.translate(-orig_w / 2.0, -orig_h / 2.0)

        arrow_transformed = transform.map(self._original_arrow)

        painter.setPen(QtGui.QPen(self.color, max(1, 2 * scale)))
        painter.setBrush(QtGui.QBrush(self.color))
        painter.drawPolygon(arrow_transformed)
        painter.end()

class Circle(QtWidgets.QGraphicsItem):
    def __init__(self, color: QtGui.QColor | str, pen_width=6, diameter=10,thickness=QtCore.Qt.RoundCap):
        super().__init__()
        self.color = QtGui.QColor(color)
        self.pen_width = pen_width
        self.percent = 1.0
        self.thickness = thickness
        self._size = diameter  # 默认直径

    def setSize(self, size: float):
        """动态设置圆的直径"""
        self.prepareGeometryChange()
        self._size = size
        self.update()

    def boundingRect(self):
        # 返回本地坐标系包围矩形（包含 pen 宽度）
        margin = self.pen_width / 2 + 2
        return QtCore.QRectF(-self._size/2 - margin, -self._size/2 - margin,
                             self._size + 2*margin, self._size + 2*margin)

    def paint(self, painter: QtGui.QPainter, option, widget):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(self.color, self.pen_width)
        pen.setCapStyle(self.thickness)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        # 画圆弧（从12点开始）
        rect = QtCore.QRectF(-self._size/2, -self._size/2, self._size, self._size)
        painter.drawArc(rect, 90 * 16, -int(360 * self.percent * 16))

    def change_percent(self, percent: float):
        self.percent = max(0.0, min(1.0, percent))
        self.update()


# ✅ 修正：LoadingRingTextItem 继承 QGraphicsItem
class LoadingRingTextItem(QtWidgets.QGraphicsItem):
    def __init__(self, color_ring: QtGui.QColor, color_text: QtGui.QColor, pen_width=6, parent_scene: QtWidgets.QGraphicsScene=None):
        super().__init__()
        self.color_ring = color_ring
        self.color_text = color_text
        self.pen_width = pen_width
        self.percent = 1.0
        self._diameter = 150  # 外环直径
        if parent_scene:
            self._diameter = min(parent_scene.width(), parent_scene.height()) - 50

        self.begin_circle = Circle(color_ring, pen_width)
        self.end_circle = Circle(color_ring, pen_width)

    def setDiameter(self, diameter: float):
        self.prepareGeometryChange()
        self._diameter = diameter
        self.update()

    def boundingRect(self):
        margin = self.pen_width + 25
        return QtCore.QRectF(
            -self._diameter/2 - margin, -self._diameter/2 - margin,
            self._diameter + 2*margin, self._diameter + 2*margin
        )

    def paint(self, painter: QtGui.QPainter, option, widget):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # 画进度环
        pen = QtGui.QPen(self.color_ring, self.pen_width)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        rect = QtCore.QRectF(-self._diameter/2, -self._diameter/2, self._diameter, self._diameter)
        painter.drawArc(rect, 90 * 16, -int(360 * self.percent * 16))

        # 画文字
        font_size = max(8, int(self._diameter / 8))
        painter.setFont(QtGui.QFont("Arial", font_size, QtGui.QFont.Bold))
        painter.setPen(QtGui.QPen(self.color_text))
        painter.drawText(rect, QtCore.Qt.AlignCenter, f"{int(self.percent * 100)}%")

    def change_percent(self, percent: float):
        self.percent = max(0.0, min(1.0, percent))
        self.update()
        # 更新子圆位置
        self._update_circle_positions()

    def _update_circle_positions(self):
        if not self.scene():
            return

        radius = self._diameter / 2 - self.pen_width
        small_size = min(20, self._diameter / 6)

        # 设置子圆大小
        self.begin_circle.setSize(small_size)
        self.end_circle.setSize(small_size)

        # 起始点（12点钟）
        self.begin_circle.setPos(0, -radius-self.pen_width)

        # 末端点
        angle = -2 * math.pi * self.percent + math.pi / 2
        end_x = (radius+self.pen_width) * math.cos(angle)
        end_y = (-radius-self.pen_width) * math.sin(angle)
        self.end_circle.setPos(end_x, end_y)

    def sceneChanged(self):
        # 当被加入 scene 时，添加子 item
        if self.scene():
            self.scene().addItem(self.begin_circle)
            self.scene().addItem(self.end_circle)
            self._update_circle_positions()

class LoadingRingText(QtWidgets.QGraphicsView):
    def __init__(self, color_ring: QtGui.QColor, color_text: QtGui.QColor, size=200,pen_width=6):
        super().__init__()
        self._scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self._scene)
        self.ringtext = LoadingRingTextItem(color_ring, color_text, pen_width)
        self._scene.addItem(self.ringtext)
        self._scene.setSceneRect(0, 0, size, size)
        # 触发子 item 添加
        self.ringtext.sceneChanged()
        self.setSceneRect(self.ringtext.boundingRect())
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

    def change_percent(self, percent: float):
        self.ringtext.change_percent(percent)

class LoadingLineItem(QtWidgets.QGraphicsItem):
    def __init__(self, color: QtGui.QColor, length=300, pen_width=4, parent: QtWidgets.QWidget=None):
        super().__init__()
        self.color = color
        self.length = length
        self.percent = 1.0
        if parent:
            length = parent.width()
        self.pen_width = pen_width

    def boundingRect(self):
        return QtCore.QRectF(0, -self.pen_width/2, self.length, self.pen_width)
    
    def paint(self, painter: QtGui.QPainter, option, widget):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(self.color, self.pen_width)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QtCore.QPointF(0.0, 0.0), QtCore.QPointF(self.length*self.percent, 0.0))
    
    def change_length(self, percent: float):
        self.percent = percent
        self.update()

class LoadingLine(QtWidgets.QGraphicsView):
        
    def __init__(self, color: QtGui.QColor, length=300, pen_width=4, parent_widget: QtWidgets.QWidget=None, circle_size=10):
        super().__init__()
        self.color = color
        self.length = length - circle_size*2 - pen_width*3
        self.circle_size = circle_size

        self._scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self._scene)
        if parent_widget:
            self.length = parent_widget.width()-circle_size*2
        

        # 起始点与末端点的圆圈
        self.circle_target = Circle(color, pen_width)
        self.circle_tail = Circle(color, pen_width)
        self.circle_target.setSize(self.circle_size)
        self.circle_tail.setSize(self.circle_size)
        self.scene().addItem(self.circle_target)
        self.scene().addItem(self.circle_tail)
        self.circle_tail.setPos(0,0)
        self.circle_target.setPos(self.length, 0)

        # 进度条线
        self.line_item = LoadingLineItem(color, self.length, pen_width, None)
        self.scene().addItem(self.line_item)

        # 布局调整
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setFixedHeight(self.circle_size+2*pen_width)
        self.setSceneRect(self._scene.itemsBoundingRect())
    
    def change_percent(self, percent: float):
        percent = max(0.0, min(1.0, percent))
        self.line_item.change_length(percent)
        self.circle_tail.setPos(self.length * percent, 0)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout()

    # 创建场景和视图
    loading_ring = LoadingRingText(
        color_ring=QtGui.QColor("#4CAF50"), 
        color_text=QtGui.QColor("#8EBAB7"), 
        pen_width=4
    )
    layout.addWidget(loading_ring, 0, QtCore.Qt.AlignCenter)

    window.setLayout(layout)
    window.resize(400, 300)
    window.show()

    loading_line = LoadingLine(
        color=QtGui.QColor("#FF5722"),
        length=loading_ring.width(),
        pen_width=3
    )
    layout.addWidget(loading_line, 0, QtCore.Qt.AlignCenter)
    window.setStyleSheet('border: 1px solid red')
    print(loading_ring.width(), loading_line._scene.width())

    # 动画
    timer = QtCore.QTimer()
    def update_item():
        new_percent = (loading_ring.ringtext.percent + 0.005) % 1.0
        loading_ring.change_percent(new_percent)
        loading_line.change_percent(new_percent)
    timer.timeout.connect(update_item)
    timer.start(30)

    sys.exit(app.exec())