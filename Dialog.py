from PySide6 import QtWidgets, QtCore, QtGui
from typing import Callable, Dict
from enum import Enum
import sys, logging

class Level(Enum):
    INFO = (1, "#4fc2ef", "#f7f7f7")
    DONE = (2, "#5fd170", "#38413e")
    WARNING = (3, "#fde351", "#4e5c57")
    ERROR = (4, "#e7612c", "#ffffff")
    
    def __init__(self, num, color_bg, color_font):
        self.num = num
        self.color_bg = color_bg
        self.color_font = color_font

class DialogWindow(QtWidgets.QWidget):
    '''
    直接浮现在窗口中心的问答框
    '''
    def __init__(
        self,
        title: str,
        content_text: str,
        level: Level,
        parent_widget: QtWidgets.QWidget,
        *buttons: tuple[(str, Callable[[], None], Level)]
    ):
        super().__init__(parent=parent_widget)
        self.main_window = parent_widget
        self.setLayout(QtWidgets.QVBoxLayout())

        # 背景暗淡
        self.background = QtWidgets.QFrame()
        self.background.setFixedSize(self.main_window.size())
        self.background.setStyleSheet("background-color: #2f000000")
        self.layout().addWidget(self.background)
        
        # 问答框
        self.dialog_window = QtWidgets.QWidget()
        self.dialog_window.setFixedSize(500, 260)
        self.dialog_window.setStyleSheet("border-radius: 5px; border: 2px solid #aaaaaaaa; padding: 0px")
        self.dialog_window.setLayout(QtWidgets.QVBoxLayout())
        self.dialog_window.layout().setSpacing(5)
        self.dialog_window.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        self.title_label = QtWidgets.QLabel(title)
        self.dialog_window.layout().addWidget(self.title_label)
        self.title_label.setStyleSheet(f"font-size: 18px; background-color: {level.color_bg}; color: {level.color_font}; padding: 5px; border-radius: none; border: none")

        # 内容文本
        self.content_text = QtWidgets.QLabel(content_text)
        self.content_text.setStyleSheet("font-size: 14px; border: none; margin: 5px")
        self.content_text.setMaximumWidth(self.dialog_window.width() - 30)
        self.content_text.setWordWrap(True)
        self.content_text.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)

        # 内容文本显示区
        self.content_text_view = QtWidgets.QScrollArea()
        self.content_text_view.setWidget(self.content_text)
        self.content_text_view.setWidgetResizable(True)
        self.content_text_view.setStyleSheet(
            """
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                margin: 0px;
                border-radius: 6px;
                border: none
            }
            QScrollBar::handle:vertical {
                background: #D0D0D0;
                border-radius: 6px;
                border: none
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                border: none
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
                border: none
            }
            """
        )
        self.dialog_window.layout().addWidget(self.content_text_view)

        # 按钮区
        self.button_section = QtWidgets.QWidget()
        self.button_section.setLayout(QtWidgets.QHBoxLayout())
        self.button_section.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.button_section.setStyleSheet('border: none; padding: 0px')
        # 实例化按钮
        for button in buttons:
            btn = QtWidgets.QPushButton(text=button[0])
            btn.setStyleSheet(f"border: 2px solid {button[2].color_bg}; border-radius: 5px; font-size: 16px; color: {button[2].color_bg}; padding: 2px")
            btn.clicked.connect(button[1])
            self.button_section.layout().addWidget(btn)
        # 加个关闭窗口键
        self.button_cancel = QtWidgets.QPushButton(text='取消')
        self.button_cancel.setStyleSheet(f"border: 2px solid {Level.INFO.color_bg}; border-radius: 5px; font-size: 16px; color: {Level.INFO.color_bg}; padding: 2px")
        self.button_cancel.clicked.connect(self.close)
        self.button_section.layout().addWidget(self.button_cancel)

        self.dialog_window.layout().addWidget(self.button_section)
        self.layout().addWidget(self.dialog_window, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        

class Dialog:
    '''
    为前端设计的，能够显示问答框的类
    '''
    def __init__(self, parent_widget=None):
        self.parent_widget = parent_widget
        self.current_dialog: DialogWindow = None

    def show_dialog(self):
        if self.current_dialog:
            self.current_dialog.hide()
            self.current_dialog.deleteLater()
        self.current_dialog = DialogWindow()

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    window = QtWidgets.QMainWindow()
    window.resize(800, 400)
    window.setLayout(QtWidgets.QHBoxLayout())
    dialog_window = DialogWindow(
        '111',
        'SBQt，换行还要有空格分开才能正确换行，如果是11111111111111111111111111111111这样就是不能分了，那我要你换行干什么😅\n你说得对，但是qt开发者小时候写英语作业，听老师说单词不够遇到空格要换行，所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿\n所以语文作文写作文时直接整一行写过去，结果就被语文老师打断了双腿',
        Level.INFO,
        window, ('111', lambda: print('111'), Level.INFO))
    window.setCentralWidget(dialog_window)
    window.show()
    sys.exit(app.exec())