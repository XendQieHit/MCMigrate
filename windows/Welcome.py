import logging, json, os
from enum import Enum
from PySide6 import QtWidgets, QtGui, QtCore
from terminal.Terminal import Terminal
from pathlib import Path

from windows.loadStyleSheet import load_stylesheet
from windows.Messageable import Messageable
from windows.Migrate import Migrate

# 欢迎界面
class Welcome(Messageable):
    def __init__(self, terminal: Terminal):
        super().__init__()
        self.terminal = terminal
        self.setStyleSheet("background-color: lightblue;")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.empty_label = QtWidgets.QLabel("欢迎使用 MCMigrator", self)
        self.empty_label.setStyleSheet("font-size: 36px; font-weight: bold; color: white;")
        self.empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.empty_label, 1)

        self.empty_label2 = QtWidgets.QLabel("目前未导入版本路径，先来一个？", self)
        self.empty_label2.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        self.empty_label2.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.empty_label2,0)
        
        self.button_import = QtWidgets.QPushButton("添加版本路径", self)
        self.button_import.setObjectName('button_import')
        self.button_import.clicked.connect(self.button_import_clicked)
        self.button_import.resize(200, 60)
        self.button_import.setStyleSheet(self.load_stylesheet("qss/welcome.qss"))
        self.layout.addWidget(self.button_import, 1, QtCore.Qt.AlignCenter)
        self.resize(800, 400)

    def button_import_clicked(self):
        version_path = Path(QtWidgets.QFileDialog.getExistingDirectory(
            parent=None,
            caption="选择.minecraft文件夹",
            dir="",
            options=QtWidgets.QFileDialog.ShowDirsOnly
        ))
        if version_path and version_path != Path("."):
            self.terminal.add_version(version_path)
            with open("versions.json", 'r', encoding='utf-8') as f:
                try:
                    versions = json.load(f)
                    migrate = Migrate(terminal=self.terminal, version_paths=versions)
                    self.terminal.window.setCentralWidget(migrate)
                    self.message.done("版本导入成功！")
                except:
                    logging.error("解析versions.json文件失败")
                    welcome = Welcome(terminal=self.terminal)
                    self.terminal.window.setCentralWidget(welcome)
                    self.message.error("版本导入失败！")