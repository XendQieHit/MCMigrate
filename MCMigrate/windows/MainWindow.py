from PySide6 import QtCore, QtGui, QtWidgets
from message.DisplayMessageable import DisplayMessageable
from typing import Callable

class GlobalClickWatcher(QtCore.QObject):
    '''用于全局点击事件方法的监听器'''
    funcs = []
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            # 执行处理点击逻辑
            for func in self.funcs: func(event)
        return super().eventFilter(obj, event)
    
    def add_runnable(self, func: Callable[[QtGui.QMouseEvent], None]):
        self.funcs.append(func)

    def remove_runnable(self, func: Callable[[QtGui.QMouseEvent], None]):
        self.funcs.remove(func)

class MainWindow(DisplayMessageable, QtWidgets.QMainWindow):
    '''主窗口，所有界面都要通过该容器展示'''
    change_central_widget = QtCore.Signal()
    def __init__(self, app: QtWidgets.QApplication):
        super().__init__()
        # 添加全局鼠标点击监听器
        self.global_click_watcher = GlobalClickWatcher(self)
        app.installEventFilter(self.global_click_watcher)

    def add_global_click_event(self, func: Callable[[QtGui.QMouseEvent], None]):
        '''
        添加全局点击事件监听函数
        注意！在对象被销毁的时候，请手动移除对应监听函数！
        '''
        self.global_click_watcher.add_runnable(func)

    def remove_global_click_event(self, func: Callable[[QtGui.QMouseEvent], None]):
        '''移除全局点击事件监听函数'''
        self.global_click_watcher.remove_runnable(func)

    # 防止窗口在切换的时候悬浮组件被遮盖
    def setCentralWidget(self, widget: QtWidgets.QWidget):
        super().setCentralWidget(widget)
        if self.message.current_message: self.message.current_message.raise_()
        if self.dialog.current_dialog: self.dialog.current_dialog.raise_()