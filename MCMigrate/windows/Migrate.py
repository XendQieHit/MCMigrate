import logging, json, time
from PySide6 import QtWidgets, QtGui, QtCore
from terminal.Terminal import Terminal, TaskMigrateAbortable
from pathlib import Path

from windows.SendMessageable import SendMessageable
from windows.MainWindow import MainWindow
from message import Message, Dialog
from core.func import *
from core.ClientLibs import ColorIconGenerator
from core import WidgetLibs
import Geometry, MCException, Animation

class Migrate(SendMessageable):
    '''版本迁移界面，以terminal.games_json作为版本数据来源'''
    def __init__(self, terminal: Terminal, migrate_task: TaskMigrateAbortable=None):
        super().__init__(terminal.main_window)
        self.terminal = terminal
        self.migrate_task = migrate_task
        self.setWindowTitle("MCMigrator")
        self.setWindowIcon(QtGui.QIcon(resource_path("assets/icon_64x64.png")))
        self.layout = QtWidgets.QVBoxLayout()

        # 顶部栏
        self.top_bar = QtWidgets.QWidget()
        self.top_bar.setLayout(QtWidgets.QHBoxLayout())
        self.layout.addWidget(self.top_bar, 0)
        # 标题
        self.window_title = QtWidgets.QLabel("选择要迁移的版本", self)
        self.window_title.setStyleSheet("font-size: 18px; color: #666666")
        self.top_bar.layout().addWidget(self.window_title, 1)
        self.top_bar.setFixedHeight(self.window_title.height())
        self.top_bar.layout().addStretch()
        self.top_bar.layout().setContentsMargins(2,0,2,0)
        # 刷新全部版本按钮
        self.refresh_all_vers_btn = WidgetLibs.TransparentColorButton(QtGui.QColor("#77D380"), QtGui.QColor("#4BBD68"), resource_path("assets/refresh.svg"), '刷新所有版本信息', self)
        self.refresh_all_vers_btn.clicked.connect(lambda: self.dialog.info(
            "确定刷新所有版本？",
            "操作过程中，可能需要你再次确认版本隔离情况。\n版本数量很多时，执行该操作可能需要一些时间。\n\n确定要刷新所有版本吗？",
            (
                "确定",
                Dialog.Level.DONE,
                self.button_refresh_all_vers_clicked
            ),
            close_when_clicked_any_btn=True
        ))
        self.top_bar.layout().addWidget(self.refresh_all_vers_btn, 0)
        # 清空所有版本按钮
        self.clear_all_vers_btn = WidgetLibs.TransparentColorButton(QtGui.QColor("#f05f5a"), QtGui.QColor("#d94641"), resource_path("assets/delete.svg"), '清除所有游戏目录', self) # 是的你的ide没有出错，QColor应用在QGraphicsColorizeEffect时，alpha通道值要放前面
        self.clear_all_vers_btn.clicked.connect(lambda: self.dialog.error(
            "确定清除所有游戏目录？",
            "该操作将会清除列表里的所有游戏文件夹！\n该操作不会对游戏文件本体产生影响。\n\n确定要清除所有游戏目录吗？",
            (
                "确定",
                Dialog.Level.ERROR,
                self.btn_clear_all_vers_clicked
            ),
            close_when_clicked_any_btn=True
        ))
        self.top_bar.layout().addWidget(self.clear_all_vers_btn, 0)
        # github链接
        self.github_url = WidgetLibs.TransparentColorButton(QtGui.QColor("#202020"), QtGui.QColor("#101010"), resource_path('assets/icon/github.svg'), '前往MCMigrate的Github仓库', self)
        self.github_url.clicked.connect(lambda: self.dialog.info(
            "即将跳转至Github",
            "即将前往MCMigrate的Github仓库。\n如果在使用MCMigrate过程中遇到了Bug，或是其他想要的功能，可以在MCMigrate的Github仓库上的提出Issue来！",
            (
                "出发！",
                Dialog.Level.DONE,
                lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl('https://github.com/XendQieHit/MCMigrate')),
                {'hover_text': "前往MCMigrate的Github仓库"}
            ),
            close_when_clicked_any_btn=True
        ))
        self.github_url.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.top_bar.layout().addWidget(self.github_url, 0)

        # 版本列表
        self.list_box = QtWidgets.QHBoxLayout()
        self.game_view_source = GameView(self.terminal.get_games(), self, self)
        self.game_view_target = GameView(self.terminal.get_games(), self, self)
        logging.info(f"{self.game_view_source.game_selector.get_items_text()}")
        self.list_box.addWidget(self.game_view_source)
        self.arrow = Geometry.Arrow(self.game_view_source, self.game_view_target, "#aaaaaa")
        self.arrow.setMaximumSize(self.window().height() * 0.05, self.window().width() * 0.05)
        self.list_box.addWidget(self.arrow, 0, QtCore.Qt.AlignCenter)
        self.list_box.addWidget(self.game_view_target)
        self.layout.addLayout(self.list_box)

        # 底部按钮
        self.button_box = QtWidgets.QHBoxLayout()
        self.button_import = QtWidgets.QPushButton("导入版本路径")
        self.button_import.setObjectName("button_import")
        self.button_import.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
        self.button_import.clicked.connect(self.button_import_clicked)
        self.button_migrate = QtWidgets.QPushButton("开始迁移")
        self.button_migrate.setObjectName("button_migrate")
        self.button_migrate.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
        self.button_migrate.clicked.connect(self.button_migrate_clicked)
        self.button_box.addWidget(self.button_import)
        self.button_box.addWidget(self.button_migrate)
        self.layout.addLayout(self.button_box)
        
        # 布局调整
        self.setLayout(self.layout)

        # 如果已经有迁移任务在进行，把任务详情的悬浮窗添加进来
        if self.migrate_task:
            self.button_migrate_detail = ButtonMigrateDetail(self.terminal, self)
            self.button_migrate_detail.set_migrate_task(self.migrate_task)
            self.migrate_task.update_migrate_general.connect(self.button_migrate_detail.update_percent)
            self.button_migrate_detail.show_directly()
            self.terminal.thread_migrate.finished.connect(self.button_migrate_detail.close_with_animation)
            if not self.migrate_task.is_calculating:
                self.button_migrate_detail.update_percent()

        # 用户操作记录部分
        self.load_app_state()

    def load_app_state(self):
        '''加载app_state.json中的窗口状态'''
        # 游戏文件夹的选择
        ## 读取选择记录
        try:
            if latest_game_folder_path:= get_app_state()['migrate']['latest_game_folder_path']:
                if source:= self.terminal.get_game_by_path(latest_game_folder_path['source']):
                    self.game_view_source.switch_game_by_dict(source)
                if target:= self.terminal.get_game_by_path(latest_game_folder_path['target']):
                    self.game_view_target.switch_game_by_dict(target)
        except Exception:
            logging.warning('加载app_state.json读取历史操作状态失败，使用默认设置')
        ## 关联切换游戏目录信号以记录操作
        def save_latest_game_folder_path(game_item: GameSelector.GameItem, is_source: bool):
            state = get_app_state()
            latest_game_folder_path = state['migrate'].get('latest_game_folder_path', None)
            if latest_game_folder_path is None:
                latest_game_folder_path = {'source': None, 'target': None}
            logging.debug(f"latest_game_folder_path: {latest_game_folder_path}")
            if is_source:
                latest_game_folder_path['source'] = game_item.data['folder_path']
            else:
                latest_game_folder_path['target'] = game_item.data['folder_path']
            modify_app_state(latest_game_folder_path, 'migrate', 'latest_game_folder_path')
        self.game_view_source.switched.connect(lambda game_item: save_latest_game_folder_path(game_item, True))
        self.game_view_target.switched.connect(lambda game_item: save_latest_game_folder_path(game_item, False))

    def button_refresh_all_vers_clicked(self):
        if versions:= self.terminal.refresh_all_games():
            # 刷新版本列表，如果遇到需要询问版本隔离的情况的话，下面代码不会执行，而是terminal手动执行switch_window()方法来刷新界面
            self.game_view_source.update_games(versions)
            self.game_view_target.update_games(versions)
            self.window().update()

    def button_import_clicked(self):
        if versions:= self.terminal.import_version():
            # 刷新版本列表，如果遇到需要询问版本隔离的情况的话，下面代码不会执行，而是terminal手动执行switch_window()方法来刷新界面
            self.game_view_source.update_games(versions)
            self.game_view_target.update_games(versions)
            self.window().update()
            self.message.done("版本导入成功！")

    def button_migrate_clicked(self):
        # 条件检测
        if self.terminal.thread_migrate.isRunning():
            self.message.info("请先等待迁移完成")
            return
        ver_source: dict = self.game_view_source.current_version()
        ver_target: dict = self.game_view_target.current_version()
        if ver_source == None or ver_target == None:
            logging.info("请先选择迁移版本和目标版本")
            self.message.info("请先选择迁移版本和目标版本")
            return

        # 添加任务详情悬浮按钮
        self.button_migrate_detail = ButtonMigrateDetail(self.terminal, self)
        self.terminal.thread_migrate.finished.connect(self.button_migrate_detail.close_with_animation)
        self.message.info(f"正在迁移 {ver_source.get('name')} 至 {ver_target.get('name')}")
        
        # 开始线程任务
        try:
            self.terminal.migrate(source_json=ver_source, target_json=ver_target)
        except MCException.VersionVerifyFailed as e:
            self.message.show_message(str(e), e.level)
            self.button_migrate_detail.close()
            return
        self.button_migrate_detail.set_migrate_task(self.terminal.task_migrate)
        self.terminal.task_migrate.update_migrate_general.connect(self.button_migrate_detail.update_percent)
        self.button_migrate_detail.show_with_animation()
    
    def update_game(self):
        self.game_view_target.update_games(self.terminal.get_games())
        self.game_view_source.update_games(self.terminal.get_games())

    def btn_clear_all_vers_clicked(self):
        self.terminal.clear_all_games()
        self.message.done("已清除所有游戏文件夹!")
        self.terminal.switch_window(Terminal.WindowEnum.WELCOME)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'button_migrate_detail'):
            self.button_migrate_detail.move(self.width() - 100, self.height() - 135)

