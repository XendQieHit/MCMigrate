import logging, json
from PySide6 import QtWidgets, QtGui, QtCore
from terminal.Terminal import Terminal
from pathlib import Path

from windows.SendMessageable import SendMessageable
from message import Message, Dialog
from windows.loadStyleSheet import load_stylesheet
from utils.func import resource_path
from utils.ClientLibs import ColorIconGenerator
import Geometry, MCException, Animation

class Migrate(SendMessageable):
    def __init__(self, terminal: Terminal, version_paths: list[dict], migrate_task: Terminal.TaskMigrateAbortable=None):
        super().__init__(terminal.main_window)
        self.versions = version_paths
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
        self.top_bar.layout().setContentsMargins(0,0,0,0)
        # 清空所有版本按钮
        self.clear_all_vers_btn = Migrate.TopBarButton(QtGui.QColor("#f05f5a"), QtGui.QColor("#e14d48"), resource_path("assets/delete.svg"), '清除列表里所有的版本', self) # 是的你的ide没有出错，QColor应用在QGraphicsColorizeEffect时，alpha通道值要放前面
        self.clear_all_vers_btn.clicked.connect(lambda: self.dialog.error(
            "确定清除所有版本？",
            "该操作将会清除列表里的所有版本！\n该操作不会对游戏文件本体产生影响。\n\n确定要清除所有版本吗？",
            (
                "确定",
                Dialog.Level.ERROR,
                self.btn_clear_all_vers_clicked
            ),
            close_when_clicked_any_btn=True
        ))
        self.top_bar.layout().addWidget(self.clear_all_vers_btn, 0)
        # github链接
        self.github_url = Migrate.TopBarButton(QtGui.QColor("#202020"), QtGui.QColor("#101010"), resource_path('assets/icon/github.svg'), '前往MCMigrate的Github仓库', self)
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
        self.resize(800, 400)

        # 如果已经有迁移任务在进行，把任务详情的悬浮窗添加进来
        if self.migrate_task:
            self.button_migrate_detail = ButtonMigrateDetail(self.terminal, self)
            self.button_migrate_detail.set_migrate_task(self.migrate_task)
            self.migrate_task.update_migrate_general.connect(self.button_migrate_detail.update_percent)
            self.button_migrate_detail.show_directly()
            self.terminal.thread_migrate.finished.connect(self.button_migrate_detail.close_with_animation)
            if not self.migrate_task.is_calculating:
                self.button_migrate_detail.update_percent()

    def button_import_clicked(self):
        if versions:= self.terminal.import_version():
            self.versions = versions
            self.ver_list_source.update_versions(versions)
            self.ver_list_target.update_versions(versions)
            self.window().update()
            self.message.done("版本导入成功！")

    def button_migrate_clicked(self):
        # 条件检测
        if self.terminal.thread_migrate.isRunning():
            self.message.info("请先等待迁移完成")
            return
        ver_source: Migrate.VersionItem = self.ver_list_source.itemWidget(self.ver_list_source.currentItem())
        ver_target: Migrate.VersionItem = self.ver_list_target.itemWidget(self.ver_list_target.currentItem())
        if ver_source == None or ver_target == None:
            logging.info("请先选择迁移版本和目标版本")
            self.message.info("请先选择迁移版本和目标版本")
            return

        # 添加任务详情悬浮按钮
        self.button_migrate_detail = ButtonMigrateDetail(self.terminal, self)
        self.terminal.thread_migrate.finished.connect(self.button_migrate_detail.close_with_animation)
        self.message.info(f"正在迁移 {ver_source.json.get('name')} 至 {ver_target.json.get('name')}")
        
        # 开始线程任务
        try:
            self.terminal.migrate(source_json=ver_source.json, target_json=ver_target.json)
        except MCException.VersionVerifyFailed as e:
            self.message.show_message(str(e), e.level)
            self.button_migrate_detail.close()
            return
        self.button_migrate_detail.set_migrate_task(self.terminal.task_migrate)
        self.terminal.task_migrate.update_migrate_general.connect(self.button_migrate_detail.update_percent)
        self.button_migrate_detail.show_with_animation()

    def btn_clear_all_vers_clicked(self):
        self.terminal.clear_all_vers()
        self.message.done("已清除所有版本!")
        self.terminal.switch_window(Terminal.WindowEnum.WELCOME)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'button_migrate_detail'):
            self.button_migrate_detail.move(self.width() - 100, self.height() - 135)
    
    class TopBarButton(QtWidgets.QPushButton):
        def __init__(self, theme_color: QtGui.QColor, clicked_color: QtGui.QColor, icon_path: str | Path, tool_tips: str, parent=None):
            super().__init__(parent)
            self.theme_color = theme_color
            self.clicked_color = clicked_color
            self.default_color = self.palette().color(QtGui.QPalette.ColorRole.Button)
            self.icon_size = min(self.height(), self.width())
            self.icon_gen = ColorIconGenerator(icon_path, theme_color)
            self.setToolTip(tool_tips)
            self.setIcon(self.icon_gen.icon(QtCore.QSize(self.icon_size, self.icon_size), self.theme_color))
            self.setContentsMargins(0,0,0,0)
            self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

        def enterEvent(self, event):
            super().enterEvent(event)
            self.anim_btn = Animation.ChangeColorTransiting(self, QtGui.QColor(self.theme_color), duration=120)
            self.anim_icon = Animation.ChangeButtonIconColorTransiting(self, self.icon_gen, QtGui.QColor(self.default_color), duration=120)
            self.anim = QtCore.QParallelAnimationGroup()
            self.anim.addAnimation(self.anim_btn)
            self.anim.addAnimation(self.anim_icon)
            self.anim.start()

        def leaveEvent(self, event):
            super().leaveEvent(event)
            self.anim_btn = Animation.ChangeColorTransiting(self, QtGui.QColor(self.default_color), duration=120)
            self.anim_icon = Animation.ChangeButtonIconColorTransiting(self, self.icon_gen, QtGui.QColor(self.theme_color), duration=120)
            self.anim = QtCore.QParallelAnimationGroup()
            self.anim.addAnimation(self.anim_btn)
            self.anim.addAnimation(self.anim_icon)
            self.anim.start()

        def mousePressEvent(self, e):
            super().mousePressEvent(e)
            palette = self.palette()
            palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(self.clicked_color))
            self.setPalette(palette)

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

            # 版本号标签和版本文件路径的容器
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
            self.float_bar = Migrate.VersionItem.FloatBar(self, self.list.parent())

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
            def __init__(self, parent_widget: 'Migrate.VersionItem', main_window: 'Migrate'):
                super().__init__(parent_widget)
                self.parent_item = parent_widget
                self.main_window = main_window
                # 总样式设置
                self.setLayout(QtWidgets.QVBoxLayout())
                self.setContentsMargins(0,0,0,0)
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
                    self.main_window.message.error('无法打开文件夹，可能版本文件夹本体已被删除！')
            
            def delete_ver(self):
                def delete(dialog: Dialog.DialogWindow):
                    try:
                        # 从列表中移除目标条目
                        try:
                            self.main_window.versions.remove(self.parent_item.json)
                        except ValueError:
                            self.main_window.message.info("未在列表中找到该版本，已跳过移除。")
                            dialog.close_with_animation()
                            return

                        # 写回文件
                        with Path('versions.json').open('w', encoding='utf-8') as f:
                            json.dump(self.main_window.versions, f, ensure_ascii=False, indent=2)

                        # 如果全删完了，就切换为欢迎界面
                        if self.main_window.versions == []:
                            self.main_window.terminal.switch_window(Terminal.WindowEnum.WELCOME)
                            dialog.close_with_animation()
                            
                        # 更新界面列表（同时更新源和目标列表）
                        try:
                            self.main_window.ver_list_source.update_versions(self.main_window.versions)
                            self.main_window.ver_list_target.update_versions(self.main_window.versions)
                        except Exception:
                            logging.exception("更新版本列表 UI 时出错")

                    except (OSError, IOError) as e:
                        logging.exception("文件操作失败")
                        self.main_window.message.error(f"文件操作失败：{e}")
                    except json.JSONDecodeError as e:
                        logging.exception("JSON 解析失败")
                        self.main_window.message.error(f"读取版本列表失败：{e}")
                    except Exception as e:
                        logging.exception("移除版本时发生未知错误")
                        self.main_window.message.error(f"移除版本失败：{e}")

                    self.main_window.message.done("已成功移除 ！")
                    dialog.close_with_animation()
                dialog: Dialog.DialogWindow = self.main_window.dialog.warning(
                    "确定要从列表中移除该版本吗？",
                    "在列表中移除该版本不会对游戏文件产生影响。",
                    ("确定", Dialog.Level.ERROR, lambda: delete(dialog))
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


    class VersionList(QtWidgets.QListWidget):
        def __init__(self, version_list: list[dict], parent_widget=None):
            super().__init__(parent=parent_widget)
            # 样式设置
            for version in version_list:
                self.add_version(Migrate.VersionItem(version, self))
            self.setStyleSheet(resource_path(load_stylesheet(resource_path("qss/migrate.qss"))))
            self.setSpacing(5)

            # 通过监听滑条移动来动态调整实现VersionItem的FloatBar工具栏与列表相对静止
            self.hover_item: Migrate.VersionItem = None
            self.h_scroll_value = 0
            self.scroll_max = self.horizontalScrollBar().maximum()
            self.scroll_pagestep = self.horizontalScrollBar().pageStep()
            
            self.horizontalScrollBar().valueChanged.connect(self.on_scroll)
        
        # 保持水平移动列表时，悬浮工具栏仍可以相对固定列表靠右处
        def on_scroll(self, value: int):
            self.h_scroll_value = value
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
                self.add_version(Migrate.VersionItem(ver, self))
            logging.info("已更新版本列表")
            
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
    
    def set_migrate_task(self, migrate_task: Terminal.TaskMigrateAbortable):
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