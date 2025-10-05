import logging
from PySide6 import QtWidgets, QtGui, QtCore
from Terminal import Terminal
from pathlib import Path
import Geometry, json, os

logging.basicConfig(level=logging.INFO)

# 欢迎界面
class Welcome(QtWidgets.QFrame):
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
        if version_path and version_path != Path("."):
            self.terminal.add_version(version_path)
            with open("versions.json", 'r', encoding='utf-8') as f:
                try:
                    versions = json.load(f)
                    migrate = Migrate(terminal=self.terminal, version_paths=versions)
                    self.terminal.window.setCentralWidget(migrate)
                except:
                    logging.error("解析versions.json文件失败")
                    welcome = Welcome(terminal=self.terminal)
                    self.terminal.window.setCentralWidget(welcome)

class Migrate(QtWidgets.QFrame):
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
        self.ver_list_source = Migrate.VersionList(version_paths)
        self.ver_list_target = Migrate.VersionList(version_paths)
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

        #
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
        if self.terminal.is_migrating:
            logging.info("请先等待迁移完成")
            return
        ver_source: Migrate.VersionItem = self.ver_list_source.itemWidget(self.ver_list_source.currentItem())
        ver_target: Migrate.VersionItem = self.ver_list_target.itemWidget(self.ver_list_target.currentItem())
        if ver_source == None or ver_target == None:
            logging.info("请先选择迁移版本和目标版本")
            return

        self.terminal.migrate(source_json=ver_source.json, target_json=ver_target.json)
        
        self.button_migrate_detail = QtWidgets.QPushButton(parent=self.parent())
        self.button_migrate_detail.setObjectName('button_migrate_detail')
        self.button_migrate_detail.setFixedSize(70, 70)
        self.button_migrate_detail.setParent(self)
        layout_detail = QtWidgets.QVBoxLayout()
        self.button_migrate_detail.setLayout(layout_detail)
        self.button_migrate_detail.setStyleSheet(load_stylesheet("qss/migrate.qss"))
        self.button_migrate_detail.clicked.connect(self.button_migrate_detail_clicked)

        self.ring = Geometry.LoadingRingText(QtGui.QColor("#EDFFFE"), QtGui.QColor("#EDFFFE"), parent=self.button_migrate_detail)
        layout_detail.addWidget(self.ring, 1, QtCore.Qt.AlignCenter)
        
        self.percent_update_timer = QtCore.QTimer()
        self.percent_update_timer.timeout.connect(lambda: self.percent_update(timer=self.percent_update_timer, ring=self.ring))
        self.percent_update_timer.start(12)

        self.button_migrate_detail.move(self.width() - 100, self.height() - 135)
        self.button_migrate_detail.show()
        self.button_migrate_detail.raise_()
    
    def percent_update(self, timer: QtCore.QTimer, ring: Geometry.LoadingRingText):
        ring.change_percent(self.terminal.pending_num)
        if self.terminal.pending_num == 0 and not self.terminal.is_migrating:
            timer.stop()
            timer.deleteLater()

    def button_migrate_detail_clicked(self):
        pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'button_migrate_detail'):
            self.button_migrate_detail.move(self.width() - 100, self.height() - 135)
    

    class VersionItem(QtWidgets.QWidget):
        def __init__(self, json: dict):
            super().__init__()
            self.setObjectName("VersionItem")

            # info
            self.json = json
            self.name = QtWidgets.QLabel(json.get('name', "未知版本名"))
            self.ver = QtWidgets.QLabel(json.get('version', '未知版本'))
            self.path = QtWidgets.QLabel(json.get('game_path', '未知路径'))
            self.mod_loader = QtWidgets.QLabel(json.get('mod_loader', '未知Mod加载器'))

            self.name.setObjectName('name_label')
            self.name.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.ver.setObjectName("version_label")
            self.ver.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.path.setObjectName("path_label")
            self.path.setStyleSheet(load_stylesheet("qss/migrate.qss"))

            # icon
            self.mod_loader_icon = self.get_icon(self.mod_loader.text())
            self.mod_loader_icon.setObjectName("mod_loader_icon")
            self.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.mod_loader_icon.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.mod_loader.setObjectName('mod_loader_label')
            self.mod_loader.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            # layout
            self.info_layout = QtWidgets.QVBoxLayout()

            self.info_name_layout = QtWidgets.QHBoxLayout()
            self.info_name_layout.addStretch()
            self.info_name_layout.addWidget(self.mod_loader, 0)

            if not json.get('is_indie', False):
                self.is_indie = QtWidgets.QLabel('非隔离版本')
                self.is_indie.setObjectName('indie_label')
                self.is_indie.setStyleSheet(load_stylesheet("qss/migrate.qss"))
                self.info_name_layout.addWidget(self.is_indie, 0)

            self.info_name_layout.addWidget(self.name, 1)
            self.info_name_layout.setDirection(QtWidgets.QBoxLayout.LeftToRight)
            self.info_name = QtWidgets.QWidget()
            self.info_name.setObjectName('info_name')
            self.info_name.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.info_name.setLayout(self.info_name_layout)

            self.info_detail_layout = QtWidgets.QHBoxLayout()
            self.info_detail = QtWidgets.QWidget()
            self.info_detail_layout.addStretch()
            self.info_detail.setObjectName('info_detail')
            self.info_detail.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.info_detail_layout.addWidget(self.ver, 0)
            self.info_detail_layout.addWidget(self.path, 1)
            self.info_detail.setLayout(self.info_detail_layout)

            self.info_layout.addWidget(self.info_name)
            self.info_layout.addWidget(self.info_detail)

            self.info = QtWidgets.QWidget()
            self.info.setObjectName('info')
            self.info.setStyleSheet(load_stylesheet("qss/migrate.qss"))
            self.info.setLayout(self.info_layout)

            self.layout = QtWidgets.QHBoxLayout()
            self.layout.addWidget(self.mod_loader_icon, 0)
            self.layout.addWidget(self.info, 1)
            
            self.setLayout(self.layout)



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
        
    class VersionList(QtWidgets.QListWidget):
        def __init__(self, version_list: list[dict]):
            super().__init__()
            self.setSpacing(8)
            
            for version in version_list:
                self.add_version(Migrate.VersionItem(version))
            self.setStyleSheet(load_stylesheet("qss/migrate.qss"))
        
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

class MigrateDetail(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()

def load_stylesheet(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"加载样式表失败: {e}")
        return ""