class VersionList(QtWidgets.QListWidget):
    '''
    Args:
        game_json(dict): 游戏目录json
    '''
    def __init__(self, game_json: dict, parent, migrate_window: Migrate):
        super().__init__(parent)
        self.migrate_window = migrate_window
        self.game_json = game_json
        # 样式设置
        for ver in game_json['versions']:
            self.add_item(VersionItem(ver, self))
        self.setStyleSheet(resource_path(load_stylesheet(resource_path("qss/migrate.qss"))))
        self.setSpacing(5)

        # 通过监听滑条移动来动态调整实现VersionItem的FloatBar工具栏与列表相对静止
        self.hover_item: VersionItem = None
        self.h_scroll_value = 0
        self.scroll_max = self.horizontalScrollBar().maximum()
        self.scroll_pagestep = self.horizontalScrollBar().pageStep()
        
        self.horizontalScrollBar().valueChanged.connect(self.on_scroll)
    
    # 保持水平移动列表时，悬浮工具栏仍可以相对固定列表靠右处
    def on_scroll(self, value: int):
        self.h_scroll_value = value
        if self.hover_item:
            self.hover_item.float_bar.move(self.viewport().width() - self.hover_item.float_bar.width() - 10 + value, 5)
    
    def add_item(self, version_item: 'VersionItem'):
        item = QtWidgets.QListWidgetItem()
        self.addItem(item)
        item.setSizeHint(version_item.sizeHint())
        self.setItemWidget(item, version_item)
    
    def apply_game(self, game_json: dict):
        '''
        应用版本列表
        Args:
            versions(dict): 游戏目录json
        '''
        self.clear()
        self.game_json = game_json
        if isinstance(game_json, dict): # 游戏目录dict
            for ver in game_json['versions']:
                self.add_item(VersionItem(ver, self))
        elif isinstance(game_json, list): # 游戏版本列表
            for ver in game_json:
                self.add_item(VersionItem(ver, self))
        logging.debug("已更新版本列表")

    def refresh(self):
        '''更新版本列表'''
        game_json = self.migrate_window.terminal.get_game_by_path(self.game_json['folder_path'])
        if game_json:
            self.apply_game(game_json)
        else: # 该游戏目录不存在
            raise MCException.NoSuchGameFolder()


