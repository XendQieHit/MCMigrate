import logging, json, os
from enum import Enum
from PySide6 import QtWidgets, QtGui, QtCore
from terminal.Terminal import Terminal
from pathlib import Path

from windows.loadStyleSheet import load_stylesheet
from windows.Messageable import Messageable
import Message, MCException

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
        self.button_import.setStyleSheet(load_stylesheet("qss/welcome.qss"))
        self.layout.addWidget(self.button_import, 1, QtCore.Qt.AlignCenter)
        self.resize(800, 400)

    def button_import_clicked(self):
        version_path = Path(QtWidgets.QFileDialog.getExistingDirectory(
            parent=None,
            caption="选择.minecraft文件夹",
            dir="",
            options=QtWidgets.QFileDialog.ShowDirsOnly
        ))
        if version_path and version_path != Path("."): # 传空值就忽略，什么消息也不发
            # 开始解析版本路径
            try:
                self.terminal.add_version(version_path)
            except MCException.NotMCGameFolder as e:
                self.message.error(f"{e}")
                return
            except Exception as e:
                self.message.error(f"版本导入失败：{e}")
                return

            # 版本路径解析完毕了，接下来就是加载前端版本列表
            with open("versions.json", 'r', encoding='utf-8') as f:
                try:
                    versions = json.load(f)
                    if not versions: # 怎么是空值？
                        raise IOError("version.json内容为空")
                except (IOError, OSError) as e:
                    self.message.error(f"读取versions.json失败：{e}")
                    return
                except Exception as e:
                    self.message.error(f"发生了意外的错误：{e}")
                    return

            self.terminal.switch_window(Terminal.WindowEnum.MIGRATE, ("版本导入成功！", Message.Level.DONE), versions)
