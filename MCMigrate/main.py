from PySide6 import QtCore, QtWidgets, QtGui
from utils import func
from terminal.Terminal import Terminal
from terminal.func import version
from logging.handlers import TimedRotatingFileHandler
import os, sys, logging, time, json

from windows.Migrate import Migrate
from windows.Welcome import Welcome
from message import Dialog
from message.DisplayMessageable import DisplayMessageable
from collections import deque

class LimitedFileHandler(logging.FileHandler):
    """
    一个自定义的 logging Handler，将日志内容限制在指定行数。
    它会将所有日志存储在内存中的一个双端队列（deque）中，
    当行数超过限制时，会移除最旧的日志行。
    """
    def __init__(self, filename, mode='a', encoding='utf-8', delay=False, max_lines=1000):
        # 调用父类的初始化，但不立即打开文件
        super().__init__(filename, mode, encoding, delay)
        self.max_lines = max_lines
        # 使用 deque 存储日志行，设置最大长度
        self.log_buffer = deque(maxlen=max_lines)

    def emit(self, record):
        """
        发射（处理）一条日志记录。
        """
        try:
            # 使用父类的 format 方法格式化日志记录
            msg = self.format(record)
            # 将格式化后的日志消息添加到内存缓冲区
            self.log_buffer.append(msg)

            # 当缓冲区达到最大长度时，将所有内容写入文件
            # 这会覆盖之前的文件内容
            # 注意：这种方法在高频率日志下可能效率不高，因为它每次都重写整个文件
            # 对于简单的截断需求，这足够了
            if len(self.log_buffer) == self.max_lines:
                # 打开文件进行写入（覆盖模式 'w'）
                # 确保在覆盖前文件已关闭（如果之前是打开的）
                if self.stream:
                    self.stream.close()
                    self.stream = None
                # 以覆盖模式打开并写入缓冲区内容
                with open(self.baseFilename, 'w', encoding=self.encoding) as f:
                    f.write('\n'.join(self.log_buffer))
                    # 如果日志记录本身包含换行符，上面的 join 可能会破坏行的完整性
                    # 更安全的方式是逐行写入
                    # for line in self.log_buffer:
                    #     f.write(line + '\n')

        except Exception:
            # 发生错误时，调用父类的 handleError 方法
            self.handleError(record)

    def close(self):
        """
        关闭处理器，将剩余的日志写入文件。
        """
        # 将缓冲区中剩余的日志写入文件
        if self.log_buffer:
            # 确保在覆盖前文件已关闭
            if self.stream:
                self.stream.close()
                self.stream = None
            # 以覆盖模式打开并写入缓冲区内容
            with open(self.baseFilename, 'w', encoding=self.encoding) as f:
                f.write('\n'.join(self.log_buffer))
                # 或者逐行写入以处理消息内的换行符
                # for line in self.log_buffer:
                #     f.write(line + '\n')

        super().close() # 调用父类的 close 方法


# 配置日志文件夹
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, f"{time.strftime('%Y-%m-%d')}.log")
os.makedirs(LOG_DIR, exist_ok=True)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = LimitedFileHandler(
    filename=os.path.join(LOG_FILE)
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