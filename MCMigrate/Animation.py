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
        self.setStartValue(0.0)
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

class ChangeColor(QtCore.QPropertyAnimation):
    '''
    颜色变化动画
    Args:
        color_role: 需要变化的颜色角色，如QtGui.QPalette.ColorRole.Button
    '''
    def __init__(self, widget: QtWidgets.QWidget, start_color: QtGui.QColor, end_color: QtGui.QColor, color_role: QtGui.QPalette.ColorRole=QtGui.QPalette.ColorRole.Button, duration: int=300):
        self.widget = widget
        self.color_role = color_role
        super().__init__(self.widget, b"color")
        self.setDuration(duration)
        self.setStartValue(start_color)
        self.setEndValue(end_color)
        self.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        self.valueChanged.connect(self.on_value_changed)

    @QtCore.Slot(QtGui.QColor)
    def on_value_changed(self, color: QtGui.QColor):
        palette = self.widget.palette()
        palette.setColor(self.color_role, color)
        self.widget.setPalette(palette)

class ChangeColorTransiting(ChangeColor):
    '''由原颜色变化至指定颜色的动画'''
    def __init__(self, widget: QtWidgets.QWidget, end_color: QtGui.QColor, color_role: QtGui.QPalette.ColorRole=QtGui.QPalette.ColorRole.Button, duration: int=300):
        super().__init__(widget, widget.palette().color(color_role), end_color, color_role, duration)

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