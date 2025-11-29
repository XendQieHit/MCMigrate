from enum import Enum
from typing import List, Callable
from pathlib import Path
from PySide6 import QtWidgets, QtCore
import os, shutil, json, logging

from utils import func
from terminal.func import version, mod, config
from message import Message, Dialog, DisplayMessageable
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
        self.refresh_terminal_version()
    
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
            return self.check_import_versions(self.add_version(version_path))
        except MCException.NotMCGameFolder as e:
            self.send_message(f"{e}", Message.Level.ERROR)
            return None
        except MCException.VersionsFolderNotFound as e:
            self.send_message(f"{e}", Message.Level.WARNING)
            return None

    def import_versions_from_pcl(self):
        return self.check_import_versions(version.get_versions_from_pcl())
        
    def check_import_versions(self, versions: tuple[dict] | list[list[dict], list[dict], list[dict]]):
        def _finish_import_versions() -> list[dict]: 
            try:
                if versions:= version.get_versions():
                    self.versions_json = versions
                    return versions
                raise IOError("version.json内容为空")
            except (IOError, OSError) as e:
                self.send_message(f"读取versions.json失败：{e}", Message.Level.ERROR)
                return None
            except json.JSONDecodeError:
                self.send_message("解析versions.json时失败", Message.Level.ERROR)
                return None
            except Exception as e:
                self.send_message(f"发生了意外的错误：{e}", Message.Level.ERROR)
                return None

        if isinstance(versions, list):
            if versions[1] != []: # 出现无法判断版本隔离的情况，让用户判断
                series = self.get_query_dialog_series(versions)

                # 问答结束后对结果的处理
                @QtCore.Slot(object)
                def _end_asked(versions: list[list[dict], list, list[str]]):
                    # 先弹出导入成功的数量信息
                    self.send_message(f'成功导入{len(versions[0])}个版本', Dialog.Level.DONE)

                    if versions[2] != []: # 出现无法正常导入的版本，弹窗提示
                        self.send_dialog('有些版本无法导入...', Dialog.Level.ERROR, f'以下版本无法正常导入：\n{'\n'.join(versions[2])}')
                    # 将解析完成的数据添加进本地的versions.json
                    self.update_versions_json(versions[0])
                    # 版本路径解析完毕了，接下来就是加载前端版本列表
                    self.switch_window(Terminal.WindowEnum.MIGRATE, _finish_import_versions())
                # 开始问答！
                self.ask_in_series(series, _end_asked)

            else: # 没有疑问但有无法导入的版本
                self.send_dialog('有些版本无法导入...', Dialog.Level.ERROR, f'以下版本无法正常导入：\n{'\n'.join(versions[2])}')
                self.update_versions_json(versions[0])
                return _finish_import_versions()
            
        else: # 哇哦！居然全解析成功了！直接用这个数据同步到本地并更新前端
            self.update_versions_json(versions)
            return _finish_import_versions()

    def get_query_dialog_series(self, versions: list[list[dict], list[dict], list[dict]]):
        '''
        生成一个用于询问版本隔离的问答框系列
        Args:
            versions(list[list[dict], list[dict], list[dict]]): 可操作的版本集合，versions[0]为成功解析的版本列表，versions[1]为待询问的版本列表，其中，versions中的偶数项为版本隔离情况下的版本信息dict，奇数项为非版本隔离情况下的版本信息dict。
        '''
        suc_vers_len = len(versions[0])
        def add_suc_versions():
            nonlocal suc_vers_len
            suc_vers_len+=1
            return suc_vers_len
        series = self.gen_a_series('ask_for_indie', versions)

        # 递归生成确认问答框
        def add_next_dialogs(i: int, node: Dialog.DialogSeries.DialogTreeNode):
            if len(versions[1]) > i+2:
                action = Dialog.DialogSeries.Action('NEXT', 0)
            else: action = Dialog.DialogSeries.Action('END', None)
            node.create_dialog_series_window(
                        '出现无法确定版本隔离的情况',
                        Dialog.Level.WARNING,
                        f"版本名称：{versions[1][i]['name']}\n版本号：{versions[1][i]['version']}\n版本路径：{versions[1][i]['game_path']}\n模组加载器：{versions[1][i]['mod_loader']}\n\n该版本是否启用版本隔离？",
                    ).add_button(
                        '是', Dialog.Level.DONE, action, Dialog.DialogSeries.Func(versions[1][i], (0, add_suc_versions()))
                    ).add_button(
                        '否', Dialog.Level.ERROR, action, Dialog.DialogSeries.Func(versions[1][i+1], (0, add_suc_versions()))
                    ).add_button(
                        '不知道啊', Dialog.Level.INFO, action, Dialog.DialogSeries.Func(versions[1][i], (0, add_suc_versions())), Dialog.DialogSeries.Func(versions[1][i+1], (0, add_suc_versions())), hover_text="将会各添加一个隔离和非隔离的版本"
                    ).add_button(
                        '跳过该版本', Dialog.Level.INFO, action
                    )

            i+=2
            if len(versions[1]) > i:
                add_next_dialogs(i, node.add_new_dialog_node())

        add_next_dialogs(0, series.create_dialog_tree())
        return series

    def refresh_terminal_version(self):
        try:
            self.versions_json = version.get_versions()
        except json.JSONDecodeError:
            version.gen_new_versions()
            self.send_message("解析versions.json时失败, 已重新生成versions.json", Message.Level.ERROR)

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
        self.task_migrate = TaskMigrateAbortable(self, source_dir, target_dir, source_json, target_json)
        self.task_migrate.finished.connect(finish)
        self.task_migrate.moveToThread(self.thread_migrate)
        self.thread_migrate.started.connect(self.task_migrate.do_work)
        self.thread_migrate.start()
    
    def terminate_migrate_task(self):
        if self.task_migrate:
            self.task_migrate.abort()
        def cleanup():
            logging.info('已终止迁移任务')
            self.thread_migrate.quit()
            self.task_migrate.deleteLater()
            self.task_migrate = None
        self.task_migrate.terminated.connect(cleanup)
            
    def add_version(self, path: Path) -> list[dict] | None:
        return version.add_version(path)
        
    def update_versions_json(self, versions: list[dict]):
        version.update_versions_json(versions)

    def get_versions(self) -> list[dict]:
        return self.versions_json
    
    def clear_all_vers(self):
        version.clear_all_vers(self)
        self.versions_json = []

    def refresh_all_versions_info(self) -> list[dict]:
        '''
        同步启动器更改，更新所有版本的信息
        Returns:
            list[dict]: 刷新后的所有版本信息
        '''
        vers = version.get_versions()
        done_versions = []
        query_versions = []
        failed_versions = []
        changed_vers_count = 0
        for ver in vers:
            ver_result = version.refresh_version_info(ver)
            if ver_result == ver: continue
            changed_vers_count += 1 # 得到的版本与原版本有变化！
            if isinstance(ver_result, list): # 解析成功
                done_versions.extend(ver_result)
            elif isinstance(ver_result, tuple): # 无法判断版本隔离的情况
                query_versions.extend(ver_result)
            else: # 布兑！有问题！
                failed_versions.append(ver['name'])

        # 可能因为有不同启动器的配置文件而再多生成一份的情况，去重
        def to_hashable(d: dict):
            return frozenset(d.items())
        done_vers_set = set()
        filtered_done_versions = []
        for ver in done_versions:
            if to_hashable(ver) in done_vers_set: continue # 跳过重复
            done_vers_set.add(to_hashable(ver))
            filtered_done_versions.append(ver)
        done_versions = filtered_done_versions

        combined_vers = [done_versions, query_versions, failed_versions]
        return self._check_refresh_versions(vers, combined_vers)
    
    def _check_refresh_versions(self, old_versions: list[dict], versions: list[list[dict], list[dict], list[dict]]):
        def _finish_refresh():
            # 覆写versions.json
            with open('versions.json', 'w', encoding='utf-8') as f:
                json.dump(versions[0], f, ensure_ascii=False, indent=2)
                self.send_message(f'已刷新{len(versions[0])}个版本！', Message.Level.DONE)
                    
            if versions[2] != []: # 出现版本解析失败的情况，告知玩家
                self.send_dialog('有些版本刷新失败...', Dialog.Level.ERROR, f'以下版本刷新时出现问题：\n{'\n'.join(versions[2])}')
            
            return versions[0]

        if versions[1] != []: # 出现可能需要询问版本隔离的情况
            # 首先要检测询问版本的内容是否已经存在于old_versions
            query_vers = []
            for i in range(0, len(versions[1]), 2):
                if versions[1][i] in old_versions:
                    versions[0].append(versions[1][i])
                elif versions[1][i+1] in old_versions:
                    versions[0].append(versions[1][i+1])
                else: # 与原版本信息出现不同，需要询问
                    query_vers.append(versions[1][i])
                    query_vers.append(versions[1][i+1])
            
            if query_vers != []:
                versions_for_query = [versions[0], query_vers]
                @QtCore.Slot(object)
                def _end_asked(query_results: list[list[dict], list[dict], list[dict]]):
                    # 将问答结果添加到versions上
                    versions[0] = query_results[0]
                    # 手动更新界面
                    self.switch_window(Terminal.WindowEnum.MIGRATE, _finish_refresh())
                
                self.ask_in_series(self.get_query_dialog_series(versions_for_query), _end_asked) # 开始向用户询问版本隔离情况
            else: return _finish_refresh()

        else: # 好耶！不需要询问版本隔离，直接结算！
            return _finish_refresh()

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
        
