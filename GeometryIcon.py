from PySide6 import QtWidgets, QtGui, QtCore
import sys, math

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

class Failed(QtWidgets.QWidget):
    def __init__(self, color: QtGui.QColor | str, size=24, parent=None):
        super().__init__(parent)
        self.color = QtGui.QColor(color)
        self._size = size
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

class Completed(QtWidgets.QWidget):
    def __init__(self, color: QtGui.QColor | str, size=24, parent=None):
        super().__init__(parent)
        self.color = QtGui.QColor(color)
        self._size = size
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

class Arrow(QtWidgets.QLabel):
    def __init__(self, color: QtGui.QColor, angle=0.0):
        self.color = color
        self.angle = angle
        self.arrow = QtGui.QPolygonF([

        ])

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QBrush(self.color))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawPolygon()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget()
    window.resize(400, 300)
    window.setLayout(QtWidgets.QHBoxLayout())
    window.layout().addWidget(Pending("#2196F3"), 0, QtCore.Qt.AlignCenter)
    window.layout().addWidget(Failed("#F44336"), 0, QtCore.Qt.AlignCenter)
    window.layout().addWidget(Completed("#4CAF50"), 0, QtCore.Qt.AlignCenter)
    window.show()
    sys.exit(app.exec())