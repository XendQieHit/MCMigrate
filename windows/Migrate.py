import logging
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtSvgWidgets import QSvgWidget
from terminal.Terminal import Terminal
from pathlib import Path

from windows.Messageable import Messageable
import Message
from windows.loadStyleSheet import load_stylesheet
import windows
import Geometry

class Migrate(Messageable):
    def __init__(self, terminal: Terminal, version_paths: list[dict]):
        super().__init__()
        self.terminal = terminal
        self.setWindowTitle("MCMigrator")
        self.setWindowIcon(QtGui.QIcon("assets/icon_64x64.png"))
        self.layout = QtWidgets.QVBoxLayout()
        self.window_title = QtWidgets.QLabel("选择要迁移的版本", self)
        self.window_title.setStyleSheet("font-size: 18px; color: #666666")
        self.layout.addWidget(self.window_title, 0)
        
        # 版本列表
        self.list_box = QtWidgets.QHBoxLayout()
        self.ver_list_source = Migrate.VersionList(version_paths, self)
        self.ver_list_target = Migrate.VersionList(version_paths, self)
        self.list_box.addWidget(self.ver_list_source)

        self.arrow = Geometry.Arrow(self.ver_list_source, self.ver_list_target, "#aaaaaa")
        self.arrow.setMaximumSize(self.window().height() * 0.05, self.window().width() * 0.05)
        self.list_box.addWidget(self.arrow, 0, QtCore.Qt.AlignCenter)

        self.list_box.addWidget(self.ver_list_target)
        self.layout.addLayout(self.list_box)

        # 底部按钮
        self.button_box = QtWidgets.QHBoxLayout()
        self.button_import = QtWidgets.QPushButton("导入版本路径")
        self.button_import.setObjectName("button_import")
        self.button_import.setStyleSheet(load_stylesheet("qss/migrate.qss"))
        self.button_import.clicked.connect(self.button_import_clicked)
        self.button_migrate = QtWidgets.QPushButton("开始迁移")
        self.button_migrate.setObjectName("button_migrate")
        self.button_migrate.setStyleSheet(load_stylesheet("qss/migrate.qss"))
        self.button_migrate.clicked.connect(self.button_migrate_clicked)
        self.button_box.addWidget(self.button_import)
        self.button_box.addWidget(self.button_migrate)
        self.layout.addLayout(self.button_box)
        
        # 布局调整
        self.setLayout(self.layout)
        self.resize(800, 400)

    def button_import_clicked(self):
        path = Path(QtWidgets.QFileDialog.getExistingDirectory(
            parent=None,
            caption="选择.minecraft文件夹",
            dir="",
            options=QtWidgets.QFileDialog.ShowDirsOnly
        ))
        if path == Path("."): return
        if self.terminal.add_version(path):
            versions = self.terminal.get_versions()
            self.ver_list_source.update_versions(versions)
            self.ver_list_target.update_versions(versions)
            self.window().update()

    def button_migrate_clicked(self):
        # 条件检测
        if self.terminal.is_migrating:
            logging.info()
            self.message.info("请先等待迁移完成")
            return
        ver_source: Migrate.VersionItem = self.ver_list_source.itemWidget(self.ver_list_source.currentItem())
        ver_target: Migrate.VersionItem = self.ver_list_target.itemWidget(self.ver_list_target.currentItem())
        if ver_source == None or ver_target == None:
            logging.info("请先选择迁移版本和目标版本")
            self.message.info("请先选择迁移版本和目标版本")
            return
        self.terminal.migrate(source_json=ver_source.json, target_json=ver_target.json)
        
        # 添加任务详情悬浮按钮
        self.button_migrate_detail = ButtonMigrateDetail(self)
    
    def percent_update(self, timer: QtCore.QTimer, ring: Geometry.LoadingRingText):
        ring.change_percent(self.terminal.pending_num)
        if self.terminal.pending_num == 0 and not self.terminal.is_migrating:
            timer.stop()
            timer.deleteLater()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'button_migrate_detail'):
            self.button_migrate_detail.move(self.width() - 100, self.height() - 135)
    

    class VersionItem(QtWidgets.QWidget):
        def __init__(self, json: dict, parent_list: 'Migrate.VersionList'):
            super().__init__(parent=parent_list)
            self.setObjectName("VersionItem")
            self.json = json
            self.list = parent_list

            # 总容器
            self.setLayout(QtWidgets.QHBoxLayout())
            self.layout().setSpacing(5)
            self.layout().setContentsMargins(5, 5, 5, 5)

            # 加载器图标
            self.mod_loader_icon = self.get_icon(self.json.get('mod_loader', 'unknown'))
            self.mod_loader_icon.setObjectName("mod_loader_icon")
            self.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.mod_loader_icon.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.layout().addWidget(self.mod_loader_icon, 0)

            # 版本信息容器
            self.info = QtWidgets.QWidget()
            self.info.setObjectName('info')
            self.info.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.info_layout = QtWidgets.QVBoxLayout()
            self.info_layout.setSpacing(0)
            self.info_layout.setContentsMargins(0, 0, 0, 0)
            self.info.setLayout(self.info_layout)
            self.layout().addWidget(self.info, 1)

            # 游戏版本名及其加载器、版本隔离标签的容器
            self.info_name = QtWidgets.QWidget()
            self.info_name.setObjectName('info_name')
            self.info_name.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.info_name_layout = QtWidgets.QHBoxLayout()
            self.info_name.setLayout(self.info_name_layout)
            self.info_layout.addWidget(self.info_name)

            # 加载器标签
            self.mod_loader = QtWidgets.QLabel(json.get('mod_loader', '未知Mod加载器'))
            self.mod_loader.setObjectName('mod_loader_label')
            self.mod_loader.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.info_name_layout.addWidget(self.mod_loader, 0)

            # 版本隔离标签
            if not json.get('is_indie', False):
                self.is_indie = QtWidgets.QLabel('非隔离版本')
                self.is_indie.setObjectName('indie_label')
                self.is_indie.setStyleSheet(load_stylesheet("qss/migrate.qss"))
                self.info_name_layout.addWidget(self.is_indie, 0)

            # 游戏版本名
            self.name = QtWidgets.QLabel(json.get('name', "未知版本名"))
            self.name.setObjectName('name_label')
            self.name.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.info_name_layout.addWidget(self.name, 1)

            self.info_name_layout.addStretch()

            # 版本号标签和版本文件路径的容器
            self.info_detail = QtWidgets.QWidget()
            self.info_detail.setObjectName('info_detail')
            self.info_detail.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.info_detail_layout = QtWidgets.QHBoxLayout()
            self.info_detail.setLayout(self.info_detail_layout)
            self.info_layout.addWidget(self.info_detail)

            # 版本号
            self.ver = QtWidgets.QLabel(json.get('version', '未知版本'))
            self.ver.setObjectName("version_label")
            self.ver.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.info_detail_layout.addWidget(self.ver, 0)

            # 版本文件路径
            self.path = QtWidgets.QLabel(json.get('game_path', '未知路径'))
            self.path.setObjectName("path_label")
            self.path.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.info_detail_layout.addWidget(self.path, 1)

            self.info_detail_layout.addStretch()

            # 悬浮操作栏
            self.float_bar = Migrate.VersionItem.FloatBar(self)

        def resizeEvent(self, event): # 这里存放根据卡片大小来确定自身大小的widget
            self.float_bar.setFixedSize(50, self.height()-10)
            super().resizeEvent(event)
        
        def enterEvent(self, event):
            self.float_bar.move(self.list.viewport().width() - self.float_bar.width() - 10, 5)
            self.float_bar.show()
            self.list.hover_item = self
            super().enterEvent(event)

        def leaveEvent(self, event):
            self.list.hover_item = None
            self.float_bar.hide()
            super().leaveEvent(event)

        def get_icon(self, mod_loader: str = None) -> QtWidgets.QLabel:
            mod_loaders = {
                "fabric": "assets/icon/fabric.png",
                "neoforge": "assets/icon/neoforge.png",
                "forge": "assets/icon/forge.png",
                "quilt": "assets/icon/quilt.png",
                "release": "assets/icon/release.png",
                "optifine": "assets/icon/optifine.png",
                "snapshot": "assets/icon/snapshot.png",
                "unknown": "assets/icon/unknown.png"
            }
            for key in mod_loaders.keys():
                if key in mod_loader.lower():
                    pixmap = QtGui.QPixmap(mod_loaders[key]).scaled(36, 36)
                    label = QtWidgets.QLabel()
                    label.setPixmap(pixmap)
                    return label
                    
            pixmap = QtGui.QPixmap("assets/icon/unknown.png").scaled(36, 36)
            label = QtWidgets.QLabel()
            label.setPixmap(pixmap)
            return label
        
        class FloatBar(QtWidgets.QFrame):
            def __init__(self, parent_widget: 'Migrate.VersionItem'):
                super().__init__(parent_widget)
                self.parent_item = parent_widget
                # 总样式设置
                self.setLayout(QtWidgets.QVBoxLayout())
                self.setContentsMargins(0,0,0,0)
                self.layout().setSpacing(2)

                self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
                self.setObjectName('float_bar')
                self.setStyleSheet(load_stylesheet('qss/migrate.qss'))

                # 打开文件夹
                # 按钮
                self.folder_btn = QtWidgets.QPushButton()
                self.folder_btn.setObjectName('folder_btn')
                self.folder_btn.setStyleSheet(load_stylesheet('qss/migrate.qss'))
                self.folder_btn.setContentsMargins(0,0,0,0)
                self.folder_btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
                self.folder_btn.setToolTip('打开该版本文件夹')
                self.folder_btn.clicked.connect(self.open_folder)
                self.folder_btn.setIcon(QtGui.QIcon('assets/folder.svg'))
                self.layout().addWidget(self.folder_btn)

                # 删除键
                # 按钮
                self.del_btn = QtWidgets.QPushButton()
                self.del_btn.setObjectName('del_btn')
                self.del_btn.setStyleSheet(load_stylesheet('qss/migrate.qss'))
                self.del_btn.setContentsMargins(0,0,0,0)
                self.del_btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
                self.del_btn.setToolTip('从列表中移除该版本（不会删除本体文件）')
                self.layout().addWidget(self.del_btn)
                # icon
                self.del_btn.setIcon(QtGui.QIcon('assets/delete.svg'))

                self.hide()

            def open_folder(self):
                if Path.exists(Path(self.parent_item.path.text())):
                    QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.parent_item.path.text()))
                else:
                    self.parent_item.list.parent().message.error('无法打开文件夹，可能版本文件夹本体已被删除！')
            
            def delete_ver(self):
                pass

            @DeprecationWarning
            def display_ui(self):
                effect = self.graphicsEffect()
                anim = QtCore.QPropertyAnimation(effect, b"opacity")
                anim.setDuration(300)
                anim.setStartValue(effect.opacity())
                anim.setEndValue(1.0)
                anim.start()

            @DeprecationWarning
            def hide_ui(self):
                effect = self.graphicsEffect()
                anim = QtCore.QPropertyAnimation(effect, b"opacity")
                anim.setDuration(300)
                anim.setStartValue(effect.opacity())
                anim.setEndValue(0.0)
                anim.finished.connect(self.hide)
                anim.start()
                self.show()  # 确保在动画期间可见


    class VersionList(QtWidgets.QListWidget):
        def __init__(self, version_list: list[dict], parent_widget=None):
            super().__init__(parent=parent_widget)
            # 样式设置
            for version in version_list:
                self.add_version(Migrate.VersionItem(version, self))
            self.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.setSpacing(5)

            # 通过监听滑条移动来动态调整实现VersionItem的FloatBar工具栏与列表相对静止
            self.hover_item: Migrate.VersionItem = None
            self.scroll_max = self.horizontalScrollBar().maximum()
            self.scroll_pagestep = self.horizontalScrollBar().pageStep()
            print(self.scroll_max, self.scroll_pagestep, self.horizontalScrollBar().value())
            
            self.horizontalScrollBar().valueChanged.connect(self.on_scroll)
        
        # 保持水平移动列表时，悬浮工具栏仍可以相对固定列表靠右处
        def on_scroll(self, value: int):
            if self.hover_item:
                self.hover_item.float_bar.move(self.viewport().width() - self.hover_item.float_bar.width() - 10 + value, 5)
        
        def add_version(self, version_item: 'Migrate.VersionItem'):
            item = QtWidgets.QListWidgetItem()
            self.addItem(item)
            item.setSizeHint(version_item.sizeHint())
            self.setItemWidget(item, version_item)
        
        def update_versions(self, versions: list[dict]):
            self.clear()
            for ver in versions:
                self.add_version(Migrate.VersionItem(ver))
            logging.info("已更新版本列表")
            
class ButtonMigrateDetail(QtWidgets.QPushButton):
    def __init__(self, terminal: Terminal, parent_widget=None):
        super().__init__(self, parent_widget)
        self.setObjectName('button_migrate_detail')
        self.setFixedSize(70, 70)
        self.setParent(self)
        layout_detail = QtWidgets.QVBoxLayout()
        self.setLayout(layout_detail)
        self.setStyleSheet(load_stylesheet("qss/migrate.qss"))
        self.clicked.connect(self.button_migrate_detail_clicked)

        self.ring = Geometry.LoadingRingText(QtGui.QColor("#EDFFFE"), QtGui.QColor("#EDFFFE"), parent=self)
        layout_detail.addWidget(self.ring, 1, QtCore.Qt.AlignCenter)
        
        self.percent_update_timer = QtCore.QTimer()
        self.percent_update_timer.timeout.connect(lambda: self.percent_update(timer=self.percent_update_timer, ring=self.ring))
        self.percent_update_timer.start(12)

        self.move(self.width() - 100, self.height() - 135)
        self.show()
        self.raise_()

    def button_migrate_detail_clicked(self):
        pass