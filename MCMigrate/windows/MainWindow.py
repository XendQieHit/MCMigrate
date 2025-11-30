from PySide6 import QtCore, QtGui, QtWidgets
from message.DisplayMessageable import DisplayMessageable

class MainWindow(DisplayMessageable, QtWidgets.QMainWindow):
    '''主窗口，所有界面都要通过该容器展示'''
    change_central_widget = QtCore.Signal()
    def __init__(self):
        super().__init__()

    # 防止窗口在切换的时候悬浮组件被遮盖
    def setCentralWidget(self, widget: QtWidgets.QWidget):
        super().setCentralWidget(widget)
        if self.message.current_message: self.message.current_message.raise_()
        if self.dialog.current_dialog: self.dialog.current_dialog.raise_()