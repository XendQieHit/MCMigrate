from PySide6 import QtCore, QtWidgets, QtGui
import os, sys, json, Windows, Terminal
import logging

logging.basicConfig(level=logging.INFO)

app = QtWidgets.QApplication([])
window = QtWidgets.QMainWindow()
window.setWindowTitle("MCMigrator")
window.setWindowIcon(QtGui.QIcon("assets/icon_64x64.png"))
window.resize(800, 400)
terminal = Terminal.Terminal(window)
if os.path.exists("versions.json") and os.path.getsize("versions.json") > 0:
    with open("versions.json", 'r', encoding='utf-8') as f:
        try:
            version_paths = json.load(f)
            migrate = Windows.Migrate(terminal=terminal, version_paths=version_paths)
            window.setCentralWidget(migrate)
            logging.info(migrate)
        except IOError:
            logging.error("解析versions.json文件失败")
            welcome = Windows.Welcome(terminal=terminal)
            window.setCentralWidget(welcome)
            logging.info(welcome)
else:
    welcome = Windows.Welcome(terminal=terminal)
    window.setCentralWidget(welcome)
    logging.info(welcome)
window.show()
sys.exit(app.exec())