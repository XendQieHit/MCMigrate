'''
为了不重复手搓动画而弄的简单动画库
注意！该动画库的动画暂不可与 同动画库里的其他动画一起使用！
以及不能使用在 已经有应用到QGraphicEffect的widget上！
'''
from PySide6 import QtCore, QtWidgets, QtGui

class FadeIn(QtCore.QPropertyAnimation):
    def __init__(self, widget: QtWidgets.QWidget, duration: int=300):
        self.effect_opacity = QtWidgets.QGraphicsOpacityEffect(opacity=0.0)
        widget.setGraphicsEffect(self.effect_opacity)
        super().__init__(widget, b"opacity")
        self.setDuration(duration)
        self.setStartValue(0.0)
        self.setEndValue(1.0)
        self.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

class FadeOut(QtCore.QPropertyAnimation):
    def __init__(self, widget: QtWidgets.QWidget, duration: int=100):
        super().__init__(widget, b"opacity")

        # 在设置初始值之前，需要检查widget是否已经应用上了QGraphicsEffect
        if not hasattr(widget.graphicsEffect(), 'opacity'):
            self.effect_opacity = QtWidgets.QGraphicsOpacityEffect(opacity=1.0) # 呃呃...感觉这样直接拉满还是有些奇怪的...算了不管了（
            widget.setGraphicsEffect(self.effect_opacity)

        self.setStartValue(widget.graphicsEffect().opacity())
        self.setDuration(duration)
        self.setEndValue(0.0)
        self.setEasingCurve(QtCore.QEasingCurve.InOutQuad)