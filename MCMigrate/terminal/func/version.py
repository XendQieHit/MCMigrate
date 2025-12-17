from pathlib import Path
from typing import List
from dataclasses import dataclass, asdict
import json, re, zipfile, os, winreg
import logging, MCException

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PathParseResult:
    '''用于包装解析结果的类'''
    is_suc: bool
    folder_name: str
    folder_path: str
    done_vers: list[dict]
    query_ver: list[dict]
    failed_vers: list[str]

    def to_dict(self) -> dict:
        return {'folder_name': self.folder_name, 'folder_path': self.folder_path, 'versions': self.done_vers}
    
    def get_vers(self) -> list[list]:
        '''
        获得解析得到的全部版本信息
        Returns:
            list[list]: 一个版本列表
        '''
        return [self.done_vers, self.query_ver, self.failed_vers]
    
    def update_vers(self, vers_list: list[list]):
        '''将处理完后的全部版本信息应用更新'''
        self.done_vers = vers_list[0]
        self.query_ver = vers_list[1]
        self.failed_vers = vers_list[2]


@dataclass
class VersionParseResult:
    '''用于模板化版本dict，这样就不用改的很费劲了'''
    game_jar: str
    name: str
    game_path: str
    version: str
    mod_loader: str
    is_indie: bool
    launcher: str

    def to_dict(self):
        return asdict(self)

def get_versions_from_pcl() -> list[PathParseResult]:
    '''从pcl导入mc版本, Returns与add_version()方法相同'''
    # 获取PCL在注册表存储的.minecraft文件夹路径数据
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\PCL')
        value: str = winreg.QueryValueEx(key, "launchFolders")[0]
        logger.info(value)
    except FileNotFoundError as e:
        logger.error(f"注册表键或值不存在: {e}")
        return None
    except PermissionError as e:
        logger.error(f"权限不足，无法访问注册表: {e}")
        return None
    except Exception as e:
        logger.error(f"读取注册表时发生了意外的错误：{e}")
    finally: winreg.CloseKey(winreg.HKEY_CURRENT_USER)

    parse_results: list[PathParseResult] = []
    for p_info in value.split("|"):
        # 拆分解析数据
        p_name, p_path = p_info.split(">") # p_name是在PCL里，用户给.minecraft游戏文件夹取的自定义名称
        folder_path = Path(p_path)
        result = add_game(folder_path)
        result.folder_name = p_name
        parse_results.append(result)

    return parse_results

def add_game(path: Path) -> PathParseResult:
    '''
    解析并获取版本信息
    tuple[0]为该游戏文件夹的空白json，tuple[1]为对该游戏文件夹的解析结果
        \n解析结果为tuple[dict]，则说明无异常，可直接使用
        \n解析结果为None, 说明解析失败或未找到
        \n解析结果为list[list[dict], list[dict], list[dict]]，则发现无法判断是否版本隔离的版本，
        \nlist[0]是已判断成功的版本信息，
        \nlist[1]是无法判断成功的版本信息，其中，每个版本各有一份隔离和非隔离的版本信息，需要用户判断是否为版本隔离来决定剔除。
        \nlist[2]是解析失败的版本
    \n该方法只是获取解析到的版本信息，具体将其同步添加到本地的versions.json，还需要将获取到的值解析并调用update_versions_json(versions)方法
    '''
    # 检测是否是游戏文件夹
    if path.name == ".minecraft" or (path / "versions").is_dir():
        logger.info("找到游戏文件夹，正在解析导入游戏版本...")

        # 获取并打包解析结果
        game_name = path.parent.name
        versions = parse_path(path)
        if isinstance(versions, tuple):
            return PathParseResult(True, game_name, path.as_posix(),  versions, [], [])
        return PathParseResult(False, game_name, path.as_posix(), *versions)
    raise MCException.NotMCGameFolder()
    