class VersionItem(QtWidgets.QWidget):
    def __init__(self, json: dict, parent_list: VersionList):
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
        self.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
        self.mod_loader_icon.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
        self.layout().addWidget(self.mod_loader_icon, 0)

        # 版本信息容器
        self.info = QtWidgets.QWidget()
        self.info.setObjectName('info')
        self.info.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
        self.info_layout = QtWidgets.QVBoxLayout()
        self.info_layout.setSpacing(0)
        self.info_layout.setContentsMargins(0, 0, 0, 0)
        self.info.setLayout(self.info_layout)
        self.layout().addWidget(self.info, 1)

        # 游戏版本名及其加载器、版本隔离标签的容器
        self.info_name = QtWidgets.QWidget()
        self.info_name.setObjectName('info_name')
        self.info_name.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
        self.info_name_layout = QtWidgets.QHBoxLayout()
        self.info_name.setLayout(self.info_name_layout)
        self.info_layout.addWidget(self.info_name)

        # 启动器标签
        self.launcher = QtWidgets.QLabel(json.get('launcher', '未知启动器') or '未知启动器')
        self.launcher.setObjectName('launcher_label')
        self.launcher.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
        self.info_name_layout.addWidget(self.launcher, 0)

        # 加载器标签
        self.mod_loader = QtWidgets.QLabel(json.get('mod_loader', '未知Mod加载器'))
        self.mod_loader.setObjectName('mod_loader_label')
        self.mod_loader.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
        self.info_name_layout.addWidget(self.mod_loader, 0)

        # 版本隔离标签
        if not json.get('is_indie', False):
            self.is_indie = QtWidgets.QLabel('非隔离版本')
            self.is_indie.setObjectName('indie_label')
            self.is_indie.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
            self.info_name_layout.addWidget(self.is_indie, 0)

        # 游戏版本名
        self.name = QtWidgets.QLabel(json.get('name', "未知版本名"))
        self.name.setObjectName('name_label')
        self.name.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
        self.info_name_layout.addWidget(self.name, 1)

        self.info_name_layout.addStretch()

        # 版本号、启动器标签和版本文件路径的容器
        self.info_detail = QtWidgets.QWidget()
        self.info_detail.setObjectName('info_detail')
        self.info_detail.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
        self.info_detail_layout = QtWidgets.QHBoxLayout()
        self.info_detail.setLayout(self.info_detail_layout)
        self.info_layout.addWidget(self.info_detail)

        # 版本号
        self.ver = QtWidgets.QLabel(json.get('version', '未知版本'))
        self.ver.setObjectName("version_label")
        self.ver.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
        self.info_detail_layout.addWidget(self.ver, 0)

        # 版本文件路径
        self.path = QtWidgets.QLabel(json.get('game_path', '未知路径'))
        self.path.setObjectName("path_label")
        self.path.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))
        self.info_detail_layout.addWidget(self.path, 1)

        self.info_detail_layout.addStretch()

        # 悬浮操作栏
        self.float_bar = VersionItem.FloatBar(self, self.list.migrate_window)

    def resizeEvent(self, event): # 这里存放根据卡片大小来确定自身大小的widget
        self.float_bar.setFixedSize(50, self.height()-10)
        super().resizeEvent(event)
    
    # 悬浮工具栏的显示逻辑
    def enterEvent(self, event):
        self.float_bar.move(self.list.viewport().width() - self.float_bar.width() - 10 + self.list.h_scroll_value, 5)
        self.float_bar.display_ui()
        self.list.hover_item = self
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.list.hover_item = None
        self.float_bar.hide_ui()
        super().leaveEvent(event)

    def get_icon(self, mod_loader: str = None) -> QtWidgets.QLabel:
        mod_loaders = {
            "fabric": resource_path("assets/icon/fabric.png"),
            "neoforge": resource_path("assets/icon/neoforge.png"),
            "forge": resource_path("assets/icon/forge.png"),
            "quilt": resource_path("assets/icon/quilt.png"),
            "release": resource_path("assets/icon/release.png"),
            "optifine": resource_path("assets/icon/optifine.png"),
            "snapshot": resource_path("assets/icon/snapshot.png"),
            "unknown": resource_path("assets/icon/unknown.png")
        }
        for key in mod_loaders.keys():
            if key in (mod_loader or "").lower():
                pixmap = QtGui.QPixmap(mod_loaders[key]).scaled(36, 36)
                label = QtWidgets.QLabel()
                label.setPixmap(pixmap)
                return label
                
        pixmap = QtGui.QPixmap(resource_path("assets/icon/unknown.png")).scaled(36, 36)
        label = QtWidgets.QLabel()
        label.setPixmap(pixmap)
        return label
    
    class FloatBar(QtWidgets.QFrame):
        def __init__(self, parent_widget: 'VersionItem', migrate_window: Migrate):
            super().__init__(parent_widget)
            self.parent_item = parent_widget
            self.migrate_window = migrate_window
            # 总样式设置
            self.setLayout(QtWidgets.QVBoxLayout())
            self.layout().setSpacing(2)

            self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
            self.setObjectName('float_bar')
            self.setStyleSheet(load_stylesheet(resource_path('qss/migrate.qss')))

            # 打开文件夹
            # 按钮
            self.folder_btn = QtWidgets.QPushButton()
            self.folder_btn.setObjectName('folder_btn')
            self.folder_btn.setStyleSheet(load_stylesheet(resource_path('qss/migrate.qss')))
            self.folder_btn.setContentsMargins(0,0,0,0)
            self.folder_btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            self.folder_btn.setToolTip('打开该版本文件夹')
            self.folder_btn.clicked.connect(self.open_folder)
            self.folder_btn.setIcon(QtGui.QIcon(resource_path('assets/folder.svg')))
            self.layout().addWidget(self.folder_btn)

            # 删除键
            # 按钮
            self.del_btn = QtWidgets.QPushButton()
            self.del_btn.setObjectName('del_btn')
            self.del_btn.setStyleSheet(load_stylesheet(resource_path('qss/migrate.qss')))
            self.del_btn.setContentsMargins(0,0,0,0)
            self.del_btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            self.del_btn.setToolTip('从列表中移除该版本（不会删除本体文件）')
            self.del_btn.clicked.connect(self.delete_ver)
            self.layout().addWidget(self.del_btn)
            # icon
            self.del_btn.setIcon(QtGui.QIcon(resource_path('assets/delete.svg')))

            self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
            self.opacity_effect.setOpacity(0.0)
            self.setGraphicsEffect(self.opacity_effect)
            self.hide()

        def open_folder(self):
            if Path.exists(Path(self.parent_item.path.text())):
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.parent_item.path.text()))
            else:
                self.migrate_window.message.error('无法打开文件夹，可能版本文件夹本体已被删除！')
        
        def delete_ver(self):
            def delete():
                try:
                    # 从列表中移除目标条目
                    try:
                        self.migrate_window.terminal.remove_version(self.parent_item.list.game_json, self.parent_item.json)
                    except MCException.NoSuchVersion:
                        self.migrate_window.message.info("未在列表中找到该版本，已跳过移除。")
                        return
                    except MCException.NoSuchGameFolder:
                        self.migrate_window.message.info("未在列表中找到该版本所属的游戏目录，已跳过移除。")
                        ### 这里要补足去除该游戏目录或是重新刷新版本列表的逻辑
                        return
                        
                    # 更新界面列表（同时更新源和目标列表）
                    try:
                        self.parent_item.list.migrate_window.game_view_source.refresh_list_view()
                        self.parent_item.list.migrate_window.game_view_target.refresh_list_view()
                    except Exception:
                        logging.exception("更新版本列表 UI 时出错")

                except (OSError, IOError) as e:
                    logging.exception("文件操作失败")
                    self.migrate_window.message.error(f"文件操作失败：{e}")
                except json.JSONDecodeError as e:
                    logging.exception("JSON 解析失败")
                    self.migrate_window.message.error(f"读取版本列表失败：{e}")
                except Exception as e:
                    logging.exception("移除版本时发生未知错误")
                    self.migrate_window.message.error(f"移除版本失败：{e}")
                self.migrate_window.message.done("已成功移除 ！")

            self.migrate_window.dialog.warning(
                "确定要从列表中移除该版本吗？",
                "在列表中移除该版本不会对游戏文件产生影响。",
                ("确定", Dialog.Level.ERROR, delete),
                close_when_clicked_any_btn=True
            )

        def display_ui(self):
            self.show()
            self.anim = QtCore.QPropertyAnimation(self.graphicsEffect(), b"opacity")
            self.anim.setDuration(60)
            self.anim.setStartValue(self.graphicsEffect().opacity())
            self.anim.setEndValue(1.0)
            self.anim.start()

        def hide_ui(self):
            self.anim = QtCore.QPropertyAnimation(self.graphicsEffect(), b"opacity")
            self.anim.setDuration(60)
            self.anim.setStartValue(self.graphicsEffect().opacity())
            self.anim.setEndValue(0.0)
            self.anim.finished.connect(self.hide)
            self.anim.start()
            self.show()  # 确保在动画期间可见
            
