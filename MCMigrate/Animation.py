'''
为了不重复手搓动画而弄的简单动画库
注意！该动画库的动画暂不可与 同动画库里的其他动画一起使用！
以及不能使用在 已经有应用到QGraphicEffect的widget上！
'''
from PySide6 import QtCore, QtWidgets, QtGui, QtSvg
from core import ClientLibs
from typing import Callable

class FadeIn(QtCore.QPropertyAnimation):
    '''淡入动画，使用前请先show()'''
    def __init__(self, widget: QtWidgets.QWidget, duration: int=300):
        self.effect = QtWidgets.QGraphicsOpacityEffect(opacity=0.0)
        widget.setGraphicsEffect(self.effect)
        super().__init__(self.effect, b"opacity")
        self.setDuration(duration)
        self.setStartValue(self.effect.opacity())
        self.setEndValue(1.0)
        self.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

class FadeOut(QtCore.QPropertyAnimation):
    def __init__(self, widget: QtWidgets.QWidget, duration: int=100):
        # 在设置初始值之前，需要检查widget是否已经应用上了QGraphicsEffect
        self.effect = widget.graphicsEffect()
        if not hasattr(self.effect, 'opacity'):
            self.effect = QtWidgets.QGraphicsOpacityEffect(opacity=1.0)
            widget.setGraphicsEffect(self.effect) # 呃呃...感觉这样直接拉满还是有些奇怪的...算了不管了（

        super().__init__(self.effect, b"opacity")
        self.setStartValue(self.effect.opacity())
        self.setDuration(duration)
        self.setEndValue(0.0)
        self.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

class ColorAnimationHelper(QtCore.QObject):
    """辅助对象，用于持有可动画的颜色属性"""
    def __init__(self, color: QtGui.QColor = None, parent=None):
        super().__init__(parent)
        self._color = color or QtGui.QColor()

    def get_color(self) -> QtGui.QColor:
        return self._color

    def set_color(self, color: QtGui.QColor):
        self._color = color

    # 定义可动画的属性
    color = QtCore.Property(QtGui.QColor, get_color, set_color)

class ChangeColor(QtCore.QPropertyAnimation):
    '''
    颜色变化动画
    Args:
        color_role: 需要变化的颜色角色，如QtGui.QPalette.ColorRole.Button
    '''
    def __init__(self, widget: QtWidgets.QWidget, end_color: QtGui.QColor, color_role: QtGui.QPalette.ColorRole=None, start_color: QtGui.QColor=None, duration: int=300):
        self.widget = widget
        self.color_role = color_role
        if not self.color_role:
            self.color_role = self.widget.backgroundRole()
        self._color = ColorAnimationHelper(self.widget.palette().color(self.color_role))
        super().__init__(self._color, b"color")
        self.setDuration(duration)
        if start_color:
            self.setStartValue(start_color)
        self.setEndValue(end_color)
        self.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        self.valueChanged.connect(self.on_value_changed)

    @QtCore.Slot(QtGui.QColor)
    def on_value_changed(self, color: QtGui.QColor):
        palette = self.widget.palette()
        palette.setColor(self.color_role, color)
        self.widget.setPalette(palette)

class ChangeButtonIconColorTransiting(QtCore.QPropertyAnimation):
    '''适配纯色图形的，由原颜色变化至指定颜色的动画'''
    def __init__(self, button: QtWidgets.QPushButton, icon_gen: ClientLibs.ColorIconGenerator, end_color: QtGui.QColor, duration: int=300):
        self.icon_gen = icon_gen
        self.btn = button
        self.btn_min_width = min(self.btn.width(), self.btn.height())
        super().__init__(self.icon_gen, b'color')
        self.setDuration(duration)
        self.setStartValue(self.icon_gen.color)
        self.setEndValue(end_color)
        self.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        self.valueChanged.connect(self.on_value_changed)

    def on_value_changed(self, color: QtGui.QColor):
        self.btn.setIcon(self.icon_gen.icon(QtCore.QSize(self.btn_min_width, self.btn_min_width), color))

class Rotate(QtCore.QPropertyAnimation):
    '''旋转QGraphicsView中的物件'''
    def __init__(self, item: QtWidgets.QGraphicsItem, rotation: float, start_rotation: float=None, duration: int=120):
        super().__init__(item, b'rotation')
        self.setDuration(duration)
        if start_rotation:
            self.setStartValue(start_rotation)
            self.setEndValue(start_rotation+rotation)
        else:
            self.setEndValue(item.rotation()+rotation)