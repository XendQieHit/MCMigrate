from PySide6 import QtCore, QtWidgets, QtGui
from utils import func
from terminal.Terminal import Terminal
from terminal.func import version
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import os, sys, logging, time, json

from windows.Migrate import Migrate
from windows.Welcome import Welcome
from message import Dialog
from message.DisplayMessageable import DisplayMessageable
from collections import deque

# 配置日志文件夹
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, f"{time.strftime('%Y-%m-%d')}.log")
os.makedirs(LOG_DIR, exist_ok=True)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(
    filename=os.path.join(LOG_FILE),
    when="midnight",
    interval=1,
    backupCount=7,
    encoding='utf-8'
)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# 捕获 Qt 事件循环中的异常
# PySide6 的信号/槽异常不会触发 sys.excepthook，需额外处理
def qt_message_handler(mode, context, message):
    """可选：捕获 Qt 警告/错误（非 Python 异常）"""
    if mode == QtCore.QtMsgType.QtCriticalMsg or mode == QtCore.QtMsgType.QtFatalMsg:
        logging.error(f"Qt Critical: {message} ({context.file}:{context.line})")

QtCore.qInstallMessageHandler(qt_message_handler)

# 清理过时log
func.clean_log_folder(LOG_DIR)

class MainWindow(DisplayMessageable, QtWidgets.QMainWindow):
    change_central_widget = QtCore.Signal()
    def __init__(self):
        super().__init__()

    # 防止窗口在切换的时候悬浮组件被遮盖
    def setCentralWidget(self, widget: QtWidgets.QWidget):
        super().setCentralWidget(widget)
        if self.message.current_message: self.message.current_message.raise_()
        if self.dialog.current_dialog: self.dialog.current_dialog.raise_()
        
# 初始化主窗口
app = QtWidgets.QApplication([])
window = MainWindow()
window.setWindowTitle("MCMigrator")
window.setWindowIcon(QtGui.QIcon(func.resource_path("assets/icon_64x64.png")))
window.resize(800, 400)

# 设置全局异常处理器
def handle_exception(exc_type, exc_value, exc_traceback):
    """捕获所有未处理异常"""
    if issubclass(exc_type, KeyboardInterrupt):
        # 允许 Ctrl+C 正常退出，但真的会有人触发吗（
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # 记录到日志文件
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    logging.error("草了，怎么主程序炸了...如果可以的话，请将该日志发在MCMigrate的Github上的Issue里，感谢;w;")
    # 弹出错误对话框
    try:
        window.dialog.error(
            "不好！",
            "MCMigrate在运行的时候遇到了不可预测的错误！❌\n如果可以的话，麻烦将该日志发在MCMigrate的Github上的Issue里，感谢;w;",
            ("打开日志文件夹", Dialog.Level.INFO, lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(QtCore.QUrl.fromLocalFile(LOG_DIR)))),
            ("前往反馈", Dialog.Level.INFO, lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://github.com/XendQieHit/MCMigrate")))
        )
    except Exception:
        pass  # 弹窗失败则静默
# 设置全局钩子
sys.excepthook = handle_exception

# 初始化 Terminal
terminal = Terminal(window)

def show_dialog_slot(title: str, level, content_text: str, payload: dict):
    buttons = payload['buttons']      # tuple
    kwargs = payload['options']      # dict
    window.dialog.show_dialog(title, level, content_text, *buttons, **kwargs)

terminal.message_requested.connect(window.message.show_message)
terminal.dialog_requested.connect(show_dialog_slot)
terminal.dialog_series_requested.connect(window.dialog.ask_in_series)

# 加载界面
if os.path.exists("versions.json") and os.path.getsize("versions.json") > 0:
        try:
            if (version_paths:= version.get_versions()) == []: 
                window.setCentralWidget(Welcome(terminal=terminal))
            else:
                migrate = Migrate(terminal=terminal, version_paths=version_paths)
                window.setCentralWidget(migrate)
                logging.info(migrate)
        except json.JSONDecodeError:
            logging.error("解析versions.json文件失败")
            welcome = Welcome(terminal=terminal)
            window.setCentralWidget(welcome)
else:
    welcome = Welcome(terminal=terminal)
    window.setCentralWidget(welcome)
    logging.info(welcome)
window.show()
sys.exit(app.exec())