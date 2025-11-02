from PySide6 import QtWidgets, QtCore, QtGui
from typing import Callable, Dict
from enum import Enum
import sys, logging
from PIL import ImageColor
from windows.loadStyleSheet import load_stylesheet

class Level(Enum):
    INFO = (1, "#7bccff", "#34566c5f", "#7bccff2b", "#ffffff")
    DONE = (2, "#80eb83", "#3068325f", "#80eb832d",  "#38413e")
    WARNING = (3, "#f6e16a", "#8a7d335f", "#f6e16a2d", "#000000")
    ERROR = (4, "#e7612c", "#981b0d5f", "#e7612c2d", "#ffffff")
    
    def __init__(self, num, color, color_bg, color_btn, color_font):
        self.num = num
        self.color = color
        self.color_bg = color_bg
        self.color_btn = color_btn
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
        *buttons: tuple[str, Level, Callable[[], None]]
    ):
        super().__init__(parent=parent_widget)
        self.parent_widget = parent_widget
        
        # 设置窗口支持透明
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # 设置自身大小为主窗口大小（作为遮罩容器）
        self.resize(parent_widget.size())

        # 背景遮罩（全屏半透明）
        self.background = QtWidgets.QFrame(self)
        self.background.setGeometry(0, 0, self.width(), self.height())  # 全屏
        self.background.setStyleSheet(f"background-color: rgba{ImageColor.getcolor(level.color_bg, "RGBA")}")
        
        # 对话框
        self.dialog_window = QtWidgets.QWidget(self)
        self.dialog_window.setFixedSize(500, 240)
        self.dialog_window.setObjectName("dialogWindow")
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
        self.dialog_window.layout().addWidget(self.button_section, 0)
        # 添加按钮
        if buttons:
            for button in buttons:
                self.button_section.layout().addWidget(DialogWindow.DialogButton(button[0], button[1], button[2]))
        
        # 取消按钮
        self.button_cancel = DialogWindow.DialogButton('取消', Level.INFO, self.close_with_animation)
        self.button_section.layout().addWidget(self.button_cancel)

        # 准备动画展示，先隐藏界面
        self.effect_opacity = QtWidgets.QGraphicsOpacityEffect(opacity=0.0)
        self.setGraphicsEffect(self.effect_opacity)

    def show_with_animation(self):
        self.show()

        # 先将其移到中心，并设为 0 大小
        center = self.rect().center()
        self.dialog_window.move(center.x() - 250, center.y() - 120)  # 初始位置（目标中心）
        self.dialog_window.resize(0, 0)  # 从 0 开始
        self.dialog_window.show()

        # 透明度动画
        self.anim_fade_in = QtCore.QPropertyAnimation(self.graphicsEffect(), b"opacity")
        self.anim_fade_in.setDuration(300)
        self.anim_fade_in.setStartValue(0.0)
        self.anim_fade_in.setEndValue(1.0)
        self.anim_fade_in.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        self.anim_fade_in.start()
    
    def close_with_animation(self):
        self.anim_fade_in = QtCore.QPropertyAnimation(self.graphicsEffect(), b"opacity")
        self.anim_fade_in.setDuration(100)
        self.anim_fade_in.setStartValue(self.graphicsEffect().opacity())
        self.anim_fade_in.setEndValue(0.0)
        self.anim_fade_in.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        self.anim_fade_in.finished.connect(self.close)
        self.anim_fade_in.start()
    
    class DialogButton(QtWidgets.QPushButton):
        def __init__(self, text: str, level: Level, func: Callable[[], None]):
            super().__init__(text)
            self.color_bg = ImageColor.getcolor(level.color_btn, "RGBA")
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.setStyleSheet(f"""
                QPushButton {{
                    border: 2px solid {level.color};
                    border-radius: 5px;
                    font-size: 16px;
                    background-color: transparent;
                    color: {level.color};
                    padding: 2px
                }}
                QPushButton:hover {{
                    background-color: rgba{self.color_bg}
                }}
            """)
            self.clicked.connect(func)


class Dialog:
    '''
    为前端设计的，能够显示问答框的类
    '''
    def __init__(self, parent_widget=None):
        self.parent_widget = parent_widget
        self.current_dialog: DialogWindow = None

    def show_dialog(self, title: str, level: Level, content_text: str, *buttons):
        if self.current_dialog:
            self.current_dialog.close()
            self.current_dialog.deleteLater()
            self.current_dialog = None
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
    
class Dialogable(QtCore.QObject):
    dialog_requested = QtCore.Signal(str, Level, str, *tuple[str, Level, Callable[[], None]])
    def __init__(self):
        super().__init__()

    def send_dialog(self, title: str, level: Level, content_text: str, *buttons):
        self.dialog_requested.emit(title, level, content_text, *buttons)