class GameView(QtWidgets.QFrame):
    switched = QtCore.Signal(object) # 切换游戏目录时发出的信号，参数为游戏目录json
    def __init__(self, games_json: list[dict], parent, migrate_window: Migrate):
        super().__init__(parent)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(2,2,2,2)
        self.migrate_window = migrate_window # 用于弹窗消息的发送
        self.games_json = games_json # 游戏文件夹json
        self.current_game_item: GameSelector.GameItem = None

        # 顶部栏（游戏文件夹选项+打开文件夹按钮）
        self.top_bar = QtWidgets.QWidget(self)
        self.top_bar.setLayout(QtWidgets.QHBoxLayout())
        self.top_bar.layout().setContentsMargins(0,0,0,0)
        self.top_bar.layout().setSpacing(1)
        self.layout().addWidget(self.top_bar)
        # 游戏文件夹选项
        self.game_selector = GameSelector(self.games_json[0]['folder_name'], self, migrate_window)
        self.top_bar.layout().addWidget(self.game_selector, 2)
        self.game_selector.update(self.games_json) # 加载选项
        self.top_bar.setMaximumHeight(self.game_selector.height()) # 将游戏文件夹选项的高度设置为最大高度
        # 刷新按钮
        self.refresh_btn = WidgetLibs.TransparentColorButton(QtGui.QColor("#77D380"), QtGui.QColor("#4BBD68"), resource_path("assets/refresh.svg"), '刷新该游戏文件夹', self.top_bar)
        self.refresh_btn.setFixedWidth(32)
        def refresh_game():
            try:
                if new_games:= migrate_window.terminal.refresh_game(self.version_view.game_json):
                    d_versions_num = len(migrate_window.terminal.get_game_by_path(self.current_game_item.data['folder_path'])['versions']) - len(self.current_game_item.data['versions'])
                    text = ''
                    if d_versions_num < 0:
                        text += f'减少{-d_versions_num}个版本'
                    else:
                        text += f'增加{d_versions_num}个版本'
                    self.migrate_window.message.done('已更新游戏版本列表,' + text)
                    self.update_games(new_games)
            except MCException.NoSuchGameFolder:
                self.migrate_window.message.info('该游戏目录不存在, 已自动清除')
                self.update_games(self.migrate_window.terminal.get_games())
            
        self.refresh_btn.clicked.connect(refresh_game)
        self.top_bar.layout().addWidget(self.refresh_btn)
        # 打开文件夹按钮
        self.folder_btn = WidgetLibs.TransparentColorButton(QtGui.QColor('#deffcf3e'), QtGui.QColor('#dfc99b3e'), resource_path('assets/folder.svg'), '打开该游戏文件夹', self.top_bar)
        self.folder_btn.setFixedWidth(32)
        self.folder_btn.clicked.connect(self.open_folder)
        self.top_bar.layout().addWidget(self.folder_btn, 0)

        # 版本列表
        self.version_view = VersionList(self.games_json[0], self, migrate_window)
        self.layout().addWidget(self.version_view)

        # 将选中的游戏版本信息的信号，绑定给版本列表
        self.game_selector.selected.connect(self.switch_game)
    
    def open_folder(self):
        path = Path(self.current_game_item.data['folder_path'])
        if Path.exists(path):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path.as_posix()))
        else:
            self.migrate_window.message.error('无法打开文件夹，可能游戏文件夹本体已被删除！')

    def current_version(self):
        return self.version_view.itemWidget(self.version_view.currentItem()).json

    def switch_game(self, game_item: 'GameSelector.GameItem'):
        '''切换游戏目录'''
        self.current_game_item = game_item
        self.game_selector.set_text(self.current_game_item.data['folder_name'])
        self.version_view.apply_game(self.current_game_item.data)
        self.switched.emit(game_item)

    def switch_game_by_dict(self, game_folder_path: dict):
        try:
            i = self.game_selector.list.items_data.index(game_folder_path)
            game_item = self.game_selector.list.items[i]
        except ValueError:
            logging.error("无法切换游戏目录，未在列表中找到对应目录")
            return
        # 切换目录
        self.switch_game(game_item)

    def refresh_list_view(self):
        '''刷新当前游戏目录的版本列表'''
        try:
            self.version_view.refresh()
        except MCException.NoSuchGameFolder:
            logging.warning("未找到该游戏文件夹")

    def update_games(self, games_json: list[dict]):
        '''更新游戏目录列表'''
        self.games_json = games_json
        
        # 更新选项卡列表
        self.game_selector.update(games_json)

        # 更新版本列表
        try:
            self.version_view.refresh()
        except MCException.NoSuchGameFolder: # 原游戏文件夹不存在，加载第一个游戏文件夹
            try:
                self.switch_game(self.game_selector.list.items[0])
            except ValueError: # 连第一个也没有了，直接抛错加载Welcome界面把
                self.migrate_window.terminal.switch_window_with_msg(Terminal.WindowEnum.WELCOME, ("没有游戏目录，已跳转至开始界面", Message.Level.WARNING))

