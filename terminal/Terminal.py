from enum import Enum
from typing import List
from pathlib import Path
from PySide6 import QtWidgets, QtCore
import Message, Dialog, MCException
from terminal.func import version, mod, config
import os, requests, hashlib, yaml, shutil, json, re, zipfile, logging

logging.basicConfig(level=logging.INFO)

class Terminal(Message.Messageable, Dialog.Dialogable):
    def __init__(self, main_window: QtWidgets.QMainWindow):
        super().__init__(__name__)
        self.config = config.get_config()
        self.is_migrating = False
        self.pending_num = 0
        self.main_window = main_window
    
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
        with open("versions.json", 'r', encoding='utf-8') as f:
            try:
                versions = json.load(f)
                if not versions: # 怎么是空值？
                    raise IOError("version.json内容为空")
                return versions
            except (IOError, OSError) as e:
                self.send_message(f"读取versions.json失败：{e}", Message.Level.ERROR)
                return None
            except Exception as e:
                self.send_message(f"发生了意外的错误：{e}", Message.Level.ERROR)
                return None

    def switch_window(self, window_enum: 'WindowEnum', msg_bar: tuple[str, Message.Level], *params):
        # 切换窗口界面
        self.main_window.setCentralWidget(window_enum.clazz(self, *params))

        # 发送预留消息
        if msg_bar and hasattr(self.main_window.centralWidget(), 'message'):
            self.send_message(*msg_bar)

    def migrate(self, source_json: dict, target_json: dict):
        source_dir = Path(source_json['game_path'])
        target_dir = Path(target_json['game_path'])

        # 路径检查
        if source_dir == None or target_dir == None:
            logging.info("请先选择迁移版本和目标版本")
            self.message_requested.emit("请先选择迁移版本和目标版本", Message.Level.INFO)
            return
        elif source_dir == target_dir:
            self.message_requested.emit('不能迁移自己口牙>_<', Message.Level.WARNING)
            return
        # 条件符合，开始迁移！

        # 计算待处理任务数量（复制文件）
        self.pending_num += len([dir for dir in os.listdir(source_dir) if dir not in list(config.get_config_value('migrate', 'excludes'))])

        not_mod_loader = ['optifine', 'release', 'snapshot', 'unknown']
        if (source_json['mod_loader'] not in not_mod_loader) and (target_json['mod_loader'] not in not_mod_loader):
            mod_list: List[str] = os.listdir(source_dir / "mods")

            # 计算待处理任务数量（mod下载）
            self.pending_num += len(mod_list)
            
            # 开始下载mod
            logging.info("下载mod中")
            self.download_mods(source_dir / "mods", target_dir / "mods", target_json["version"], target_json["mod_loader"], mod_list)
            logging.info("mod下载完成")

        logging.info("迁移游戏文件")
        self.migrate_file(source_dir, target_dir)
        logging.info("游戏文件迁移完成")
        self.message_requested.emit(f"{source_json.get('name')}已迁移至{target_json.get('name')}！", Message.Level.Info)

    def migrate_file(self, source_dir: Path, target_dir: Path):
        for item in Path(source_dir).iterdir():
            if item.name.startswith('.') or item.name.startswith('$'): continue
            if self.config['migrate']['filter_rule'] == 'excludes' and item.name not in self.config['migrate']['excludes']:
                logging.info(f"复制{item}至{target_dir / item.name}")
                try:
                    shutil.copy(item, target_dir / item.name)
                except PermissionError:
                    logging.warning("权限不足")
                except Exception as e:
                    logging.error("未知错误：" + e)
            self.pending_num -= 1
            
    def download_mods(self, source_dir: str, target_dir: str, target_ver: str, mod_loader: str, file_name_list: List[str]):
        # 缓存，记录没有下载完成的mod
        if not os.path.exists(f"{target_dir}dl.txt"):
            with open(f"{target_dir}dl.txt", 'w') as f:
                logging.info("已创建缓存文件dl.txt")
        with open(f"{target_dir}dl.txt", 'r') as f:
            logging.info("读取缓存文件dl.txt")
            file_name_list_done: List[str] = [line.strip() for line in f.readlines()]
        not_adapt_mods: List[str] = []

        for old_file_name in file_name_list:
            logging.info(f"\n{old_file_name}")
            
            # 检测是否已下载，有则跳过
            if old_file_name in file_name_list_done:
                logging.info(f"{old_file_name} 已下载")
                self.pending_num -= 1
                continue

            if not mod.modrinth(target_ver, mod_loader, source_dir, old_file_name, target_dir, not_adapt_mods):
                if not mod.curseforge(target_ver, mod_loader, source_dir, old_file_name, target_dir, not_adapt_mods):
                    list.append(not_adapt_mods, old_file_name)
                    self.pending_num -= 1
                    continue
                self.pending_num -= 1

        # 结果统计
        if len(not_adapt_mods) != 0:
            logging.info("\n\n\n以下模组暂未找到适配：")
            for not_adapt_mod in not_adapt_mods: logging.info(not_adapt_mod)
        else: 
            logging.info("\n\n\n无不适配情况，全部模组已完成版本迁移！")
            os.remove(f"{target_dir}dl.txt")
    
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
        return version.get_versions()
    

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