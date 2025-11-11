from PySide6 import QtWidgets
from message.DisplayMessageable import DisplayMessageable

class SendMessageable(QtWidgets.QFrame):
    def __init__(self, window: DisplayMessageable):
        super().__init__()
        self.message = window.message
        self.dialog = window.dialog