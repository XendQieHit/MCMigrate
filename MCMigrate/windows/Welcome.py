import logging, json, os, winreg
from enum import Enum
from PySide6 import QtWidgets, QtGui, QtCore
from terminal.Terminal import Terminal
from pathlib import Path

from windows.loadStyleSheet import load_stylesheet
from windows.SendMessageable import SendMessageable
from message import Message
from core.func import resource_path
import MCException

# 欢迎界面
class Welcome(SendMessageable):
    def __init__(self, terminal: Terminal):
        super().__init__(terminal.main_window)
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
        
        self.button_container = QtWidgets.QWidget(self)
        self.button_container.setLayout(QtWidgets.QHBoxLayout())
        self.layout.addWidget(self.button_container, 1, QtCore.Qt.AlignCenter)

        self.button_import = QtWidgets.QPushButton("添加版本路径", self.button_container)
        self.button_import.setObjectName('button_import')
        self.button_import.clicked.connect(self.button_import_clicked)
        self.button_import.resize(200, 60)
        self.button_import.setStyleSheet(load_stylesheet(resource_path("qss/welcome.qss")))
        self.button_container.layout().addWidget(self.button_import, 0, QtCore.Qt.AlignCenter)
        
        # 查找是否有PCL，有则显示PCL导入按钮
        if os.name == 'nt':
            has_pcl = False
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\PCL')
                value: str = winreg.QueryValueEx(key, "launchFolders")[0]
                has_pcl = True
            except FileNotFoundError as e:
                logging.info(f"没有PCL注册表键或值不存在。")
            finally: winreg.CloseKey(winreg.HKEY_CURRENT_USER)
            if has_pcl:
                self.button_import_pcl = QtWidgets.QPushButton("一键从PCL添加版本", self.button_container)
                self.button_import_pcl.setObjectName('button_import_pcl')
                self.button_import_pcl.clicked.connect(self.button_import_pcl_clicked)
                self.button_import_pcl.resize(200, 60)
                self.button_import_pcl.setStyleSheet(load_stylesheet(resource_path("qss/welcome.qss")))
                self.button_container.layout().addWidget(self.button_import_pcl, 0, QtCore.Qt.AlignCenter)

        self.button_container.adjustSize()
        self.resize(800, 400)

    def button_import_clicked(self):
        if versions := self.terminal.import_version():
            self.terminal.switch_window_with_msg(Terminal.WindowEnum.MIGRATE, ("版本导入成功！", Message.Level.DONE), versions)

    def button_import_pcl_clicked(self):
        if versions:= self.terminal.import_versions_from_pcl():
            self.terminal.switch_window_with_msg(Terminal.WindowEnum.MIGRATE, ("版本导入成功！", Message.Level.DONE), versions)