class TaskMigrateAbortable(QtCore.QObject):
    finished = QtCore.Signal()
    terminated = QtCore.Signal()
    update_migrate_general = QtCore.Signal(int)
    update_migrate_detail = QtCore.Signal(int, int)
    def __init__(self, terminal: 'Terminal', source_dir: Path, target_dir: Path, source_json: dict, target_json: dict):
        '''
        Args:
        source_json(dict): 原版本在versions.json里的dict表现
        target_json(dict): 目标版本在versions.json里的dict表现
        '''
        super().__init__()
        self.terminal = terminal
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.source_json = source_json
        self.target_json = target_json

        # 状态
        self.is_calculating = True
        self._abort = False

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

    def abort(self):
        '''终止任务'''
        self._abort = True
        
    @QtCore.Slot()
    def do_work(self):
        # 计算待处理任务数量（复制文件）
        if self._abort:
            logging.info('任务被终止（计算任务数阶段）')
            self.terminated.emit()
            return
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
        if self._abort:
            logging.info('任务被终止（计算任务数阶段）')
            self.terminated.emit()
            return
        # 算完任务数量了，接下来就来干正事吧（
        self.is_calculating = False
        
        # 开始下载mod
        if mod_list:
            logging.info("下载mod中")
            if not config.get_config_value('migrate', 'keep-original-mods'):
                func.clear_folder(self.target_dir / 'mods')
            self.download_mods(self.source_dir / "mods", self.target_dir / "mods", self.target_json["version"], self.target_json["mod_loader"], mod_list)
            if self._abort:
                logging.info('任务被终止（模组下载阶段）')
                self.terminated.emit()
                return
            logging.info("mod下载完成") 
            
        # 开始迁移文件
        logging.info("迁移游戏文件")
        self.migrate_file(self.source_dir, self.target_dir)
        if self._abort:
            logging.info('任务被终止（文件迁移阶段）')
            self.terminated.emit()
            return
        logging.info("游戏文件迁移完成")
        self.report_exception()
        self.finished.emit()

    def migrate_file(self, source_dir: Path, target_dir: Path):
        for item in Path(source_dir).iterdir():
            if self._abort:
                return
            if item.name.startswith('.') or item.name.startswith('$'): continue # 跳过隐藏文件
            if item.name not in self.exclude_files: # 根据config.yml中的过滤规则来筛去文件
                logging.info(f"复制{item}至{target_dir / item.name}")
                try:
                    if item.is_dir(): # 文件夹（覆盖）
                        self.copy_tree_with_abort(item, target_dir / item.name, exist_ok=True)
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
            if self._abort:
                return
            logging.info(f"\n{old_file_name}")
            
            # 检测是否已下载，有则跳过
            if old_file_name in file_name_list_done:
                logging.info(f"{old_file_name} 已下载")
                self.reduce_pending_num_mod()
                continue
            
            modrinth_result = mod.modrinth(target_ver, mod_loader, source_dir, old_file_name, target_dir)
            # 尝试查找并下载
            if not modrinth_result == mod.Result.SUCCESS: # 有下载失败的，具体分析
                if isinstance(modrinth_result, list): # 依赖下载失败的
                    self.failed_mods_dl.append(f"{old_file_name}的依赖：\n{"\n".join(modrinth_result)}")

                elif modrinth_result == mod.Result.NOT_ADAPTED: self.failed_mods_not_adapt.append(old_file_name) # 模组本体未适配版本的
                else: self.failed_mods_dl.append(old_file_name)
            
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
                report_content += f"以下模组在 {self.target_json.get('mod_loader')}-{self.target_json.get('version')} 版本中没有适配：\n"
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

    def copy_tree_with_abort(self, src: Path, dst: Path, exist_ok=True):
        """递归复制目录，支持中途终止"""
        if self._abort:
            return

        dst.mkdir(parents=True, exist_ok=exist_ok)
        
        for item in src.iterdir():
            if self._abort:
                return
            if item.is_dir():
                self.copy_tree_with_abort(item, dst / item.name)
            else:
                try:
                    shutil.copy2(item, dst / item.name)
                except Exception as e:
                    self.failed_files_copy.append([str(item), str(e)])