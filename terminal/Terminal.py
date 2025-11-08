from enum import Enum
from typing import List, Callable
from pathlib import Path
from PySide6 import QtWidgets, QtCore
import os, shutil, json, logging

from terminal.func import version, mod, config, utils
from message import Message, Dialog
import MCException

logging.basicConfig(level=logging.INFO)

class Terminal(Message.Messageable, Dialog.Dialogable):
    def __init__(self, main_window: QtWidgets.QMainWindow):
        super().__init__(__name__)
        self.config = config.get_config()
        self.main_window = main_window
        self.thread_migrate = QtCore.QThread()
        self.task_migrate = None
        self.versions_json: list[dict]
        self.refresh_version()
    
    def import_version(self) -> list[dict] | None:
        '''
        为前端预制封装的导入方法，可根据返回的versions是否为None来判断导入成功
        '''
        version_path = Path(QtWidgets.QFileDialog.getExistingDirectory(
            parent=None,
            caption="选择.minecraft文件夹",
            dir="",
            options=QtWidgets.QFileDialog.ShowDirsOnly
        ))
        if version_path == Path("."): return None # 传空值就忽略，什么消息也不发
        # 开始解析版本路径
        try:
            self.add_version(version_path)
        except MCException.NotMCGameFolder as e:
            self.send_message(f"{e}", Message.Level.ERROR)
            return None
        except MCException.VersionsFolderNotFound as e:
            self.send_message(f"{e}", Message.Level.WARNING)
            return None
        except Exception as e:
            self.send_message(f"导入版本失败：{e}", Message.Level.ERROR)
            return None

        # 版本路径解析完毕了，接下来就是加载前端版本列表
        try:
            if versions:= version.get_versions():
                self.versions_json = versions
                return versions
            raise IOError("version.json内容为空")
        except (IOError, OSError) as e:
            self.send_message(f"读取versions.json失败：{e}", Message.Level.ERROR)
            return None
        except TypeError:
            self.send_message(str(e))
            return None
        except Exception as e:
            self.send_message(f"发生了意外的错误：{e}", Message.Level.ERROR)
            return None

    def refresh_version(self):
        self.versions_json = version.get_versions()

    def switch_window(self, window_enum: 'WindowEnum', *params):
        '''
        用于切换窗口
        \n但因为qt本身会立马删除没有使用或是show()的窗口，所以很大情况不能通过直接传入widget来实现窗口切换
        \n因此只能根据传入的自己搓的窗口枚举类WindowEnum及其对应的形参来现场生成一个窗口并setCentralWidget()
        \n为什么要用枚举类？防止其他窗口调用该方法时产生循环导入（circular import）
        '''
        self.main_window.setCentralWidget(window_enum.clazz(self, *params))
    
    def switch_window_with_msg(self, window_enum: 'WindowEnum', msg_bar: tuple[str, Message.Level], *params):
        # 切换窗口界面
        self.switch_window(window_enum, *params)

        # 发送预留消息
        if msg_bar and hasattr(self.main_window.centralWidget(), 'message'):
            self.send_message(*msg_bar)
    
    def switch_window_with_dialog(self, window_enum: 'WindowEnum', dialog: tuple[str, Dialog.Level, str, None, tuple[str, Dialog.Level, Callable[[], None]]], *params):
        # 切换窗口界面
        self.switch_window(window_enum, *params)
        
        # 发送预留消息
        if dialog and hasattr(self.main_window.centralWidget(), 'dialog'):
            self.send_message(*dialog)

    def migrate(self, source_json: dict, target_json: dict):
        if self.thread_migrate.isRunning(): return
        source_dir = Path(source_json['game_path'])
        target_dir = Path(target_json['game_path'])
        # 路径检查
        if source_dir == None or target_dir == None:
            logging.info("请先选择迁移版本和目标版本")
            raise MCException.VersionVerifyFailed("请先选择迁移版本和目标版本", Message.Level.INFO)
             
        elif source_dir == target_dir:
            raise MCException.VersionVerifyFailed('不能迁移自己口牙>_<', Message.Level.WARNING)

        # 条件符合，开始迁移！
        # 创建新线程
        def finish():
            self.thread_migrate.quit()
            self.task_migrate.deleteLater()
            self.task_migrate = None
            self.message_requested.emit(f"{source_json.get('name')}已迁移至{target_json.get('name')}！", Message.Level.DONE)
        self.task_migrate = Terminal.TaskMigrate(self, source_dir, target_dir, source_json, target_json)
        self.task_migrate.finished.connect(finish)
        self.task_migrate.moveToThread(self.thread_migrate)
        self.thread_migrate.started.connect(self.task_migrate.do_work)
        self.thread_migrate.start()

            
    def add_version(self, path: Path) -> list[dict] | None:
        return version.add_version(path)
        
    def update_versions_json(self, versions: list[dict]):
        version.update_versions_json(versions)

    def parse_path(self, path: Path) -> list[dict]:
        return version.parse_path(path)
    
    def is_indie_pcl(self, pcl_folder) -> bool:
        return version.is_indie_pcl(pcl_folder)
        
    def is_indie_hmcl(self, hmcl_cfg_file) -> bool:
        return version.is_indie_hmcl(hmcl_cfg_file)

    def parse_version(self, path: Path, is_indie=True) -> dict | None:
        return version.parse_version(path, is_indie)

    def get_versions(self) -> list[dict]:
        return self.versions_json
    

    class WindowEnum(Enum):
        '''
        作为一个中介，来让各个窗口可以调用其他窗口（其实主要是防止循环导入）
        '''
        WELCOME = "windows.Welcome.Welcome"
        MIGRATE = "windows.Migrate.Migrate"
        MIGRATE_DETAIL = "windows.MigrateDetail.MigrateDetail"

        @property
        def clazz(self):
            # 延迟导入：只有访问 .clazz 时才导入
            import importlib
            module_path, class_name = self.value.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        
    class TaskMigrate(QtCore.QObject):
        finished = QtCore.Signal()
        update_migrate_general = QtCore.Signal(int)
        update_migrate_detail = QtCore.Signal(int, int)
        def __init__(self, terminal: 'Terminal', source_dir: Path, target_dir: Path, source_json: dict, target_json: dict):
            super().__init__()
            self.terminal = terminal
            self.source_dir = source_dir
            self.target_dir = target_dir
            self.source_json = source_json
            self.target_json = target_json

            # 状态
            self.is_calculating = True

            # 任务总数
            self.pending_num = 0
            self.pending_num_total = 0

            self.pending_num_mod = -1
            self.pending_num_mod_total = -1
            
            self.pending_num_file = -1
            self.pending_num_file_total = -1

            # 错误实例
            self.failed_files_copy = []
            self.failed_mods_dl = []
            self.failed_mods_not_adapt = []

            # 迁移时会跳过的文件
            self.exclude_files = [
                source_json['name']+".json",
                source_json['name']+".jar",
                "launcher_profiles.json",
                "PCL.ini",
                "mods"
            ]
            if config.get_config_value('migrate', 'filter_rule') == 'excludes':
                self.exclude_files.extend(config.get_config_value('migrate', 'excludes'))
            
        @QtCore.Slot()
        def do_work(self):
            # 计算待处理任务数量（复制文件）
            self.pending_num_file = len([dir for dir in os.listdir(self.source_dir) if dir not in self.exclude_files])
            self.pending_num += self.pending_num_file
            self.pending_num_total = self.pending_num
            self.pending_num_file_total = self.pending_num_file

            # 计算待处理任务数量（mod下载）
            not_mod_loader = ['optifine', 'release', 'snapshot', 'unknown']
            mod_list: List[str] = None
            if (self.source_json['mod_loader'] not in not_mod_loader) and (self.target_json['mod_loader'] not in not_mod_loader):
                mod_list = os.listdir(self.source_dir / "mods")
                self.pending_num_mod = len(mod_list)
                self.pending_num += self.pending_num_mod
                self.pending_num_total = self.pending_num
                self.pending_num_mod_total = self.pending_num_mod

            # 算完任务数量了，接下来就来干正事吧（
            self.is_calculating = False
            
            # 开始下载mod
            if mod_list:
                logging.info("下载mod中")
                if not config.get_config_value('migrate', 'keep-original-mods'):
                    utils.clear_folder(self.target_dir / 'mods')
                self.download_mods(self.source_dir / "mods", self.target_dir / "mods", self.target_json["version"], self.target_json["mod_loader"], mod_list)
                logging.info("mod下载完成")
            
            # 开始迁移文件
            logging.info("迁移游戏文件")
            self.migrate_file(self.source_dir, self.target_dir)
            logging.info("游戏文件迁移完成")
            self.report_exception()
            self.finished.emit()

        def migrate_file(self, source_dir: Path, target_dir: Path):
            for item in Path(source_dir).iterdir():
                if item.name.startswith('.') or item.name.startswith('$'): continue # 跳过隐藏文件
                if item.name not in self.exclude_files: # 根据config.yml中的过滤规则来筛去文件
                    logging.info(f"复制{item}至{target_dir / item.name}")
                    try:
                        if item.is_dir(): # 文件夹（覆盖）
                            shutil.copytree(item, target_dir / item.name, dirs_exist_ok=True)
                        else: # 文件
                            shutil.copy(item, target_dir / item.name)
                    except PermissionError as e:
                        logging.warning("权限不足")
                        self.failed_files_copy.append([item.name, "权限不足"])
                    except Exception as e:
                        logging.error("未知错误：" + str(e))
                        self.failed_files_copy.append([item.name, e])
                self.reduce_pending_num_file()
                
        def download_mods(self, source_dir: str, target_dir: str, target_ver: str, mod_loader: str, file_name_list: List[str]):
            # 缓存，记录没有下载完成的mod
            if not os.path.exists(f"{target_dir}dl.txt"):
                with open(f"{target_dir}dl.txt", 'w') as f:
                    logging.info("已创建缓存文件dl.txt")
            with open(f"{target_dir}dl.txt", 'r') as f:
                logging.info("读取缓存文件dl.txt")
                file_name_list_done: List[str] = [line.strip() for line in f.readlines()]
            self.failed_mods_not_adapt: List[str] = []

            for old_file_name in file_name_list:
                logging.info(f"\n{old_file_name}")
                
                # 检测是否已下载，有则跳过
                if old_file_name in file_name_list_done:
                    logging.info(f"{old_file_name} 已下载")
                    self.reduce_pending_num_mod()
                    continue

                elif not mod.modrinth(target_ver, mod_loader, source_dir, old_file_name, target_dir, self.failed_mods_not_adapt):
                        list.append(self.failed_mods_not_adapt, old_file_name)

                self.reduce_pending_num_mod()

            # 结果统计
            if len(self.failed_mods_not_adapt) != 0:
                logging.info("\n以下模组暂未找到适配：")
                for not_adapt_mod in self.failed_mods_not_adapt: logging.info(not_adapt_mod)
            else: 
                logging.info("\n无不适配情况，全部模组已完成版本迁移！")
                os.remove(f"{target_dir}dl.txt")
        
        def report_exception(self):
            if self.failed_files_copy != [] or self.failed_mods_dl != [] or self.failed_mods_not_adapt != []:
                report_content = ""
                level = Dialog.Level.WARNING
                title = "还有些需要留意..."

                # 模组未适配
                if self.failed_mods_not_adapt != []:
                    report_content += f"以下模组在 {self.target_json.get('version')} 版本中没有适配：\n"
                    for file in self.failed_mods_not_adapt:
                        report_content += file + '\n'

                # 模组下载失败
                if self.failed_mods_dl != []:
                    report_content += f"以下模组下载失败：\n"
                    for file in self.failed_mods_dl:
                        report_content += file + '\n'

                # 文件迁移失败（这个部分问题就比较多了，就由说明具体错误
                if self.failed_files_copy != []:
                    title = "遇到问题了..."
                    level = Dialog.Level.ERROR
                    report_content += f"以下文件在迁移时出错：\n"
                    for file in self.failed_files_copy:
                        report_content += f"{file[0]}：{file[1]}\n"
                self.terminal.send_dialog(
                    title,
                    level,
                    report_content,
                    None,
                    change_cancel_btn_text='好的'
                )

        def reduce_pending_num(self):
            self.pending_num -= 1
            self.update_migrate_general.emit(self.pending_num)
            self.update_migrate_detail.emit(self.pending_num_mod, self.pending_num_file)

        def reduce_pending_num_mod(self):
            self.pending_num_mod -= 1
            self.reduce_pending_num()

        def reduce_pending_num_file(self):
            self.pending_num_file -= 1
            self.reduce_pending_num()