class GameSelector(WidgetLibs.CollapsibleBox):
    def __init__(self, text, parent, migrate_window: Migrate, games_json: list[dict]=None):
        super().__init__(text, parent, migrate_window.terminal.main_window)
        self.list = GameSelector.GameList(self, migrate_window)
        self.current_item = None
        if games_json:
            self.update(games_json)
    
    def add_item(self, text, data=None):
        '''
        添加游戏目录选项
        Args:
            text(str): 游戏选项显示文本
            data(dict): 游戏选项的json
        '''
        item = self.list.add_item(text, data)
        if self.current_item is None: # 设置第一个添加的为当前选中项
            self.current_item = item

    def update(self, games_json: list[dict]):
        '''更新游戏目录所有选项'''
        self.list.update_items(games_json)
    
    class GameList(WidgetLibs.CollapsibleBox.ItemList):
        def __init__(self, parent, migrate_window: Migrate, max_height = 200, fixed_width = 240):
            super().__init__(parent, max_height, fixed_width, migrate_window.terminal.main_window)
            self.migrate_window = migrate_window
            self.hover_item: GameSelector.GameItem
            self.horizontalScrollBar().valueChanged.connect(self.on_scroll)
            self.h_scroll_value = 0 # 当前水平滚动条位置
            self.items: list[GameSelector.GameItem] = []
            self.items_text: list[str] = []
            self.items_data: list[dict] = []
            self.latest_clicked_time = time.time()

        def add_item(self, text, data=None):
            '''
            添加游戏目录选项
            Args:
                text(str): 游戏选项显示文本
                data(dict): 游戏选项的json
            '''
            item = GameSelector.GameItem(text, data, self, self.migrate_window)
            self.items.append(item)
            self.items_text.append(text)
            self.items_data.append(data)
            self.container.layout().addWidget(item)
            return item

        def update_items(self, games_json: list[dict]):
            '''更新游戏目录所有选项'''
            self.clear()
            for game in games_json:
                self.add_item(game['folder_name'], game)
        
        def clear(self):
            '''清空所有选项'''
            super().clear()
            self.items.clear()
            self.items_text.clear()
            self.items_data.clear()
        
        # 保持水平移动列表时，悬浮工具栏仍可以相对固定列表靠右处
        def on_scroll(self, value: int):
            self.h_scroll_value = value # 更新当前滑条位置
            # 让滑动的时候也能同步相对静止悬浮按钮的位置
            if self.hover_item:
                self.hover_item.float_bar.move(
                    self.viewport().width() - self.hover_item.float_bar.width() - 20 + value, self.hover_item.height()/2 - self.hover_item.float_bar.height()/2
                )

    class GameItem(WidgetLibs.CollapsibleBox.Item):
        def __init__(self, text, data: dict, parent: 'GameSelector.GameList', migrate_window: Migrate):
            super().__init__(text, data, parent)
            self.list = parent
            self.float_bar = GameSelector.GameItem.FloatBar(self, migrate_window)
            parent.on_scroll(0)  # 初始化悬浮按钮位置

        def enterEvent(self, event):
            # 根据列表当前滚动条位置调整悬浮栏位置
            self.float_bar.move(self.list.viewport().width() - self.float_bar.width() - 20 + self.list.h_scroll_value, self.height()/2 - self.float_bar.height()/2)

            super().enterEvent(event)
            # 显示悬浮栏
            self.float_bar.raise_()
            self.float_bar.display_ui()

        def leaveEvent(self, event):
            self.float_bar.hide_ui()
            return super().leaveEvent(event)

        class FloatBar(QtWidgets.QFrame):
            def __init__(self, parent_item: 'GameSelector.GameItem', migrate_window: Migrate):
                super().__init__(parent_item)
                self.parent_item = parent_item
                self.migrate_window = migrate_window
                # 总样式设置
                self.setLayout(QtWidgets.QHBoxLayout())
                self.layout().setContentsMargins(0,0,0,0)
                self.layout().setSpacing(2)
                self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
                self.setFixedWidth(28) # 本来是想根据按钮的高度来调整宽度的，算了先这样硬编码吧
                self.setObjectName('float_bar')
                self.setStyleSheet(load_stylesheet(resource_path('qss/migrate.qss')))
                self.setAttribute(QtCore.Qt.WA_AlwaysStackOnTop, True)

                # 删除键
                # 按钮
                self.del_btn = QtWidgets.QPushButton(self)
                self.del_btn.setObjectName('del_btn')
                self.del_btn.setStyleSheet(load_stylesheet(resource_path('qss/migrate.qss')))
                self.del_btn.setFixedSize(28, 28)
                self.del_btn.setToolTip('从列表中移除该游戏文件夹（不会删除本体文件）')
                self.del_btn.clicked.connect(self.delete_ver)
                self.layout().addWidget(self.del_btn, 1)
                # icon
                self.del_btn.setIcon(QtGui.QIcon(resource_path('assets/delete.svg')))

                # 初始化
                self.hide()
            
            def delete_ver(self):
                def delete():
                    try:
                        # 从列表中移除目标条目
                        try:
                            self.migrate_window.terminal.remove_game(self.parent_item.data)
                        except MCException.NoSuchGameFolder:
                            self.migrate_window.message.info("未找到该游戏文件夹，已跳过移除。")
                            # 更新选项卡列表
                            self.parent_item.list.update_items(self.migrate_window.terminal.get_games())
                            return

                        # 如果全删完了，就切换为欢迎界面
                        if self.migrate_window.terminal.get_games() == []:
                            self.migrate_window.terminal.switch_window(Terminal.WindowEnum.WELCOME)
                            return
                            
                        # 更新界面列表（同时更新源和目标列表）
                        try:
                            self.migrate_window.game_view_source.update_games(self.migrate_window.terminal.get_games())
                            self.migrate_window.game_view_target.update_games(self.migrate_window.terminal.get_games())
                        except Exception:
                            logging.exception("更新版本列表 UI 时出错")

                    except (OSError, IOError) as e:
                        logging.exception("文件操作失败")
                        self.migrate_window.message.error(f"文件操作失败：{e}")
                    except json.JSONDecodeError as e:
                        logging.exception("JSON 解析失败")
                        self.migrate_window.message.error(f"读取版本列表失败：{e}")
                    except Exception as e:
                        logging.exception("移除时发生未知错误")
                        self.migrate_window.message.error(f"移除游戏文件夹失败：{e}")

                    self.migrate_window.message.done("已成功移除 ！")
                self.migrate_window.dialog.warning(
                    "确定要从列表中移除该游戏文件夹吗？",
                    "在列表中移除该游戏文件夹不会对本体文件产生影响。",
                    ("确定", Dialog.Level.ERROR, delete),
                    close_when_clicked_any_btn=True
                )

            def display_ui(self):
                self.show()
                self.anim = Animation.FadeIn(self, 60)
                self.anim.start()
                self.anim.finished.connect(lambda: self.setGraphicsEffect(None)) # 加上了这一行，悬浮窗的显示问题就修复了...该说不说是好神奇吗...

            def hide_ui(self):
                self.anim = Animation.FadeOut(self, 60)
                self.anim.finished.connect(self.hide)
                self.anim.start()
                self.show()  # 确保在动画期间可见
            
