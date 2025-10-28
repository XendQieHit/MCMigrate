import logging
from PySide6 import QtWidgets, QtCore

import Message

logging.basicConfig(level=logging.INFO)

# 消息弹窗
class Messageable(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()
        self.message = Message.Message(parent_widget=self)
        # 监听自身移动/缩放
        self.move_timer = QtCore.QTimer()
        self.move_timer.setSingleShot(True)
        self.move_timer.timeout.connect(self._update_message_position)
        
    def _update_message_position(self):
        """更新消息弹窗位置"""
        if hasattr(self.message, 'current_message') and self.message.current_message:
            msg_bar = self.message.current_message
            if msg_bar.isVisible():
                x = self.width() - msg_bar.width() - 20
                y = 20
                msg_bar.move(x, y)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.move_timer.start(50)  # 防抖
        
    def moveEvent(self, event):
        super().moveEvent(event)
        self.move_timer.start(50)