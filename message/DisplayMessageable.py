import logging
from PySide6 import QtWidgets, QtCore

from message import Message, Dialog

logging.basicConfig(level=logging.INFO)

# 消息弹窗
class DisplayMessageable():
    '''
    作为消息展示的载体
    \n不过为了防止在新增或替换子组件的时候，悬浮组件被遮盖，建议重写相应的方法并增加悬浮更新
    '''
    def __init__(self):
        super().__init__()
        self.message = Message.Message(parent_widget=self)
        self.dialog = Dialog.Dialog(parent_widget=self)
        # 监听自身移动/缩放
        self.move_timer = QtCore.QTimer()
        self.move_timer.setSingleShot(True)
        self.move_timer.timeout.connect(self._update_message_position)
        
    def _update_message_position(self):
        """实时更新消息弹窗和对话框位置，防止因窗口拉伸而被遮挡"""
        if hasattr(self.message, 'current_message') and self.message.current_message:
            msg = self.message.current_message
            if msg.isVisible():
                x = self.width() - msg.width() - 20
                y = 20
                msg.move(x, y)

        if hasattr(self.dialog, 'current_dialog') and self.dialog.current_dialog:
            dialog = self.dialog.current_dialog
            if dialog.isVisible():
                x = self.width() - dialog.width() - 20
                y = 20
                dialog.move(x, y)
        
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.move_timer.start(50)  # 防抖
        
    def moveEvent(self, event):
        super().moveEvent(event)
        self.move_timer.start(50)