class ButtonMigrateDetail(QtWidgets.QPushButton):
    '''任务详情的按钮，在被调用之前必须先set_migrate_task()'''
    def __init__(self, terminal: Terminal, parent_widget):
        super().__init__(parent=parent_widget)
        self.terminal = terminal
        self._size = 70
        self.total_pending_num: int = None
        self.setObjectName('button_migrate_detail')
        self.setFixedSize(self._size, self._size)
        layout_detail = QtWidgets.QVBoxLayout()
        self.setLayout(layout_detail)
        self.setStyleSheet(load_stylesheet(resource_path("qss/migrate.qss")))

        self.ring = Geometry.LoadingRingText(QtGui.QColor("#EDEDFF"), QtGui.QColor("#EDEDFF"))
        self.ring.change_percent(0.0)
        self.ring.setStyleSheet("background: transparent")
        layout_detail.addWidget(self.ring, 1, QtCore.Qt.AlignCenter)
        
        self.raise_()

        # 放大动画的阴影，先预设以下（我不要再新整个类了aaa
        self.shadow = QtWidgets.QWidget(parent=parent_widget)
        self.shadow.setFixedSize(self._size, self._size)
        self.shadow.setStyleSheet("background-color: '#5f9772'; border-radius: 35px")
        self.move(self.parentWidget().width() - self._size - 20, self.parentWidget().height() - self._size - 20)
    
    def set_migrate_task(self, migrate_task: TaskMigrateAbortable):
        # 点击后转至MigrateDetail界面
        self.clicked.connect(lambda: self.terminal.switch_window(Terminal.WindowEnum.MIGRATE_DETAIL, migrate_task, self.parent()))
    
    @QtCore.Slot()
    def update_percent(self):
        self.ring.change_percent(1 - self.terminal.task_migrate.pending_num / self.terminal.task_migrate.pending_num_total)
    
    def show_with_animation(self):
        self.show()
        self.raise_()

        # === 按钮弹入动画 ===
        pop_out = QtCore.QPropertyAnimation(self, b"pos")
        end_x = self.parentWidget().width() - self._size - 20
        end_y = self.parentWidget().height() - self._size - 50
        start_y = self.parentWidget().height() + 20  # 从下方开始

        pop_out.setStartValue(QtCore.QPoint(end_x, start_y))
        pop_out.setEndValue(QtCore.QPoint(end_x, end_y))
        pop_out.setEasingCurve(QtCore.QEasingCurve.OutBack)
        pop_out.setDuration(300)

        # === 阴影扩散（使用 geometry，谨慎）===
        # 确保 shadow 已正确创建
        shadow_rect = self.shadow.geometry()
        expanded_rect = shadow_rect.adjusted(-100, -100, 100, 100)  # 扩大100px

        shadow_scale = QtCore.QPropertyAnimation(self.shadow, b"geometry")
        shadow_scale.setStartValue(shadow_rect)
        shadow_scale.setEndValue(expanded_rect)
        shadow_scale.setEasingCurve(QtCore.QEasingCurve.InBounce)
        shadow_scale.setDuration(300)

        # === 阴影淡出（使用 opacity effect）===
        if not hasattr(self, 'shadow_effect'):
            self.shadow_effect = QtWidgets.QGraphicsOpacityEffect(self.shadow)
            self.shadow.setGraphicsEffect(self.shadow_effect)

        shadow_fade = QtCore.QPropertyAnimation(self.shadow_effect, b"opacity")
        shadow_fade.setStartValue(1.0)
        shadow_fade.setEndValue(1.0)
        shadow_fade.setDuration(240)
        shadow_fade.setEasingCurve(QtCore.QEasingCurve.InBounce)

        # === 启动动画组 ===
        self.anim_group = QtCore.QParallelAnimationGroup()
        self.anim_group.addAnimation(pop_out)
        self.anim_group.addAnimation(shadow_scale)
        self.anim_group.addAnimation(shadow_fade)
        self.anim_group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def show_directly(self):
        self.move(self.parentWidget().width() - self._size - 20, self.parentWidget().height() - self._size - 50)
        self.show()
        self.shadow.close()

    def close_with_animation(self):
        # === 按钮弹入动画 ===
        self.anim = QtCore.QPropertyAnimation(self, b"pos")
        end_x = self.parentWidget().width() - self._size - 20
        end_y = self.parentWidget().height() + 20
        start_y = self.parentWidget().height() - self._size - 50

        self.anim.setStartValue(QtCore.QPoint(end_x, start_y))
        self.anim.setEndValue(QtCore.QPoint(end_x, end_y))
        self.anim.setEasingCurve(QtCore.QEasingCurve.OutBack)
        self.anim.setDuration(300)
        
        def close_and_delete():
            self.close()
            self.deleteLater()
        self.anim.finished.connect(close_and_delete)
        self.anim.start()