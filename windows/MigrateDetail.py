import sys, os
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # 单独调试时的代码

import logging, json, os
from enum import Enum
from PySide6 import QtWidgets, QtGui, QtCore
# app = QtWidgets.QApplication(sys.argv)
from terminal.Terminal import Terminal
from pathlib import Path

from windows.loadStyleSheet import load_stylesheet
from windows.Messageable import Messageable
import Geometry, GeometryIcon

class MigrateDetail(Messageable):
    def __init__(self, terminal: Terminal):
        super().__init__()
        self.terminal = terminal
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
        self.loading_ring.change_percent(0.79)
        self.loading_ring_container.layout().addWidget(self.loading_ring, 0, QtCore.Qt.AlignCenter)

        # 左侧文字
        self.loading_ring_text = QtWidgets.QLabel("迁移中", self)
        self.loading_ring_text.setObjectName("loadingRingText")
        self.loading_ring_text.setStyleSheet(load_stylesheet('qss/migrate_detail.qss'))
        self.loading_ring_container.layout().addWidget(self.loading_ring_text, 0, QtCore.Qt.AlignCenter)

        # 右侧进度详情
        self.task_list = MigrateDetail.TaskList()
        self.layout().addWidget(self.task_list)

        # 退出按钮
        self.button_back = MigrateDetail.ButtonBack(self)
        self.button_back.move(15, 15)
        self.raise_()

        # 示例任务
        self.task_list.add_task("准备迁移数据", MigrateDetail.TaskStatus.COMPLETED)
        self.aaa = self.task_list.add_task("迁移用户数据", MigrateDetail.TaskStatus.IN_PROGRESS)
        self.aaa.update_progress(0.45)

        self.task_list.layout().addStretch()

    class TaskList(QtWidgets.QFrame):
        def __init__(self):
            super().__init__()
            self.setLayout(QtWidgets.QVBoxLayout())
            self.setObjectName('taskList')
            self.setStyleSheet(load_stylesheet("qss/migrate_detail.qss"))
            self.setFixedWidth(380)
            self.layout().setSpacing(5)
            self.setContentsMargins(10,5,10,5)
            self.tasks = []

        def add_task(self, task_name: str, task_status: 'MigrateDetail.TaskStatus') -> 'MigrateDetail.TaskBar':
            task = MigrateDetail.TaskBar(task_name=task_name, status=task_status, parent=self)
            self.layout().addWidget(task)
            self.tasks.append(task)
            return task

    class TaskStatus(Enum):
        PENDING = ("pending", GeometryIcon.Pending("#2196F3"))
        IN_PROGRESS = ("in_progress", GeometryIcon.Pending("#2196F3"))
        COMPLETED = ("completed", GeometryIcon.Completed("#4CAF50"))
        FAILED = ("failed", GeometryIcon.Failed("#F44336"))

        def __init__(self, text: str, icon: QtWidgets.QWidget):
            self.text = text
            self.icon = icon
    
    class TaskBar(QtWidgets.QFrame):
        def __init__(self, task_name: str, status: 'MigrateDetail.TaskStatus' = None, parent=None, length=300):
            super().__init__(parent)
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
            self.status_icon = self.status.icon
            self.status_icon.setObjectName("statusIcon")
            self.status_icon.setStyleSheet(load_stylesheet("qss/migrate_detail.qss"))
            self.status_percent = QtWidgets.QLabel()
            self.status_percent.setObjectName("statusPercent")
            self.status_percent.setStyleSheet(load_stylesheet('qss/migrate_detail.qss'))
            self.status_percent.setText(f"{int(self.process_percent * 100)}%")
            if self.status == MigrateDetail.TaskStatus.IN_PROGRESS:
                self.info_container.layout().addWidget(self.status_percent)
            else:
                self.info_container.layout().addWidget(self.status_icon)
        
            # 任务名称
            self.label_task_name = QtWidgets.QLabel(self.task_name, self)
            self.label_task_name.setObjectName("taskName")
            self.label_task_name.setStyleSheet(load_stylesheet('qss/migrate_detail.qss'))
            self.info_container.layout().addWidget(self.label_task_name)
            self.info_container.layout().addStretch()

            # 进度条
            self.loading_line = Geometry.LoadingLine(color=QtGui.QColor("#79D2B1"), pen_width=3, length=length-40)
            self.loading_line.setObjectName('loadingLine')
            self.loading_line.setStyleSheet(load_stylesheet('qss/migrate_detail.qss'))
            self.loading_line.change_percent(self.process_percent)
            self.layout().addWidget(self.loading_line)

            # 布局
            self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
            self.adjustSize()
            self.setObjectName("taskBar")
            self.setStyleSheet(load_stylesheet("qss/migrate_detail.qss"))

        def switch_status(self, status: 'MigrateDetail.TaskStatus'):
            if status == MigrateDetail.TaskStatus.IN_PROGRESS:
                self.info_container.layout().replaceWidget(self.status_icon, self.status_percent)
            elif status in [
                    MigrateDetail.TaskStatus.COMPLETED, 
                    MigrateDetail.TaskStatus.FAILED,
                    MigrateDetail.TaskStatus.PENDING
                ]:
                self.status_icon = status.icon
                self.info_container.layout().replaceWidget(self.status_percent, self.status_icon)
            self.status = status

        def update_progress(self, percent: float):
            self.process_percent = percent
            self.status_percent.setText(f"{int(self.process_percent * 100)}%")
            self.loading_line.change_percent(self.process_percent)
    
    class ButtonBack(QtWidgets.QPushButton):
        def __init__(self, parent: QtWidgets.QFrame):
            super().__init__(parent=parent)
            self.setFixedSize(45, 45)
            self.setObjectName('buttonBack')
            self.setStyleSheet(load_stylesheet('qss/migrate_detail.qss'))
            self.setLayout(QtWidgets.QHBoxLayout())
            self.layout().addWidget(Geometry.Arrow(self, self, color="#79D2B1", angle=-180))
            self.clicked.connect(lambda: self.button_clicked(self.parent()))

        def button_clicked(parent):
            pass
    
if __name__ == "__main__":
    import sys
    
    window = QtWidgets.QMainWindow()
    terminal = Terminal(window)
    md = MigrateDetail(terminal=terminal)
    terminal.window.setCentralWidget(md)
    terminal.window.show()
    sys.exit(app.exec())