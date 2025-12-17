from PySide6 import QtCore, QtWidgets, QtGui
from terminal.Terminal import Terminal
from terminal.func import version
from logging.handlers import TimedRotatingFileHandler
import os, sys, logging, time, json, core.func

from windows.Migrate import Migrate
from windows.Welcome import Welcome
from windows.MainWindow import MainWindow
from message import Dialog, Message

# 配置日志文件夹
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, f"{time.strftime('%Y-%m-%d')}.log")
os.makedirs(LOG_DIR, exist_ok=True)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
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
core.func.clean_log_folder(LOG_DIR)
        
# 初始化主窗口
app = QtWidgets.QApplication([])
window = MainWindow(app)
window.setWindowTitle("MCMigrator")
window.setWindowIcon(QtGui.QIcon(core.func.resource_path("assets/icon_64x64.png")))
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

def show_welcome():
    window.setCentralWidget(Welcome(terminal=terminal))

# 加载界面
if os.path.exists("versions.json") and os.path.getsize("versions.json") > 0:
    versions = version.get_versions()
    try:
        if versions == []: 
            show_welcome()
        else:
            try:
                migrate = Migrate(terminal=terminal)
                window.setCentralWidget(migrate)
            except (ValueError, KeyError):
                logging.error("解析versions.json文件失败")
                show_welcome()
                terminal.send_message("加载版本列表失败：解析versions.json文件失败", Message.Level.ERROR)
            except Exception as e:
                logging.error(f"加载主界面时发生错误：{e}")
                show_welcome()
                terminal.send_message(f"加载主界面时发生错误：{e}", Message.Level.ERROR)
    except json.JSONDecodeError:
        logging.error("解析versions.json文件失败")
        show_welcome()
        terminal.send_message("加载版本列表失败：解析versions.json文件失败", Message.Level.ERROR)
else:
    show_welcome()
    terminal.send_message("加载版本列表失败：解析versions.json文件失败", Message.Level.ERROR)
window.show()

# 用户操作记录部分
# 读取窗口大小记录
try:
    window.resize(*core.func.get_app_state()['window_size'])
except Exception:
    pass
# 监听窗口大小变化以记录操作
window.resizeEvent = lambda event: (
    QtWidgets.QMainWindow.resizeEvent(window, event),
    core.func.modify_app_state([window.width(), window.height()], 'window_size')
)

sys.exit(app.exec())