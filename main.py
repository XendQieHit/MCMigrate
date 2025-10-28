from PySide6 import QtCore, QtWidgets, QtGui
import os, sys, json
from terminal.Terminal import Terminal
import logging

from windows.Migrate import Migrate
from windows.Welcome import Welcome

logging.basicConfig(level=logging.INFO)

# 初始化主窗口
app = QtWidgets.QApplication([])
window = QtWidgets.QMainWindow()
window.setWindowTitle("MCMigrator")
window.setWindowIcon(QtGui.QIcon("assets/icon_64x64.png"))
window.resize(800, 400)

# 初始化 Terminal
terminal = Terminal(window)

# 连接 Terminal 的信号到窗口的消息系统
def show_message_slot(msg: str, level):
    # 通过窗口的 centralWidget 获取当前页面的消息实例
    current_widget = window.centralWidget()
    if hasattr(current_widget, 'message'):
        current_widget.message.show_message(msg, level)

terminal.message_requested.connect(show_message_slot)

if os.path.exists("versions.json") and os.path.getsize("versions.json") > 0:
    with open("versions.json", 'r', encoding='utf-8') as f:
        try:
            version_paths = json.load(f)
            migrate = Migrate(terminal=terminal, version_paths=version_paths)
            window.setCentralWidget(migrate)
            logging.info(migrate)
        except IOError:
            logging.error("解析versions.json文件失败")
            welcome = Welcome(terminal=terminal)
            window.setCentralWidget(welcome)
            logging.info(welcome)
else:
    welcome = Welcome(terminal=terminal)
    window.setCentralWidget(welcome)
    logging.info(welcome)
window.show()
sys.exit(app.exec())