from pathlib import Path
from typing import List
import json, re, zipfile
import logging, Message

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
message = Message.Messageable(logger)


def add_version(path: Path) -> list[dict] | None:
    # 检测是否是游戏文件夹
    if path.name == ".minecraft" or (path / "versions").is_dir():
        logger.info("找到游戏文件夹，正在解析导入游戏版本...")
        versions = parse_path(path)
        update_versions_json(versions)
        return versions
    logger.error("查找不到.minecraft或游戏文件夹，请检查是否正确选取导入")
    return None
    
def update_versions_json(versions: list[dict]):
    if not versions:
        return

    try:
        with open('versions.json', 'r', encoding='utf-8') as f:
            content = json.load(f)
    except (FileNotFoundError, ValueError):
        content = []

    # 将字典转为可哈希的 frozenset（或 tuple）去重
    def to_hashable(d):
        return frozenset(d.items())
    
    existing_set = {to_hashable(item) for item in content}
    new_items = [
        v for v in versions
        if to_hashable(v) not in existing_set
    ]

    content[0:0] = new_items

    with open('versions.json', 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    
    logger.info(f"已更新 versions.json，新增 {len(new_items)} 个版本")

def parse_path(path: Path) -> list[dict]:
    versions = []
    path_versions = Path(path / 'versions')
    if path_versions.exists():
        logger.info("找到versions文件夹，开始逐个解析版本")
        version_items = list(path_versions.iterdir())
        for p in version_items:
            logger.info(p.name)
            if p.is_dir() and list(p.glob('*.json')) != []: # 好耶！找到版本了耶！
                # 但是在这之前，还要先判断有没有版本隔离
                # 很不幸，版本隔离是靠每次启动时，通过预填启动参数--gameDir，来确定游戏文件夹来确定的
                # 而预填启动参数，是交给启动器来进行的
                # 可是不同的启动器有不一样的版本隔离配置方法啊啊啊，这又得一个一个排除了
                is_confirmed = False
                for item in list(p.iterdir()):
                    logger.info(item)
                    if item.is_dir() and item.name == "PCL": # PCL
                        logger.info('PCL')
                        versions.append(parse_version(p, is_indie_pcl(item)))
                        is_confirmed = True
                        break
                                
                    elif item.is_file() and item.name == "hmclversion.cfg": # HMCL
                        logger.info('HMCL')
                        # 开了
                        versions.append(parse_version(p, is_indie_hmcl(item)))
                        is_confirmed = True
                        break
                # 什么？！都到这里居然什么都没有？那只能隔离和非隔离的都加一份了
                # 好吧其实应该待其他确定版本导入完成后，再去向用户询问是否有版本隔离
                # 但是现在还是先专注与功能实现吧...
                if not is_confirmed:
                    versions.append(parse_version(p, True))
                    versions.append(parse_version(p, False))
    else: 
        logger.warning("未发现versions文件夹，还没下游戏吗...?")

    filtered_versions = []
    for item in versions:
        if item:
            filtered_versions.append(item)
        else:
            logger.error(f"导入{item}失败")
    return filtered_versions

def is_indie_pcl(pcl_folder) -> bool:
    with open(pcl_folder / 'Setup.ini', 'r', encoding='utf-8') as ini_file:
        for line in reversed(ini_file.readlines()):
            logger.info(line)
            # 开版本隔离了
            if "VersionArgumentIndieV2" in line and bool(line.split(':')[1]):
                return True
            if "VersionArgumentIndie" in line and int(line.split(':')[1]) == 1:
                return True
        return False
    
def is_indie_hmcl(hmcl_cfg_file) -> bool:
    json_file: dict = json.load(open(hmcl_cfg_file, 'r', encoding='utf-8'))
    if int(json_file.get("gameDirType")) == 1: return True
    return False

def parse_version(path: Path, is_indie=True) -> dict:
    # 区别是否版本隔离的路径写入差异
    game_path = ''
    version = ''
    secondary_mod_loader = ''
    if is_indie:
        game_path = path.as_posix()
    else: game_path = path.parent.parent.as_posix()
    logger.info('版本隔离：%s', is_indie)

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
                logger.info(f"解析{f.name}")

                for item in libraries: # 有libraries，是版本json文件！进行解析获取版本号和加载器
                    # Fabric
                    fabric = re.search(r'(?<=(net\.fabricmc:intermediary:)).*', item.get("name"))
                    quilt = 'org.quiltmc:' in item.get('name')
                    if fabric != None:
                        # Quilt
                        if quilt:
                            return {'name': path.name, 'game_path': game_path, 'version': fabric, 'mod_loader': 'quilt', 'is_indie': is_indie}
                        return {'name': path.name, 'game_path': game_path, 'version': fabric.group(), 'mod_loader': 'fabric', 'is_indie': is_indie}
                    
                    # Forge
                    forge = re.search(r'(?<=net\.minecraftforge:forge:)[^-]*', item.get("name"))
                    if forge != None:
                        return {'name': path.name, 'game_path': game_path, 'version': forge.group(), 'mod_loader': 'forge', 'is_indie': is_indie}

                    # Optifine
                    optifine = re.search(r'(?<=(optifine:OptiFine:))[^_]*', item.get("name"))
                    if optifine != None:
                        version = optifine.group()
                        secondary_mod_loader = 'optifine'

                # NeoForge
                game: List[str] = content.get('arguments').get('game')
                for i in range(len(game)):
                    if game[i] == "--fml.mcVersion":
                        return {'name': path.name, 'game_path': game_path, 'version': game[i+1], 'mod_loader': 'neoforge', 'is_indie': is_indie}
                
                # 因为有可能forge和fabric在启动器时一起安装，会导致两个特征词条都会出现，因此需要后置区别
                if secondary_mod_loader != '':
                    return  {'name': path.name, 'game_path': game_path, 'version': version, 'mod_loader': secondary_mod_loader, 'is_indie': is_indie}
                
        except (KeyError, AttributeError):
            # 找不到libraries，换个方式打开...?
            logger.error(f"解析{f.name}失败")
            pass

        try:
            # Release & Snapshot & Unknown
            # 在区分版本类型之前，需要区别该版本的下载来源是PCL还是HMCL还是直接官启，这样才能正确解析json
            hmcl = content.get('patches', False)
            pcl = content.get('clientVersion', False)
            ver_type = content.get('type', None)
            if hmcl: # HMCL
                return {'name': path.name, 'game_path': game_path, 'version': hmcl[0]['version'], 'mod_loader': ver_type, 'is_indie': is_indie}
            elif pcl: # PCL
                return {'name': path.name, 'game_path': game_path, 'version': pcl, 'mod_loader': ver_type, 'is_indie': is_indie}
        except (KeyError, AttributeError):
            # 看来都没有
            continue
            
    # 怎么都没有版本json...看来只能拆jar包了
    try:
        with zipfile.ZipFile(path / f'{path.name}.jar', 'r') as jar_file:
            logger.info("解析版本jar包")
            with jar_file.open('version.json', 'r') as json_file:
                logger.info("读取完成")
                return {'name': path.name, 'game_path': game_path, 'version': json.load(json_file)['id'], 'mod_loader': ver_type, 'is_indie': is_indie}
    except Exception as e: # 万策尽QAQ————
        logger.error("无法解析版本号: %s", e)
        return None

def get_versions() -> list[dict]:
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