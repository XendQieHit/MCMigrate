from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsProxyWidget
)
from PySide6.QtGui import QPainter  # ✅ 导入 QPainter
from PySide6.QtCore import Qt

class RotatableWidget(QGraphicsView):
    def __init__(self, widget: QWidget, rotation=0, parent=None):
        super().__init__(parent)
        # ✅ 正确：使用 QPainter 的 RenderHint
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setOptimizationFlag(QGraphicsView.DontAdjustForAntialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.proxy = self.scene.addWidget(widget)
        self.proxy.setTransformOriginPoint(
            widget.width() / 2, widget.height() / 2
        )
        self.proxy.setRotation(rotation)

        self.setSceneRect(self.proxy.boundingRect())
        self.setFixedSize(widget.size())

# 测试
if __name__ == "__main__":
    app = QApplication([])
    button = QPushButton("旋转我！")
    button.setFixedSize(100, 50)

    rot_view = RotatableWidget(button, rotation=30)
    rot_view.show()

    app.exec()