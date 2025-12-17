from enum import Enum
from typing import Callable, Union
from pathlib import Path
from PySide6 import QtWidgets, QtCore
from windows.MainWindow import MainWindow
import os, shutil, json, logging

from utils import func
from terminal.func import version, mod, config
from message import Message, Dialog, DisplayMessageable
import MCException

logging.basicConfig(level=logging.INFO)

class Terminal(Message.Messageable, Dialog.Dialogable):
    def __init__(self, main_window: MainWindow):
        super().__init__(__name__)
        self.config = config.get_config()
        self.main_window = main_window
        self.thread_migrate = QtCore.QThread()
        self.task_migrate = None

        # versions.json索引部分
        try:
            self.versions_manager = VersionsJsonManager(self)
        except KeyError:
            games_json = version.get_versions()
            if not isinstance(games_json[0].get('versions', None), dict) and isinstance(games_json[0].get('game_jar', None), str): # 升级旧版本versions.json
                version.update_versions_json()
            else: # versions.json格式又炸了, 重置
                version.gen_new_versions()
                self.send_message('加载versions.json文件时出错，已重置文件')
            self.versions_manager = VersionsJsonManager(self)
    # == 前端封装方法 ==

    def import_version(self) -> list[dict] | None:
        '''
        为前端预制封装的导入方法
        Returns:
            list[dict]|None: 将导入结果应用之后的versions.json内容。若为None，则说明解析失败。
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
            versions = self.check_and_apply_import_result(version.add_game(version_path))
            self.versions_manager.refresh()
            return versions
        except MCException.NotMCGameFolder as e:
            self.send_message(f"{e}", Message.Level.ERROR)
            return None
        except MCException.VersionsFolderNotFound as e:
            self.send_message(f"{e}", Message.Level.WARNING)
            return None

    def import_versions_from_pcl(self):
        versions = self.check_and_apply_import_result(version.get_versions_from_pcl())
        self.versions_manager.refresh()
        return versions
        
    def check_and_apply_import_result(self, result: version.PathParseResult | list[version.PathParseResult]) -> list[dict] | None:
        '''
        检查并将导入结果写入versions.json中
        Returns:
            list[dict]|None: 完成写入之后的versions.json中内容。若为None，则说明正在向用户询问版本隔离的信息。
        '''
        def _finish_import_versions() -> list[dict]: # 将结果写入导入
            try:
                if versions:= version.get_versions():
                    self.versions_manager.games_json = versions
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

        if isinstance(result, version.PathParseResult) and result.is_suc: # 只有一个PathParseResult的情况，且全解析成功了！直接用这个数据同步到本地并更新前端
            version.update_versions_json(result.to_dict())
            return _finish_import_versions()
        
        else:
            def send_failed_games_content():
                if isinstance(result, version.PathParseResult):
                    self.send_dialog('有些版本无法导入...', Dialog.Level.ERROR, '以下版本无法正常导入：\n' + '\n'.join(result.failed_vers))
                else:
                    failed_content = ""
                    for i in failed_games:
                        failed_content += '\n' + f'在 {result[i].folder_name} 中的：\n{'\n'.join(result[i].failed_vers)}\n'
                    self.send_dialog('有些版本无法导入...', Dialog.Level.ERROR, '以下版本无法正常导入：'+ failed_content)

            if isinstance(result, list):
                # 用来记录哪些表格有问题或需要询问版本隔离的
                query_games: list[int] = []
                failed_games: list[int] = []
                for i in range(len(result)):
                    if result[i].is_suc: continue
                    if result[i].failed_vers != []: failed_games.append(i)
                    if result[i].query_ver != []: query_games.append(i)

                if query_games != []: # 出现无法判断版本隔离的情况，让用户判断
                    series = self.get_query_dialog_series(result)
                
                else: # 没有疑问但有无法导入的版本
                    send_failed_games_content()
                    version.update_versions_json([r.to_dict() for r in result])
                    return _finish_import_versions()
            
            else:
                if result.query_ver != []:
                    series = self.get_query_dialog_series(result)
                else:
                    send_failed_games_content()
                    version.update_versions_json(result.to_dict())
                    return _finish_import_versions()

            # 问答结束后对结果的处理
            @QtCore.Slot(object)
            def _end_asked(queried_result: list):
                if isinstance(queried_result[0][0], dict): # 取样，查看是否为单个游戏文件夹
                    result.update_vers(queried_result)
                    version.update_versions_json(result.to_dict())

                else: # 多个游戏文件夹的情况

                    # 应用询问结果
                    for i in query_games:
                        print(f"queried result {i}: {queried_result[i]}")
                        result[i].update_vers(queried_result[i])

                    # 先弹出导入成功的数量信息
                    self.send_message(f'成功导入版本', Dialog.Level.DONE)

                    if failed_games != []: # 出现无法正常导入的版本，弹窗提示
                        send_failed_games_content()

                    # 将解析完成的数据添加进本地的versions.json
                    version.update_versions_json([r.to_dict() for r in result])
                    # 更新versions.json数据
                
                # 版本路径解析完毕了，接下来就是加载前端版本列表
                self.versions_manager.refresh()
                self.switch_window(Terminal.WindowEnum.MIGRATE)

            # 开始问答！
            self.ask_in_series(series, _end_asked)
            
    def get_query_dialog_series(self, result: version.PathParseResult | list[version.PathParseResult]):
        '''
        生成一个用于询问版本隔离的问答框系列
        Args:
            versions(list[list[dict], list[dict], list[dict]]): 可操作的版本集合，versions[0]为成功解析的版本列表，versions[1]为待询问的版本列表，其中，versions中的偶数项为版本隔离情况下的版本信息dict，奇数项为非版本隔离情况下的版本信息dict。
        '''
        if isinstance(result, list):
            data = [d.get_vers() for d in result]
            series = self.gen_a_series('indie_query_mulit', data)
            def add_node(i_games: int, i_vers: int, node: Dialog.DialogSeries.DialogTreeNode, next_query_game_i: int=None):
                action = Dialog.DialogSeries.Action('NEXT', 0)
                is_query_vers_finished = False

                if i_games == 0 and next_query_game_i is None: # 初次使用，先找到第一个需要询问的版本吧
                    for i_games in range(i_games, len(data)):
                        if data[i_games][1] == []: continue # 跳过没有问题的游戏目录
                        else: 
                            break
                    if len(data) < i_games+1: # 索引溢出，说明后面没有其他需要询问的版本了
                        return
                        
                if len(data[i_games][1]) <= i_vers+2: # 这个完成之后，就没有剩余待询问版本
                    is_query_vers_finished = True
                    if len(data) <= i_games+1: # 这已经是最后一个版本了
                        action = Dialog.DialogSeries.Action('END')
                    else:
                        # 先记录下一个需要询问的版本位置
                        for i in range(i_games+1, len(data)):
                            print(i)
                            if data[i][1] == []: # 跳过没有问题的游戏目录
                                print('has')
                                next_query_game_i = i
                            else: 
                                break
                        print(next_query_game_i, len(data))
                        if len(data) <= next_query_game_i+1: # 索引溢出，说明后面没有其他需要询问的版本了
                            next_query_game_i = i_games
                            action = Dialog.DialogSeries.Action('END')
                    
                query_ver = data[i_games][1][i_vers]
                node.create_dialog_series_window(
                            '出现无法确定版本隔离的情况',
                            Dialog.Level.WARNING,
                            f"版本名称：{query_ver['name']}\n版本号：{query_ver['version']}\n版本路径：{query_ver['game_path']}\n模组加载器：{query_ver['mod_loader']}\n\n该版本是否启用版本隔离？",
                        ).add_button(
                            '是', Dialog.Level.DONE, action, Dialog.DialogSeries.Func(data[i_games][1][i_vers], (i_games, 0, None))
                        ).add_button(
                            '否', Dialog.Level.ERROR, action, Dialog.DialogSeries.Func(data[i_games][1][i_vers+1], (i_games, 0, None))
                        ).add_button(
                            '不知道啊', Dialog.Level.INFO, action, Dialog.DialogSeries.Func(data[i_games][1][i_vers], (i_games, 0, None)), Dialog.DialogSeries.Func(data[i_games][1][i_vers+1], (i_games, 0, None)), hover_text="将会各添加一个隔离和非隔离的版本"
                        ).add_button(
                            '跳过该版本', Dialog.Level.INFO, action
                        )
                if action.type != 'END':
                    if is_query_vers_finished: # 无剩余版本但后续其他游戏目录还有需要询问的，转到下一个需要询问的游戏目录
                        print('next game')
                        add_node(next_query_game_i, 0, node.add_new_dialog_node(), None)
                    else: # 还有剩余版本，继续在相同版本询问
                        print('next ver')
                        add_node(i_games, i_vers+2, node.add_new_dialog_node(), next_query_game_i)

            add_node(0, 0, series.create_dialog_tree())
            return series

        else: # 单个游戏文件夹的版本列表
            data = result.get_vers()
            series = self.gen_a_series('indie_query_single', data)
            def add_node(i: int, node: Dialog.DialogSeries.DialogTreeNode):
                if len(result.query_ver) > i+2:
                    action = Dialog.DialogSeries.Action('NEXT', 0)
                else: action = Dialog.DialogSeries.Action('END')
                    
                node.create_dialog_series_window(
                            '出现无法确定版本隔离的情况',
                            Dialog.Level.WARNING,
                            f"版本名称：{data[1][i]['name']}\n版本号：{data[1][i]['version']}\n版本路径：{data[1][i]['game_path']}\n模组加载器：{data[1][i]['mod_loader']}\n\n该版本是否启用版本隔离？",
                        ).add_button(
                            '是', Dialog.Level.DONE, action, Dialog.DialogSeries.Func(data[1][i], (0, None))
                        ).add_button(
                            '否', Dialog.Level.ERROR, action, Dialog.DialogSeries.Func(data[1][i+1], (0, None))
                        ).add_button(
                            '不知道啊', Dialog.Level.INFO, action, Dialog.DialogSeries.Func(data[1][i], (0, None)), Dialog.DialogSeries.Func(data[1][i+1], (0, None)), hover_text="将会各添加一个隔离和非隔离的版本"
                        ).add_button(
                            '跳过该版本', Dialog.Level.INFO, action
                        )
                if action.type != 'END':
                    add_node(i+2, node.add_new_dialog_node())
                
            add_node(0, series.create_dialog_tree())
            return series
        
    def clear_all_games(self):
        self.versions_manager.clear_all_games()

    def refresh_all_games(self) -> list[dict]:
        '''
        同步启动器更改，更新所有版本的信息
        Returns:
            list[dict]: 刷新后的所有版本信息
        '''
        games = version.get_versions()
        changed_vers_count = 0
        game_results: list[version.PathParseResult] = []
        for game in games:
            game_results.append(version.add_game(Path(game['folder_path'])))
            
        return self.check_and_apply_refresh_result(game_results)
        
    def check_and_apply_refresh_result(self, result: version.PathParseResult | list[version.PathParseResult]) -> list[dict] | None:
        '''
        检查并将导入结果写入versions.json中
        Returns:
            list[dict]|None: 完成写入之后的versions.json中内容。若为None，则说明正在向用户询问版本隔离的信息。
        '''
        def _finish_refresh_versions() -> list[dict]: # 将结果写入导入
            try:
                if versions:= version.get_versions():
                    self.versions_manager.games_json = versions
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

        if isinstance(result, version.PathParseResult) and result.is_suc: # 只有一个PathParseResult的情况，且全解析成功了！直接用这个数据同步到本地并更新前端
            version.update_versions_json(result.to_dict())
            return _finish_refresh_versions()
        
        else:
            def send_failed_games_content():
                if isinstance(result, version.PathParseResult):
                    self.send_dialog('有些版本无法导入...', Dialog.Level.ERROR, '以下版本无法正常导入：\n' + '\n'.join(result.failed_vers))
                else:
                    failed_content = ""
                    for i in failed_games:
                        failed_content += '\n' + f'在 {result[i].folder_name} 中的：\n{'\n'.join(result[i].failed_vers)}\n'
                    self.send_dialog('有些版本无法导入...', Dialog.Level.ERROR, '以下版本无法正常导入：'+ failed_content)

            if isinstance(result, list):
                # 用来记录哪些表格有问题或需要询问版本隔离的
                query_games: list[int] = []
                failed_games: list[int] = []
                for i in range(len(result)):
                    if result[i].is_suc: continue
                    if result[i].failed_vers != []: failed_games.append(i)
                    if result[i].query_ver != []: query_games.append(i)

                if query_games != []: # 出现无法判断版本隔离的情况，让用户判断
                    print(result)
                    series = self.get_query_dialog_series(result)
                
                else: # 没有疑问但有无法导入的版本
                    send_failed_games_content()
                    version.update_versions_json([r.to_dict() for r in result])
                    return _finish_refresh_versions()
            
            else:
                if result.query_ver != []:
                    series = self.get_query_dialog_series(result)
                else:
                    send_failed_games_content()
                    version.update_versions_json(result.to_dict())
                    return _finish_refresh_versions()

            # 问答结束后对结果的处理
            @QtCore.Slot(object)
            def _end_asked(queried_result: list):
                if isinstance(queried_result[0][0], dict): # 取样，查看是否为单个游戏文件夹
                    result.update_vers(queried_result)
                    version.update_versions_json(result.to_dict())

                else: # 多个游戏文件夹的情况

                    # 应用询问结果
                    for i in query_games:
                        print(f"queried result {i}: {queried_result[i]}")
                        result[i].update_vers(queried_result[i])

                    # 先弹出导入成功的数量信息
                    self.send_message(f'已刷新所有游戏目录', Dialog.Level.DONE)

                    if failed_games != []: # 出现无法正常导入的版本，弹窗提示
                        send_failed_games_content()

                    # 将解析完成的数据添加进本地的versions.json
                    version.update_versions_json([r.to_dict() for r in result])
                    # 更新versions.json数据
                
                # 版本路径解析完毕了，接下来就是加载前端版本列表
                self.versions_manager.refresh()
                self.switch_window(Terminal.WindowEnum.MIGRATE)

            # 开始问答！
            self.ask_in_series(series, _end_asked)


    # == 前端窗口 ==

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

    # == versions.json操作代理方法 ==

    def get_games(self) -> list[dict]:
        '''获取versions.json内容'''
        return self.versions_manager.get_games()
    
    def get_game_by_path(self, folder_path: str) -> dict | None:
        '''
        通过游戏文件夹名获取对应的游戏文件夹dict
        Args:
            folder_name (str): 游戏文件夹名
        Returns:
            dict|None: 对应的游戏文件夹dict，若不存在则返回None
        '''
        return self.versions_manager.get_game_by_path(folder_path)
    
    def remove_version(self, game: dict | str, version: dict | str):
        '''
        移除指定游戏文件夹中的指定版本
        Args:
            game (dict | str): 该游戏文件夹的 dict 或 folder_path 字符串
            version (dict | str): 该版本的 dict 或 game_jar 路径字符串
        '''
        self.versions_manager.remove_version(game, version)

    def remove_game(self, game: dict | str):
        """
        移除整个游戏文件夹条目
        Args:
            game: 游戏条目 dict 或 folder_path 字符串
        
        Raises:
            MCException.NoSuchGame: 若指定的游戏文件夹不在当前索引中
        """
        self.versions_manager.remove_game(game)

    def refresh_game(self, game: dict | str) -> list[dict] | None:
        '''
        更新游戏文件夹列表
        Args:
            game: 完整的游戏条目 dict 或是 folder_path
        '''
        return self.versions_manager.refresh_game(game)

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
        mod_list: list[str] = None
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
            
    def download_mods(self, source_dir: str, target_dir: str, target_ver: str, mod_loader: str, file_name_list: list[str]):
        # 缓存，记录没有下载完成的mod
        if not os.path.exists(f"{target_dir}dl.txt"):
            with open(f"{target_dir}dl.txt", 'w') as f:
                logging.info("已创建缓存文件dl.txt")
        with open(f"{target_dir}dl.txt", 'r') as f:
            logging.info("读取缓存文件dl.txt")
            file_name_list_done: list[str] = [line.strip() for line in f.readlines()]
        self.failed_mods_not_adapt: list[str] = []

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
                report_content += '\n'

            # 模组下载失败
            if self.failed_mods_dl != []:
                report_content += f"以下模组下载失败：\n"
                for file in self.failed_mods_dl:
                    report_content += file + '\n'
                report_content += '\n'

            # 文件迁移失败（这个部分问题就比较多了，就由说明具体错误
            if self.failed_files_copy != []:
                title = "遇到问题了..."
                level = Dialog.Level.ERROR
                report_content += f"以下文件在迁移时出错：\n"
                for file in self.failed_files_copy:
                    report_content += f"{file[0]}：{file[1]}\n"
                report_content += '\n'
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

class VersionsJsonManager:
    def __init__(self, terminal: 'Terminal'):
        self.terminal = terminal
        try:
            self.games_json = version.get_versions()
            self.game_folder_paths = [g['folder_path'] for g in self.games_json] # 用于通过folder_path快速索引游戏文件夹
        except (TypeError, json.JSONDecodeError) as e:
            logging.error("解析 versions.json 文件错误")
            raise e

    def get_games(self) -> list[dict]:
        return self.games_json

    # ========== 版本管理 ==========

    def add_version(self, game: dict | str, new_version: dict):
        """
        向指定游戏文件夹添加一个新版本
        Args:
            game: 游戏条目 dict 或 folder_path 字符串
            new_version: 完整的版本 dict（需包含 game_jar 等字段）
        """
        if isinstance(game, str):
            game = self.get_game_by_path(game)
            if game is None:
                self.terminal.send_message('未找到对应游戏文件夹，无法添加版本', Message.Level.ERROR)
                return

        try:
            idx = self.games_json.index(game)
        except ValueError:
            self.terminal.send_message('游戏文件夹不在当前管理列表中', Message.Level.ERROR)
            return

        # 避免重复添加（按 game_jar 判断）
        for v in self.games_json[idx]['versions']:
            if v.get('game_jar') == new_version.get('game_jar'):
                self.terminal.send_message('该版本已存在，跳过添加', Message.Level.INFO)
                return

        self.games_json[idx]['versions'].append(new_version)
        self.terminal.send_message(f'已添加版本: {new_version.get("name", "unnamed")}', Message.Level.DONE)
        self._save()

    def remove_version(self, game: dict | str, version: dict | str):
        """
        移除指定游戏文件夹中的指定版本
        Args:
            game(dict | str): 游戏条目 dict 或 folder_path 字符串
            version(dict | str): 版本条目 dict 或 game_jar 路径字符串
        Raises:
            MCException.NoSuchGame: 若指定的游戏文件夹不在当前索引中
            MCException.NoSuchVersion: 若指定的版本不在对应游戏文件夹中
        """
        # 验证game
        if isinstance(game, str):
            game = self.get_game_by_path(game)
            if game is None:
                logging.info('未找到对应游戏文件夹')
                raise MCException.NoSuchGameFolder('未找到对应游戏文件夹')
        # 验证该game是否存在该versions.json中
        try:
            game_i = self.games_json.index(game)

        except ValueError:
            logging.info('游戏文件夹不在列表中或已被改变')
            raise MCException.NoSuchGameFolder('游戏文件夹不在列表中或已被改变')

        # 获取version
        if isinstance(version, str):
            version = self.get_ver_by_game_jar(game, version)
            if version is None:
                logging.info('未找到对应版本')
                raise MCException.NoSuchVersion('未找到对应版本')
        
        # 移除version
        try:
            game_versions: list[dict] = game['versions']
            game_versions.remove(version)
            game['versions'] = game_versions
        except ValueError:
            logging.info('版本不在该游戏文件夹中或已被改变')
            raise MCException.NoSuchGameFolder('版本不在该游戏文件夹中或已被改变')

        # 应用该game的更改
        self.games_json[game_i] = game
        self._save()

        self.terminal.send_message(f'已成功移除版本: {version}', Message.Level.DONE)

    # ========== 游戏文件夹管理 ==========

    def add_game(self, new_game: dict):
        """
        添加一个全新的游戏文件夹条目
        Args:
            new_game: 完整的游戏条目 dict 或是 folder_path
        """
        if not isinstance(new_game, dict) or 'folder_path' not in new_game:
            self.terminal.send_message('无效的游戏条目格式', Message.Level.ERROR)
            return

        # 检查是否已存在
        for g in self.games_json:
            if g['folder_path'] == new_game['folder_path']:
                self.terminal.send_message('该游戏文件夹已存在，跳过添加', Message.Level.INFO)
                return

        self.games_json.append(new_game)
        self.terminal.send_message(f'已添加游戏: {new_game.get("folder_name", "unnamed")}', Message.Level.DONE)
        self._save()
    
    def refresh_game(self, game: dict | str) -> list[dict] | None:
        '''
        更新游戏文件夹列表
        Args:
            game: 完整的游戏条目 dict 或是 folder_path
        '''
        self.refresh()
        if isinstance(game, dict): # 由game获取folder_path
            folder_path = game['folder_path']

        # 检验该folder_path是否存在
        try:
            self.game_folder_paths.index(folder_path)
        except ValueError:
            logging.warning('该游戏目录不存在')
            raise MCException.NoSuchGameFolder()
        
        # 获取最新该游戏文件夹的信息
        result = version.add_game(Path(folder_path))
        if new_games_json:= self.terminal.check_and_apply_import_result(result):
            self.games_json = new_games_json
            return self.games_json

    def remove_game(self, game: dict | str):
        """
        移除整个游戏文件夹条目
        Args:
            game: 游戏条目 dict 或 folder_path 字符串
        
        Raises:
            MCException.NoSuchGame: 若指定的游戏文件夹不在当前索引中
        """
        # 通过folder_path定位game
        try:
            if isinstance(game, str):
                i = self.game_folder_paths.index(game) # 验证是否存在该folder_path
            else:
                i = self.games_json.index(game)
        except ValueError:
            logging.info('游戏文件夹不在当前索引中，已忽略操作')
            raise MCException.NoSuchGameFolder()

        # 移除game
        try:
            game_name = self.games_json.pop(i)['folder_name']
            self.game_folder_paths.pop(i)
            self._save()
            self.terminal.send_message(f'已移除游戏: {game_name}', Message.Level.DONE)
        except ValueError:
            logging.info('游戏文件夹不在当前索引中，已忽略操作')
            raise MCException.NoSuchGameFolder()

    def clear_all_games(self):
        version.clear_all_vers()
        self.games_json = []
        logging.info("已清除所有游戏版本")

    # ========== 辅助方法 ==========

    def get_game_by_path(self, folder_path: str) -> dict | None:
        """根据 folder_path 查找游戏条目"""
        for g in self.games_json:
            if g.get('folder_path') == folder_path:
                return g
        return None

    def get_ver_by_game_jar(self, game: dict, game_jar: str) -> dict | None:
        """根据 game_jar 查找版本条目"""
        for v in game.get('versions', []):
            if v.get('game_jar') == game_jar:
                return v
        return None

    def refresh(self):
        """重新从文件加载（用于外部修改后同步）"""
        try:
            self.games_json = version.get_versions()
            self.game_folder_paths = [g['folder_path'] for g in self.games_json]
            logging.info('已重新加载 versions.json')
        except Exception as e:
            self.terminal.send_message(f'重新加载失败: {e}', Message.Level.ERROR)

    def _save(self):
        """统一保存入口，调用外部 update_versions_json"""
        try:
            with open('versions.json', 'w', encoding='utf-8') as f:
                json.dump(self.games_json, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.terminal.send_message(f'保存 versions.json 失败: {e}', Message.Level.ERROR)
            return
        logging.info("保存 versions.json 文件")