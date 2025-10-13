# Message.py - 修改后的版本
from PySide6 import QtWidgets, QtCore, QtGui
from enum import Enum
import sys, logging

class Level(Enum):
    INFO = (1, "#4fc2ef", "#f7f7f7")
    DONE = (2, "#5fd170", "#38413e")
    WARNING = (3, "#e3ed4b", "#38413e")
    ERROR = (4, "#e7612c", "#eaffe1")
    
    def __init__(self, num, color_bg, color_font):
        self.num = num
        self.color_bg = color_bg
        self.color_font = color_font

class MessageBar(QtWidgets.QWidget):
    def __init__(self, msg: str, level: Level, parent_widget=None):
        super().__init__(parent_widget)
        self.main_window = parent_widget
        self.level = level
        
        # init
        layout = QtWidgets.QHBoxLayout() # 增加一些内边距
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.label = QtWidgets.QLabel(msg)
        self.label.setStyleSheet(f"color: {level.color_font}; font-size: 14px; font-weight: bold; padding: 4px")
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        self.setStyleSheet(f"background: {level.color_bg}; border-radius: 4px;")
        self.setFixedSize(250, 36)  # 固定大小，避免布局计算
        
        # 初始隐藏
        self.setWindowOpacity(0.0)
        
        # 存储动画引用
        self.animations = None

    def show_with_animation(self):
        """显示并播放进入动画"""
        # 如果有父窗口，定位到父窗口右上角
        if self.main_window:
            # 定位到主窗口右上角（内部坐标）
            x = self.main_window.width() - self.width() - 20
            y = 20
            self.move(x, y)
        
        self.show()
        
        self.show()
        
        # 淡入动画
        fade_in = QtCore.QPropertyAnimation(self, b"windowOpacity")
        fade_in.setDuration(300)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        
        # 滑入动画（从右侧）
        start_pos = self.pos() + QtCore.QPoint(50, 0)
        slide_in = QtCore.QPropertyAnimation(self, b"pos")
        slide_in.setDuration(300)
        slide_in.setStartValue(start_pos)
        slide_in.setEndValue(self.pos())
        slide_in.setEasingCurve(QtCore.QEasingCurve.OutBack)
        
        self.animations = QtCore.QParallelAnimationGroup()
        self.animations.addAnimation(fade_in)
        self.animations.addAnimation(slide_in)
        self.animations.start()
        
        # 自动关闭
        QtCore.QTimer.singleShot(3000, self.hide_with_animation)
        
    def hide_with_animation(self):
        """播放退出动画并隐藏"""
        if self.animations and self.animations.state() == QtCore.QAbstractAnimation.Running:
            return
            
        fade_out = QtCore.QPropertyAnimation(self, b"Opacity")
        fade_out.setDuration(300)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        
        slide_out = QtCore.QPropertyAnimation(self, b"pos")
        slide_out.setDuration(300)
        slide_out.setStartValue(self.pos())
        slide_out.setEndValue(self.pos() + QtCore.QPoint(50, 0))
        slide_out.setEasingCurve(QtCore.QEasingCurve.InBack)
        slide_out.finished.connect(self.close)  # 使用 close 而不是 hide
        
        self.animations = QtCore.QParallelAnimationGroup()
        self.animations.addAnimation(fade_out)
        self.animations.addAnimation(slide_out)
        self.animations.start()


class Message:
    '''
    为前端设计的，能够显示消息弹窗的类
    '''
    def __init__(self, parent_widget=None):
        self.parent_widget = parent_widget
        self.current_message = None
        
    def show_message(self, msg: str, level: Level):
        # 创建新消息
        self.current_message = MessageBar(msg, level, self.parent_widget)
        self.current_message.show_with_animation()
        
    def info(self, msg: str):
        self.show_message(msg, Level.INFO)
        
    def done(self, msg: str):
        self.show_message(msg, Level.DONE)
        
    def warning(self, msg: str):
        self.show_message(msg, Level.WARNING)
        
    def error(self, msg: str):
        self.show_message(msg, Level.ERROR)

class Messageable(QtCore.QObject):
    '''
    为后端设计的，能够向前端窗口发送消息弹窗的类
    '''
    message_requested = QtCore.Signal(str, Level) # 用于向前端窗口发送消息弹窗请求的Signal
    def __init__(self, logging_obj: str | logging.Logger):
        super().__init__()
        # 初始化logger对象，让发送消息弹窗的时候也同步发送日志
        if isinstance(logging_obj, logging.Logger):
            self.logger = logging_obj
        else:
            self.logger = logging.Logger(logging_obj)

    def send_message(self, msg: str, msg_level: Level):
        if msg_level == Level.INFO:
            self.logger.info(msg)
        elif msg_level == Level.DONE:
            self.logger.info("DONE: " + msg)
        elif msg_level == Level.WARNING:
            self.logger.warning(msg)
        elif msg_level == Level.ERROR:
            self.logger.error(msg)
        
        self.message_requested.emit(msg, msg_level)