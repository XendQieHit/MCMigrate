from PySide6 import QtWidgets, QtCore, QtGui
from typing import Callable, Dict
from enum import Enum
import sys, logging
from windows.loadStyleSheet import load_stylesheet

class Level(Enum):
    INFO = (1, "#7bccff", "#7bccffc1", "#f7f7f7")
    DONE = (2, "#80eb83", "#80eb83c1",  "#38413e")
    WARNING = (3, "#f6e16a", "#f6e16ac1", "#000000")
    ERROR = (4, "#e7612c", "#e7612cc1", "#ffffff")
    
    def __init__(self, num, color, color_bg, color_font):
        self.num = num
        self.color = color
        self.color_bg = color_bg
        self.color_font = color_font

class DialogWindow(QtWidgets.QWidget):
    '''
    直接浮现在窗口中心的问答框
    '''
    def __init__(
        self,
        title: str,
        level: Level,
        content_text: str,
        parent_widget: QtWidgets.QWidget,
        *buttons: tuple[str, Callable[[], None], Level]
    ):
        super().__init__(parent=parent_widget)
        self.parent_widget = parent_widget
        
        # 设置为无边框对话框，支持透明
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # 设置自身大小为主窗口大小（作为遮罩容器）
        self.resize(parent_widget.size())

        # 背景遮罩（全屏半透明）
        self.background = QtWidgets.QFrame(self)
        self.background.setGeometry(0, 0, self.width(), self.height())  # 全屏
        self.background.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")

        # 对话框内容
        self.dialog_window = QtWidgets.QWidget(self)
        self.dialog_window.setFixedSize(500, 260)

        # 设置对话框样式
        self.dialog_window.setStyleSheet(load_stylesheet("qss/dialog.qss"))
        self.dialog_window.setLayout(QtWidgets.QVBoxLayout())
        self.dialog_window.layout().setSpacing(5)
        self.dialog_window.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        self.title_label = QtWidgets.QLabel(title, self.dialog_window)
        self.title_label.setStyleSheet(f"font-size: 18px; background-color: {level.color}; color: {level.color_font}; padding: 5px;")
        self.dialog_window.layout().addWidget(self.title_label)

        # 内容文本
        self.content_text = QtWidgets.QLabel(content_text, self.dialog_window)
        self.content_text.setObjectName("contentText")
        self.content_text.setStyleSheet(load_stylesheet("qss/dialog.qss"))
        self.content_text.setMaximumWidth(self.dialog_window.width() - 30)
        self.content_text.setWordWrap(True)
        self.content_text.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)

        # 滚动区域
        self.content_text_view = QtWidgets.QScrollArea(self.dialog_window)
        self.content_text_view.setWidget(self.content_text)
        self.content_text_view.setWidgetResizable(True)
        self.content_text_view.setObjectName('contentTextView')
        self.content_text_view.setStyleSheet(load_stylesheet("qss/dialog.qss"))
        self.dialog_window.layout().addWidget(self.content_text_view)

        # 按钮区
        self.button_section = QtWidgets.QWidget(self.dialog_window)
        self.button_section.setLayout(QtWidgets.QHBoxLayout())
        self.button_section.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.button_section.setObjectName("buttonSection")
        self.button_section.setStyleSheet(load_stylesheet('qss/dialog.qss'))
        
        for button in buttons:
            btn = QtWidgets.QPushButton(button[0], self.button_section)
            btn.setStyleSheet(f"border: 2px solid {button[2].color}; border-radius: 5px; font-size: 16px; color: {button[2].color}; padding: 2px")
            btn.clicked.connect(button[1])
            self.button_section.layout().addWidget(btn)
        
        # 取消按钮
        self.button_cancel = QtWidgets.QPushButton('取消', self.button_section)
        self.button_cancel.setStyleSheet(f"border: 2px solid {Level.INFO.color}; border-radius: 5px; font-size: 16px; color: {Level.INFO.color}; padding: 2px")
        self.button_cancel.clicked.connect(self.close_and_delete)
        self.button_section.layout().addWidget(self.button_cancel)
        
        self.dialog_window.layout().addWidget(self.button_section)

        # 先隐藏
        self.setWindowOpacity(0.0)

    def showEvent(self, event):
        super().showEvent(event)
        print(2)

    def show_with_animation(self):
        self.show()

        # 1. 背景遮罩和整个对话框容器淡入（透明度动画）
        fade_in = QtCore.QPropertyAnimation(self, b"windowOpacity")
        fade_in.setDuration(300)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        # 2. 内部对话框（dialog_window）缩放动画
        # 先将其移到中心，并设为 0 大小
        center = self.rect().center()
        self.dialog_window.move(center.x() - 250, center.y() - 120)  # 初始位置（目标中心）
        self.dialog_window.resize(0, 0)  # 从 0 开始
        self.dialog_window.show()

        scale_anim = QtCore.QPropertyAnimation(self.dialog_window, b"geometry")
        scale_anim.setDuration(4000)
        scale_anim.setStartValue(QtCore.QRect(center.x() - 250, center.y() - 120, 0, 0))
        scale_anim.setEndValue(QtCore.QRect(center.x() - 250, center.y() - 120, 500, 240))
        scale_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        # 3. 并行动画：淡入 + 缩放
        group = QtCore.QParallelAnimationGroup()
        group.addAnimation(fade_in)
        group.addAnimation(scale_anim)
        group.start()

        # 防止动画被垃圾回收
        self._animation_group = group

    def close_and_delete(self):
        self.close()
        self.deleteLater()

class Dialog:
    '''
    为前端设计的，能够显示问答框的类
    '''
    def __init__(self, parent_widget=None):
        self.parent_widget = parent_widget
        self.current_dialog: DialogWindow = None

    def show_dialog(self, title: str, level: Level, content_text: str, *buttons):
        if self.current_dialog:
            self.current_dialog.close_and_delete()
        self.current_dialog = DialogWindow(title, level, content_text, self.parent_widget, *buttons)
        self.current_dialog.show_with_animation()
        return self.current_dialog

    def info(self, title: str, content_text: str, *buttons):
        return self.show_dialog(title, Level.INFO, content_text, *buttons)

    def warning(self, title: str, content_text: str, *buttons):
        return self.show_dialog(title, Level.WARNING, content_text, *buttons)

    def error(self, title: str, content_text: str, *buttons):
        return self.show_dialog(title, Level.ERROR, content_text, *buttons)

    def done(self, title: str, content_text: str, *buttons):
        return self.show_dialog(title, Level.DONE, content_text, *buttons)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    window = QtWidgets.QMainWindow()
    window.resize(800, 400)
    window.setLayout(QtWidgets.QHBoxLayout())
    frame = QtWidgets.QFrame()
    window.setCentralWidget(frame)
    window.show()

    dialog = Dialog(parent_widget=frame)
    dialog.show_dialog(
        '111',
        Level.WARNING,
        'SBQt，换行还要有空格分开才能正确换行，如果是11111111111111111111111111111111这样就是不能分了，那我要你换行干什么😅\n你说得对，但是qt开发者小时候写英语作业，听老师说单词不够遇到空格要换行，所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿',
         ('111', lambda: print('111'), Level.ERROR))

    sys.exit(app.exec())