def update_versions_json(games: dict | list[dict]):
    '''
    更新versions.json
    Args:
        games(dict | list[dict]): 单个游戏文件夹的json或是多个游戏文件夹的json列表
    '''
    new_content = []
    if not games: # 过滤None
        return
    try:
        with open('versions.json', 'r', encoding='utf-8') as f:
            content = json.load(f)

        content_folder_paths = [d['folder_path'] for d in content]
        def update_game(game):
            try: # 查找并更新对应游戏文件夹的版本列表
                i = content_folder_paths.index(game['folder_path'])
                content[i]['versions'] = game['versions']
                logger.debug(f"更改位于content_folder_path[{i}]的 {game['folder_path']}")
            except ValueError: # 未找到对应的游戏文件夹，是新的游戏文件夹，稍后添加
                logger.debug(f"新增游戏文件夹 {game['folder_name'], game['folder_path']}")
                new_content.append(game)

        def apply_games(games: dict | list[dict]):
            if isinstance(games, dict):
                update_game(games)
            else: 
                for game in games:
                    update_game(game)
        apply_games(games)
        
    except (FileNotFoundError, ValueError) as e: # 解析失败或文件为空
        content = []
        logger.info("versions.json文件不存在或格式错误，已重新生成")
        if isinstance(games, dict):
            new_content.append(games)
        else:
            new_content.extend(games)
    except TypeError: # 谁又乱动versions.json文件了
        clear_all_vers()
        apply_games(games)

    # 添加新增游戏文件夹
    content[0:0] = new_content

    with open('versions.json', 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    
    logger.info(f"已更新 versions.json，新增 {len(new_content)} 个版本")

def parse_path(path: Path) -> tuple[dict] | list[list[dict], list[dict], list[dict]]:
    """解析.minecraft文件夹"""
    done_versions = []
    query_versions = []
    failed_versions = []

    path_versions = Path(path / 'versions')
    if path_versions.exists():
        logger.info("找到versions文件夹，开始逐个解析版本")
        version_items = list(path_versions.iterdir())
        for p in version_items:
            logger.info(p.name)
            if not p.is_dir(): continue
            p_result = parse_single_ver_path(p)
            if isinstance(p_result, list): # 解析成功
                done_versions.extend(p_result)
            elif isinstance(p_result, tuple): # 无法判断版本隔离的情况
                query_versions.extend(p_result)
            else: # 布兑！有问题！
                failed_versions.append(str(p))
    else: 
        raise MCException.VersionsFolderNotFound()

    # 汇总结果
    has_exception = False
    if failed_versions != []:
        logger.error(f"以下版本解析失败：\n{'\n'.join(failed_versions)}")
        has_exception = True
    if query_versions != []:
        logger.warning(f"无法确定以下版本的隔离设置：\n{'\n'.join([query_versions[i]['name'] for i in range(0, len(query_versions), 2)])}")
        has_exception = True
    if has_exception: return [done_versions, query_versions, failed_versions]
    return tuple(done_versions)

def parse_single_ver_path(p: Path) -> list[dict] | tuple[dict, dict] | None:
    '''
    解析单个版本的信息
    Returns:
        list[dict]: 解析得到的版本信息（？你问为什么是列表单个dict？因为不同启动器有不同的配置文件，版本隔离信息这一块会有不同，所以都加
        
        tuple[dict, dict]: 出现无法判断版本隔离的情况，就返回版本隔离和非版本隔离的两份dict，tuple[0]隔离版，tuple[1]为非隔离版

        None: 解析失败炸了;w;
    '''
    if p.is_dir() and list(p.glob('*.json')) != []: # 好耶！找到版本了耶！
        # 但是在这之前，还要先判断有没有版本隔离
        # 很不幸，版本隔离是靠每次启动时，通过预填启动参数--gameDir，来确定游戏文件夹来确定的
        # 而预填启动参数，是交给启动器来进行的
        # 可是不同的启动器有不一样的版本隔离配置方法啊啊啊，这又得一个一个排除了
        results = []
        is_confirmed = False
        for item in list(p.iterdir()):
            logger.debug(item)
            if item.is_dir() and item.name == "PCL" and Path.exists(item / "Setup.ini"): # PCL
                logger.debug('PCL')
                result = parse_version_info(p, "PCL2", is_indie_pcl(item))
                if not result: return None # 检测到解析失败直接返回None
                results.append(result)
                is_confirmed = True
                                
            elif item.is_file() and item.name == "hmclversion.cfg": # HMCL
                logger.debug('HMCL')
                # 开了
                result = parse_version_info(p, 'HMCL', is_indie_hmcl(item))
                if not result: return None
                results.append(result)
                is_confirmed = True
                # 是的你没看错，这个就是遇见一个已有的启动器配置就加一份，没办法呀毕竟我也是两个启动都用口牙呜

                # 什么？！都到这里居然什么都没有？那只能去向用户询问是否有版本隔离了...
        if is_confirmed: # 解析成功，直接返回结果
            return results

        return (parse_version_info(p, None, True), parse_version_info(p, None, False)) # 无法判断版本隔离，返回tuple

def is_indie_pcl(pcl_folder) -> bool:
    pcl_ini_file_name = 'Setup.ini'
    if not Path(pcl_folder / pcl_ini_file_name).exists: pcl_ini_file_name = pcl_ini_file_name.lower() # Linux的大小写敏感可能报错，就加了这个（但是linux能跑pcl吗（？
    with open(pcl_folder / pcl_ini_file_name, 'r', encoding='utf-8') as ini_file:
        is_indie = False
        for line in reversed(ini_file.readlines()):
            def to_bool(s: str): # 什么嘛，还是得手动枚举转bool
                if s.upper() == 'TRUE': return True
                elif s.upper() == 'FALSE': return False
            logger.debug(line.strip())
            # V2版本的优先级大于v1
            if "VersionArgumentIndieV2" in line:
                logger.debug("VersionArgumentIndieV2")
                return to_bool(line.split(':')[1].strip())
            
            if "VersionArgumentIndie" in line and int(line.split(':')[1]) == 1:
                logger.debug("VersionArgumentIndie")
                is_indie = True
        return is_indie
    
def is_indie_hmcl(hmcl_cfg_file) -> bool:
    json_file: dict = json.load(open(hmcl_cfg_file, 'r', encoding='utf-8'))
    if int(json_file.get("gameDirType")) == 1: return True
    return False

def parse_version_info(path: Path, launcher, is_indie=True) -> dict | None:
    '''
    解析获取版本的版本号、模组加载器、和版本名等信息
    '''
    game_path = ''
    version = ''
    secondary_mod_loader = ''

    # 获取游戏核心jar文件名字作为唯一版本标识
    game_jar = next(path.glob('*.jar'), None)
    if not game_jar: return None # 找不到jar就不是版本了
    game_jar = game_jar.as_posix()

    # 区别是否版本隔离的路径写入差异
    if is_indie:
        game_path = path.as_posix()
    else: game_path = path.parent.parent.as_posix()
    logger.debug('版本隔离：%s', is_indie)

    # 首先会进行加载器的检测
    # 但因为大部分启动器在选择下载optifine后，同样写入版本json里，这样会混淆optifine端的判断
    # 因此，如果检测到了像fabric, forge那样的强模组加载器，就会直接返回dict
    # 但如果检测到了optifine，那么会暂时先储存版本号和加载器信息，如果后面真的找不到其他的模组加载器的话，就在libraries列表遍历完成后，判断为optifine端，返回之前获取到的版本号和加载器信息dict
    # 其实有这个原理，也可以做liteloader的检测适配，但...现在真的会有人单独用liteloader吗（
    for f in list(path.glob('*.json')):
        # 先看看是不是版本json文件
        try:
            with open(f, 'r', encoding='utf-8') as file:
                content: dict = json.load(file)
                libraries: List[dict] = content.get("libraries")
                logger.debug(f"解析{f.name}")

                for item in libraries: # 有libraries，是版本json文件！进行解析获取版本号和加载器
                    # Fabric
                    fabric = re.search(r'(?<=(net\.fabricmc:intermediary:)).*', item.get("name"))
                    quilt = 'org.quiltmc:' in item.get('name')
                    if fabric != None:
                        # Quilt
                        if quilt:
                            return VersionParseResult(game_jar, path.name, game_path, fabric.group(), 'quilt', is_indie, launcher).to_dict()
                        return VersionParseResult(game_jar, path.name, game_path, fabric.group(), 'fabric', is_indie, launcher).to_dict()
                    
                    # Forge
                    forge = re.search(r'(?<=net\.minecraftforge:forge:)[^-]*', item.get("name"))
                    if forge != None:
                        return VersionParseResult(game_jar, path.name, game_path, forge.group(), 'forge', is_indie, launcher).to_dict()

                    # Optifine
                    optifine = re.search(r'(?<=(optifine:OptiFine:))[^_]*', item.get("name"))
                    if optifine != None:
                        version = optifine.group()
                        secondary_mod_loader = 'optifine'

                # NeoForge
                game: List[str] = content.get('arguments').get('game')
                for i in range(len(game)):
                    if game[i] == "--fml.mcVersion":
                        return VersionParseResult(game_jar, path.name, game_path, game[i+1], 'neoforge', is_indie, launcher).to_dict()
                
                # 因为有可能forge和fabric在启动器时一起安装，会导致两个特征词条都会出现，因此需要后置区别
                if secondary_mod_loader != '':
                    return VersionParseResult(game_jar, path.name, game_path, version, secondary_mod_loader, is_indie, launcher).to_dict()
                
        except (KeyError, AttributeError, TypeError):
            # 找不到libraries，换个方式打开...?
            logger.error(f"解析{f.name}失败")

        try:
            # Release & Snapshot & Unknown
            # 在区分版本类型之前，需要区别该版本的下载来源是PCL还是HMCL还是直接官启，这样才能正确解析json
            hmcl = content.get('patches', False)
            pcl = content.get('clientVersion', False)
            ver_type = content.get('type', None)
            if hmcl: # HMCL
                return VersionParseResult(game_jar, path.name, game_path, hmcl[0]['version'], ver_type, is_indie, launcher).to_dict()
            elif pcl: # PCL
                return VersionParseResult(game_jar, path.name, game_path, pcl, ver_type, is_indie, launcher).to_dict()
        except (KeyError, AttributeError):
            # 看来都没有
            continue
            
    # 怎么都没有版本json...看来只能拆jar包了
    try:
        with zipfile.ZipFile(path / f'{path.name}.jar', 'r') as jar_file:
            logger.info("解析版本jar包")
            with jar_file.open('version.json', 'r') as json_file:
                logger.info("读取完成")
                return VersionParseResult(game_jar, path.name, game_path, json.load(json_file)['id'], ver_type, is_indie, launcher).to_dict()
    except Exception as e: # 万策尽QAQ————
        logger.error("无法解析版本号: %s", e)
        return None
        
def refresh_version_info(version: dict) -> list[dict] | tuple[dict, dict] | None:
    '''
    同步启动器更改，更新该版本的信息
    '''
    try:
        game_jar = Path(version['game_jar'])
        p_result = parse_single_ver_path(game_jar.parent)
    except KeyError: # 兼容0.0.4版本之前的versions.json格式
        game_path = Path(version['game_path'])
        if game_path.name == '.minecraft': return # 非隔离版本就没法确定了，无视
        p_result = parse_single_ver_path(game_path)
    
    logger.info(f"已更新{version['name']}版本信息") # 总有种不想的预感...会不会什么奇怪的版本名就把这个爆了吧...?
    return p_result

def gen_new_versions() -> list[dict]:
    with open("versions.json", "w", encoding='utf-8') as f:
        json.dump([], f)

def get_versions() -> list[dict]:
    # 空文件检测
    if not os.path.exists("versions.json") or os.path.getsize("versions.json") < 8:
        gen_new_versions()

    # 读取
    try:
        with open("versions.json", "r", encoding="utf-8") as f:
            versions = json.load(f)
            if isinstance(versions, list):
                return versions
            else:
                logger.error("versions.json文件格式错误")
                raise TypeError("versions.json文件格式错误")
    except Exception as e:
        logger.error("读取文件失败")
        raise e
    
def clear_all_vers():
    '''清除所有版本信息'''
    if os.path.exists('versions.json'):
        logger.info('已删除versions.json文件')
        os.remove('versions.json')

def upgrade_versions_json():
    '''兼容升级旧的versions.json文件'''
    old_versions = get_versions()
    game_names = [] # 用于快速判断和索引游戏文件夹在games里的位置
    games: list[dict] = []

    for ver in old_versions:
        try:
            i = game_names.index(Path(ver['game_jar']).parents[3].name) # 判断是否已添加该游戏文件夹

        except ValueError: # 
            path = Path(ver['game_jar'])
            game_name = path.parents[3].name # 自动取.mincraft文件夹的上一层文件夹名
            game_path = path.parents[2].as_posix()
            game_versions = []

            # 添加游戏文件夹
            game_names.append(game_name)
            i = len(game_names) - 1
            game_dict = {'folder_name': game_name, 'folder_path': game_path, 'versions': game_versions}
            games.append(game_dict)

        games[i]['versions'].append(ver)

    try:
        with open('versions.json', 'w', encoding='utf-8') as f:
            json.dump(games, f)
            logger.info('已将versions.json升级为新版本格式')
            return games
            
    except Exception as e:
        logger.error("升级versions.json文件失败")
        raise e