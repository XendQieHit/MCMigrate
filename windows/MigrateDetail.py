from enum import Enum
from PySide6 import QtWidgets, QtGui, QtCore
from terminal.Terminal import Terminal

from message import Dialog, Message
from windows.loadStyleSheet import load_stylesheet
from windows.SendMessageable import SendMessageable
from terminal.func.utils import resource_path
import Geometry, GeometryIcon

class MigrateDetail(SendMessageable):
    def __init__(self, terminal: Terminal, migrate_task: Terminal.TaskMigrateAbortable, pre_window: QtWidgets.QFrame):
        super().__init__(terminal.main_window)
        self.pre_window = pre_window
        self.terminal = terminal
        self.migrate_task = migrate_task
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setSpacing(30)
        self.layout().setContentsMargins(30,30,30,30)

        # 左侧加载圈和文字容器
        self.loading_ring_container = QtWidgets.QWidget(self)
        self.loading_ring_container.setLayout(QtWidgets.QVBoxLayout())
        self.loading_ring_container.layout().setSpacing(0)
        self.loading_ring_container.layout().setContentsMargins(20,0,0,20)
        self.layout().addWidget(self.loading_ring_container, 1, QtCore.Qt.AlignCenter)
        
        # 左侧加载圈
        self.loading_ring = Geometry.LoadingRingText(QtGui.QColor("#79D2B1"), QtGui.QColor("#409A9C"))
        self.loading_ring.change_percent(0.0)
        self.loading_ring_container.layout().addWidget(self.loading_ring, 0, QtCore.Qt.AlignCenter)

        # 左侧文字
        self.loading_ring_text = QtWidgets.QLabel("迁移中", self)
        self.loading_ring_text.setObjectName("loadingRingText")
        self.loading_ring_text.setStyleSheet(load_stylesheet(resource_path('qss/migrate_detail.qss')))
        self.loading_ring_container.layout().addWidget(self.loading_ring_text, 0, QtCore.Qt.AlignCenter)

        # 右侧进度详情
        self.task_list = MigrateDetail.TaskList()
        self.layout().addWidget(self.task_list)

        # 退出按钮
        self.button_back = MigrateDetail.ButtonBack(self)
        self.button_back.move(20, 15)
        self.button_back.raise_()
        # 终止任务按键
        self.button_terminate = MigrateDetail.ButtonTerminate(self)
        self.button_terminate.move(20, self.terminal.main_window.height()-self.button_terminate.height()-30)
        self.button_terminate.raise_()

        # 模组方面
        self.task_list.add_task('mod', '下载更新模组', MigrateDetail.TaskStatus.IN_PROGRESS)
        # 文件方面
        self.task_list.add_task('file', '迁移游戏文件', MigrateDetail.TaskStatus.PENDING)
        self.task_list.layout().addStretch()

        # 初始化进度数据
        self.init_stats()

        # 进度数据同步更新
        self.migrate_task.update_migrate_general.connect(self.update_loading_ring)
        self.migrate_task.update_migrate_detail.connect(self.update_tasks)

        # 任务完成时，自动回到上一窗口
        self.migrate_task.finished.connect(self.back)

    def init_stats(self):
        if not self.migrate_task.is_calculating:
            self.loading_ring.change_percent(1-self.migrate_task.pending_num/self.migrate_task.pending_num_total)
            if self.migrate_task.pending_num_mod > 0:
                self.task_list.update_task('mod', percent=1-self.migrate_task.pending_num_mod/self.migrate_task.pending_num_mod_total, task_status=MigrateDetail.TaskStatus.IN_PROGRESS)
                return
            else:
                self.task_list.update_task('mod', task_status=MigrateDetail.TaskStatus.COMPLETED)
            if self.migrate_task.pending_num_file > 0:
                self.task_list.update_task('file', percent=1-self.migrate_task.pending_num_file/self.migrate_task.pending_num_file_total, task_status=MigrateDetail.TaskStatus.IN_PROGRESS)
            else: self.task_list.update_task('file', task_status=MigrateDetail.TaskStatus.COMPLETED)

    @QtCore.Slot()
    def terminate(self):
        self.dialog.current_dialog.close_with_animation()
        self.terminal.switch_window_with_msg(Terminal.WindowEnum.MIGRATE, ('已终止迁移任务', Message.Level.INFO), self.terminal.versions_json)

    @QtCore.Slot()
    def back(self):
        self.terminal.switch_window(Terminal.WindowEnum.MIGRATE, self.terminal.versions_json, self.terminal.task_migrate)

    @QtCore.Slot(int, int)
    def update_tasks(self, pending_num_mod, pending_num_file):
        if not self.migrate_task.pending_num_mod <= 0:
            self.task_list.update_task('mod', percent=1-pending_num_mod/self.migrate_task.pending_num_mod_total)
            return
        else: 
            self.task_list.update_task('mod', task_status=MigrateDetail.TaskStatus.COMPLETED)
            self.task_list.update_task('file', task_status=MigrateDetail.TaskStatus.IN_PROGRESS)

        if not self.migrate_task.pending_num_file <= 0:
            self.task_list.update_task('file', percent=1-pending_num_file/self.migrate_task.pending_num_file_total)
            return
        else: self.task_list.update_task('file', task_status=MigrateDetail.TaskStatus.COMPLETED)

    @QtCore.Slot(int)
    def update_loading_ring(self, pending_num):
        self.loading_ring.change_percent(1-pending_num/self.migrate_task.pending_num_total)

    class TaskList(QtWidgets.QFrame):
        def __init__(self):
            super().__init__()
            self.setLayout(QtWidgets.QVBoxLayout())
            self.setObjectName('taskList')
            self.setStyleSheet(load_stylesheet(resource_path("qss/migrate_detail.qss")))
            self.setFixedWidth(380)
            self.layout().setSpacing(5)
            self.setContentsMargins(10,5,10,5)
            self.tasks: list[MigrateDetail.TaskBar] = []

        def add_task(self, task_id: str, task_name: str, task_status: 'MigrateDetail.TaskStatus') -> 'MigrateDetail.TaskBar':
            task = MigrateDetail.TaskBar(task_id=task_id, task_name=task_name, status=task_status, parent=self)
            self.layout().addWidget(task)
            self.tasks.append(task)
            return task

        def update_task(self, task_id: str, percent: float=None, task_status: 'MigrateDetail.TaskStatus'=None):
            for task in self.tasks:
                if task.task_id == task_id:
                    if task_status: 
                        task.switch_status(task_status)
                        if task_status == MigrateDetail.TaskStatus.COMPLETED: task.update_progress(1.0)
                    if percent: task.update_progress(percent)

    class TaskStatus(Enum):
        PENDING = ("pending", GeometryIcon.Pending, "#2196F3")
        IN_PROGRESS = ("in_progress", GeometryIcon.Pending, "#2196F3")
        COMPLETED = ("completed", GeometryIcon.Completed, "#4CAF50")
        FAILED = ("failed", GeometryIcon.Failed, "#F44336")

        def __init__(self, text: str, clazz: type, color: str):
            self.text = text
            self.clazz = clazz
            self.color = color

        @property
        def instance(self) -> QtWidgets.QWidget:
            return self.clazz(self.color)

    class TaskBar(QtWidgets.QFrame):
        def __init__(self, task_id: str, task_name: str, status: 'MigrateDetail.TaskStatus' = None, parent=None, length=300):
            super().__init__(parent)
            self.task_id = task_id
            self.task_name = task_name
            if status is None:
                status = MigrateDetail.TaskStatus.PENDING
            if parent:
                length = parent.width()

            self.status = status  # pending, in_progress, completed, failed
            self.process_percent = 0.0  # 0.0 - 1.0
            self.setLayout(QtWidgets.QVBoxLayout())
            self.layout().setSpacing(0)
            self.layout().setContentsMargins(0,0,0,0)

            # 状态图标和进度的容器
            self.info_container = QtWidgets.QFrame(self)
            self.info_container.setLayout(QtWidgets.QHBoxLayout())
            self.info_container.layout().setContentsMargins(0,0,0,0)
            self.info_container.layout().setSpacing(5)
            self.layout().addWidget(self.info_container)

            # 状态图标和进度
            self.status_icon = self.status.instance
            self.status_icon.setObjectName("statusIcon")
            self.status_icon.setStyleSheet(load_stylesheet(resource_path("qss/migrate_detail.qss")))
            self.status_percent = QtWidgets.QLabel()
            self.status_percent.setObjectName("statusPercent")
            self.status_percent.setStyleSheet(load_stylesheet(resource_path('qss/migrate_detail.qss')))
            self.status_percent.setText(f"{int(self.process_percent * 100)}%")
            if self.status == MigrateDetail.TaskStatus.IN_PROGRESS:
                self.info_container.layout().addWidget(self.status_percent)
            else:
                self.info_container.layout().addWidget(self.status_icon)
        
            # 任务名称
            self.label_task_name = QtWidgets.QLabel(self.task_name, self)
            self.label_task_name.setObjectName("taskName")
            self.label_task_name.setStyleSheet(load_stylesheet(resource_path('qss/migrate_detail.qss')))
            self.info_container.layout().addWidget(self.label_task_name)
            self.info_container.layout().addStretch()

            # 进度条
            self.loading_line = Geometry.LoadingLine(color=QtGui.QColor("#79D2B1"), pen_width=3, length=length-40)
            self.loading_line.setObjectName('loadingLine')
            self.loading_line.setStyleSheet(load_stylesheet(resource_path('qss/migrate_detail.qss')))
            self.loading_line.change_percent(self.process_percent)
            self.layout().addWidget(self.loading_line)

            # 布局
            self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
            self.adjustSize()
            self.setObjectName("taskBar")
            self.setStyleSheet(load_stylesheet(resource_path("qss/migrate_detail.qss")))

        def switch_status(self, status: 'MigrateDetail.TaskStatus'):
            if status == MigrateDetail.TaskStatus.IN_PROGRESS:
                self.info_container.layout().replaceWidget(self.status_icon, self.status_percent)
                self.status_icon.close()
            elif status in [
                    MigrateDetail.TaskStatus.COMPLETED, 
                    MigrateDetail.TaskStatus.FAILED,
                    MigrateDetail.TaskStatus.PENDING
                ]:
                self.status_icon = status.instance
                self.info_container.layout().replaceWidget(self.status_percent, self.status_icon)
                self.status_percent.close()
            self.status = status

        def update_progress(self, percent: float):
            self.process_percent = percent
            self.status_percent.setText(f"{int(self.process_percent * 100)}%")
            self.loading_line.change_percent(self.process_percent)
    
    class ButtonBack(QtWidgets.QPushButton):
        def __init__(self, parent: 'MigrateDetail'):
            super().__init__(parent=parent)
            self.setFixedSize(45, 45)
            self.setToolTip("回到上一界面")
            self.setObjectName('buttonBack')
            self.setStyleSheet(load_stylesheet(resource_path('qss/migrate_detail.qss')))
            self.setLayout(QtWidgets.QHBoxLayout())
            self.layout().addWidget(Geometry.Arrow(self, self, color="#79D2B1", angle=-180))
            self.clicked.connect(parent.back)

    class ButtonTerminate(QtWidgets.QPushButton):
        def __init__(self, parent: 'MigrateDetail'):
            super().__init__(parent=parent)
            self.setFixedSize(50,50)
            self.setToolTip("终止任务")
            self.setObjectName('buttonTerminate')
            self.setStyleSheet(load_stylesheet(resource_path('qss/migrate_detail.qss')))
            self.setLayout(QtWidgets.QHBoxLayout())
            self.layout().setContentsMargins(0,0,0,0)
            self.layout().addWidget(GeometryIcon.Terminate("#79D2B1", size=36), 0, QtCore.Qt.AlignmentFlag.AlignCenter)

            def wait_for_terminated():
                parent.terminal.terminate_migrate_task()
                current_dialog = parent.dialog.current_dialog
                # 失效终止按钮，防止重复发送请求
                current_dialog.dialog_buttons[0].clicked.disconnect()
                current_dialog.content_text.setText(current_dialog.content_text.text() + "\n\n等待任务结束中...")

            self.clicked.connect(lambda: parent.dialog.warning(
                '确定要终止迁移任务吗？',
                '已经迁移完成的文件将不会删除，若有需要请自行删除',
                ('终止任务!', Dialog.Level.ERROR, wait_for_terminated)
            ))
            parent.terminal.task_migrate.terminated.connect(parent.terminate)