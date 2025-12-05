import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # 单独调试时的代码
from windows.MainWindow import MainWindow
from xml.etree import ElementTree

from PySide6 import QtWidgets, QtGui, QtCore
from pathlib import Path
from terminal.Terminal import Terminal
from terminal.func import config
from windows.SendMessageable import SendMessageable
from core.func import load_stylesheet, resource_path
from message import Message, Dialog

class Menu(SendMessageable):
    def __init__(self, terminal: Terminal):
        super().__init__(terminal.main_window)
        self.config = config.get_config()
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(0)
        
        # 侧边栏选项栏
        self.option_bar = OptionBar(self)
        self.option_bar.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.option_bar)
        
        # 详情栏
        self.content = ContentArea(self)
        self.layout().addWidget(self.content)
    
class OptionBar(QtWidgets.QTreeWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.setObjectName('optionBar')
        self.setStyleSheet((load_stylesheet('qss/menu.qss')))

        # 标题
        self.title = QtWidgets.QLabel('菜单')
        self.title.setObjectName('optionBarTitle')
        self.title.setStyleSheet((load_stylesheet('qss/menu.qss')))
        self.layout().addWidget(self.title)

    def set_menu_xml(xml_path: Path):
        with open(xml_path, 'r', encoding='utf-8') as f:
            data = ElementTree.parse(f)
        view = data.getroot()

class ContentArea(QtWidgets.QFrame):
    def __init__(self, parent):
        super().__init__(parent)
    
    def set_panel_xml(xml_path: Path):
        with open(xml_path, 'r', encoding='utf-8') as f:
            data = ElementTree.parse(f)
        for root in data.iter():
            pass
            

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    window = MainWindow()
    terminal = Terminal(window)
    menu = Menu(terminal)
    window.setCentralWidget(menu)
    window.show()
    app.exec()