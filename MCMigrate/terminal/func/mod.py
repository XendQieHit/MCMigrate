from typing import List
from pathlib import Path
from enum import Enum
import requests, hashlib, logging, zipfile, json, re

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# 主要功能方法
HEADERS = {
    "Content-Type": "application/json"
}

class Result(Enum):
    SUCCESS = 1
    NOT_ADAPTED = 2
    FAILED = 3

def modrinth(target_version: str, mod_loader: str, source_dir: str, old_file_name: str, target_dir: str) -> Result | list[str]:
    """
    通过Modrinth进行模组下载更新
    Returns:
        Result: 模组下载的结果状态（成功SUCCESS|不适配NOT_ADAPTED|失败FAILED）
        list: 下载失败的依赖
    """
    if modrinth_update(target_version, mod_loader, source_dir, old_file_name, target_dir) == Result.SUCCESS:
        logger.info(f"[modrinth]{old_file_name}下载完成")
        return Result.SUCCESS
    
    else: # hash方法不行，直接搜索吧...
        logger.warning("[modrinth]无法通过原模组文件hash值获取适配版本, 尝试通过模组作者进行搜索")
        adapted_ver = modrinth_search(Path(source_dir / old_file_name), mod_loader, target_version)
        if not isinstance(adapted_ver, dict):
            return adapted_ver # 找不到呜;w;...
        
        # 先下载依赖，不过即使其中有一个依赖下载失败，也还是会继续下载模组，但会给玩家一个提示（或者要不直接在这里做个配置选项？
        failed_dps = modrinth_dl_dependencies(adapted_ver, mod_loader, target_version)

        # 下载模组
        try:
            download_url: str = adapted_ver["files"][0]["url"]
            file_name: str = adapted_ver["files"][0]["filename"]
            download_mod(old_file_name, target_dir, download_url, file_name)
            return failed_dps # 只要有依赖下载失败就返回获取失败的依赖list，但不影响本体模组的下载

        except Exception as e:
            logger.error(f"怎么会写入失败呢: {e}")
            return Result.FAILED


def modrinth_update(target_version: str, mod_loader: str, source_dir: str, old_file_name: str, target_dir: str) -> Result | list:
    '''通过向modrinth api post模组jar文件的sha1值获取最新的适配模组'''

    request_body = {
        "loaders": [mod_loader],
        "game_versions": [target_version]
    }
    old_version_file_hash = get_file_hash(f"{source_dir / old_file_name}")
    logger.info(f"{old_file_name}: {old_version_file_hash}")
    
    try:
        response = requests.post(f"https://api.modrinth.com/v2/version_file/{old_version_file_hash}/update", headers=HEADERS, params={"algorithm": "sha1"}, json=request_body, timeout=10)

        if not response.ok:
            if response.status_code == 404:
                logger.warning(f"[modrinth]{old_file_name} 没有适配 {mod_loader} 的 {target_version}")
                return Result.NOT_ADAPTED
            logger.warning("[modrinth]链接炸了或无适配版本")
            return Result.FAILED
        latest_version_json = response.json()

    except TimeoutError:
        logger.warning("[modrinth]加载时间过长")
        return Result.FAILED
    
    except KeyError:
        logger.warning(f"[modrinth]{old_file_name} 没有适配 {target_version}")
        return Result.FAILED

    # 下载模组依赖
    failed_dps = modrinth_dl_dependencies(latest_version_json, mod_loader, target_version)

    # 下载模组
    try:
        download_url: str = latest_version_json["files"][0]["url"]
        file_name: str = latest_version_json["files"][0]["filename"]
        download_mod(old_file_name, target_dir, download_url, file_name)
        return failed_dps # 只要有依赖下载失败就返回获取失败的依赖list，但不影响本体模组的下载

    except Exception as e:
        logger.error(f"怎么会写入失败呢: {e}")
        return Result.FAILED
    
def modrinth_dl_mod_from_ver_dict(version: dict, old_file_name: str, target_dir: str):
    '''根据从modrinth api获取到的版本信息json进行下载'''
    download_url: str = version["files"][0]["url"]
    file_name: str = version["files"][0]["filename"]
    download_mod(old_file_name, target_dir, download_url, file_name)


def modrinth_search(mod_file_path: Path, mod_loader: str, target_version: str) -> dict | Result:
    """
    \n唉呀唉呀,最后还是只能自己找吗?不过嘛,这个搜索是通过模组jar文件里的信息说明文件来判定的.
    \n目前是根据所搜索到的项目的作者,与模组文件备注里的作者名字是否相符,来确定找到与否.
    \n信息文件优先级: fabric.mod.json > mcmod.info
    \n将会返回该模组适配版本的json或状态Result

    Returns:
        dict: 符合条件的模组版本的信息
        Result.NOT_ADAPTED: 没有适配的模组版本
        Result.FAILED: 搜索的时候失败炸了
    """
    try:
        # 打开模组jar文件
        with zipfile.ZipFile(mod_file_path, 'r') as jar:
            files_list = jar.namelist()
            author = None
            name = None

            # 查找fabric.mod.json
            if "fabric.mod.json" in files_list:
                logger.info("解析fabric.mod.json")
                file: dict = json.loads(jar.read("fabric.mod.json").decode('utf-8'))
                author = file['authors'][0]
                name = file['name']

            # 查找mcmod.info
            elif "mcmod.info" in files_list:
                logger.info("解析mcmod.info")
                file: list[dict] = json.loads(jar.read("mcmod.info").decode('utf-8'))
                author = file[0]["authorList"][0]
                name = file[0]['name']

            # 查找neoforge.mod.toml
            elif "META-INF/neoforge.mods.toml" in files_list:
                logger.info("解析META-INF/neoforge.mods.toml")
                content: str = json.loads(jar.read("mcmod.info").decode('utf-8'))
                name = re.search(r'(?<=(modId\s=\s")).*(?=")', content).group(1)
                author = re.split(r',\s*', re.search(r'(?<=(authors\s=\s")).*(?=")', content).group().strip())[0]

    except Exception as e:
        logger.error(f"解析模组 {mod_file_path} 的jar文件时出错: {e}")
        return Result.FAILED
        
    # 有找到作者，开始搜索！
    if author and author != []:
        params={'query': name, 'facets': f"[[\"author: {author}\"],[\"versions: {target_version}\"],[\"categories: {mod_loader}\"]]"}
        logger.info("[modrinth]尝试搜索:\n" + str(params))
        try:
            response = requests.get(
                f"https://api.modrinth.com/v2/search", 
                params=params, 
                timeout=60
            ) # 是的没错，modrinth的关键词搜索有自己一套的格式，双引号还不能换成单引号呜

            if not response.ok:
                if response.status_code == 404:
                    logger.warning(f"[modrinth]{mod_file_path.name} 没有适配 {mod_loader} 的 {target_version}")
                    return Result.NOT_ADAPTED
                logger.warning("[modrinth]链接炸了或无适配版本")
                return Result.FAILED
            result = response.json()

        except TimeoutError:
            logger.info('[modrinth]搜索超时')
            return Result.FAILED
        except KeyError:
            logger.warning(f"[modrinth]{mod_file_path.name} 没有适配 {target_version}")
            return Result.NOT_ADAPTED
        
        if result['hits'] == []:
            logger.warning(f"[modrinth]无法搜索到{mod_file_path}")
            return Result.NOT_ADAPTED
        
        most_relevant_hit = result['hits'][0] # 这里在想要不要加个自定义搜索关联度过滤，不过先能跑再说吧（
        project_id = most_relevant_hit['project_id']

        # 获取到了project_id，接下来获取所有的版本列表
        versions = modrinth_get_version_list(project_id, most_relevant_hit['title'])
        if not isinstance(versions, list):
            return versions # 获取版本失败了，原封不动返回Result枚举
        
        # 过滤得到支持目标版本的最新模组版本
        return modrinth_get_adapted_version(versions, mod_loader, target_version)

def modrinth_get_version_list(project_id: str, project_name: str=None) -> list[dict] | Result:
    """根据该project_id获取该模组所有版本"""
    if not project_name: project_name=project_id

    try:
        response = requests.get(f"https://api.modrinth.com/v2/project/{project_id}/version")

        if not response.ok:
            if response.status_code == 404: # 真假，怎么会有没有任何版本的project（
                logger.warning(f"[modrinth]{project_id}没有任何版本（真假？")
                return Result.NOT_ADAPTED
            logger.warning(f"[modrinth]无法获得{project_id}的详情信息")
            return Result.FAILED
        return response.json()

    except TimeoutError:
        logger.info(f'[modrinth]获取{project_name}的版本列表超时')
        return Result.FAILED

def modrinth_get_adapted_version(versions: list[dict], mod_loader: str, target_version: str) -> dict | Result:    
    '''
    解析从modrinth得到的versions并得到支持目标版本的最新模组版本

    Returns:
        dict: 符合条件的模组版本的信息
        Result.NOT_ADAPTED: 找不到适配版本
    '''
    for ver in versions:
        if ver['loaders'] != mod_loader or target_version not in ver['game_versions']: continue
        
        # 找到匹配的版本了好耶！
        return ver
    return Result.NOT_ADAPTED # 呜找不到适配版本

def modrinth_get_dependencies(version: dict) -> list[dict]:
    """获取该版本所有required级别的依赖列表"""
    dependencies: list[dict] = version["dependencies"]
    dependencies = [d for d in dependencies if d["project_id"] not in ["P7dR8mSH", "qvIfYCYJ"] and d['dependency_type'] == "required"] # 排除fabric api和quilt api

def modrinth_dl_dependencies(version: dict, mod_loader: str, target_version: str, target_dir: str) -> Result | list[str]:
    """
    查找并下载该模组的依赖
        返回对象为Result.SUCCESS, 恭喜全部下载完成！
        返回对象为list[str], 有些依赖库下载失败了...该list里面包含下载失败的依赖名称
    """
    dependencies = modrinth_get_dependencies(version)

    failed_dps = []
    for d in dependencies:
        if v_id:= d['version_id']:
            logger.info(f"[modrinth]正在根据version_id {v_id} 下载依赖")
            result = modrinth_dl_from_version_id(v_id, target_dir)
            if result != Result.SUCCESS: failed_dps.append(result)

        elif p_id:= d['project_id']:
            logger.info(f"[modrinth]正在根据project_id {p_id} 下载依赖")
            result = modrinth_dl_from_project_id(p_id, mod_loader, target_version, target_dir)
            if result != Result.SUCCESS: failed_dps.append(result)

    if failed_dps != []: return failed_dps # 有下载失败的,返回下载失败的列表
    return Result.SUCCESS
            
def modrinth_dl_from_project_id(project_id: str, mod_loader: str, target_version: str, target_dir: str) -> Result:
    """根据project_id获取并下载最新适配的模组版本"""
    try:
        response = requests.get(f"https://api.modrinth.com/v2/project/{project_id}")
        if not response.ok:
            if response.status_code == 404:
                logger.warning(f"[modrinth]无法根据该project_id({project_id})找到模组项目（真的假的？")
                return Result.FAILED
            logger.warning("[modrinth]链接炸了或无适配版本")
            return Result.FAILED
        p_detail = response.json()

    except TimeoutError:
        logger.warning("[modrinth]加载时间过长")
        return Result.FAILED

    # 确认存在此project_id，获取所有版本
    versions = modrinth_get_version_list(project_id, p_detail["title"])
    if versions != []: return versions # 获取版本列表失败时直接返回状态码

    # 得到最新适配的模组版本
    adapted_ver = modrinth_get_adapted_version(versions, mod_loader, target_version)
    if adapted_ver != dict: return adapted_ver # 查询不到适配版本直接返回状态码

    # 开始下载
    filename = adapted_ver['files'][0]['filename']
    try:
        modrinth_dl_mod_from_ver_dict(versions, filename, target_dir)
    except Exception as e:
        logger.error(f"[modrinth]下载{filename}时遇到了其他错误{e}")
        return Result.FAILED


def modrinth_dl_from_version_id(version_id: str, target_dir: str) -> Result:
    """根据提供的version_id下载指定模组版本"""
    # 获取版本详情信息
    try:
        response = requests.get(f"https://api.modrinth.com/v2/version/{version_id}")
        if not response.ok:
            if response.status_code == 404:
                logger.warning(f"[modrinth]无法根据该version_id({version_id})找到模组项目（真的假的？")
                return Result.FAILED
            logger.warning("[modrinth]链接炸了或无适配版本")
            return Result.FAILED
        ver = response.json()
        
    except TimeoutError:
        logger.warning("[modrinth]加载时间过长")
        return Result.FAILED
    
    # 开始下载
    filename = ver["files"][0]["filename"]
    try:
        modrinth_dl_mod_from_ver_dict(ver, filename, target_dir)
    except Exception as e:
        logger.error(f"[modrinth]下载{filename}时遇到了其他错误：{e}")
        return Result.FAILED
    
def download_mod(old_file_name, target_dir, download_url, file_name):
    """
    把with open那一堆东西整合在一起了，错误在外面捕获吧
    不过现在这个缓存功能不适配连同依赖下载的情况，到时候再重构吧
    Args:
        old_file_name: 用于写入已下载模组的缓存
    """
    # 下载模组
    response = requests.get(download_url, stream=True, timeout=(30, 30))
    response.raise_for_status() # 检查请求是否成功
    with open(f"{target_dir / file_name}", 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk: # 过滤掉 keep-alive 结束块
                file.write(chunk)
    logger.info(f"{file_name} 下载完成!")

    # 写入缓存
    with open(f"{target_dir}dl.txt", "a") as f: f.write(f"{old_file_name}\n")

def get_file_hash(file_path, algorithm='sha1'):
    hash_func = getattr(hashlib, algorithm)()
    
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


### 暂时弃用的curseforge，因为Curseforge API的使用必须要用到开发者密钥，但我暂时还不知道怎么隐藏密钥的同时能让玩家能访问API，总不可能我整一个远程服务器发密钥吧（（（
def curseforge(target_version: str, mod_loader: str, resource_dir: str, old_file_name: str, target_dir: str, not_adapt_mods: List[str]):
    curseforge_hash: int = gen_curseforge_hash(resource_dir, old_file_name)
    logger.info(curseforge_hash)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    request_body = {
        "fingerprints": [curseforge_hash]
    }

    try:
        response = requests.post("https://api.curseforge.com/v1/fingerprints/", headers=headers, json=request_body, timeout=60)
        if not response.ok:
            logger.warning("[curseforge]链接炸了或无适配版本")
            return False
        mod_info_json = response.json()
        project_id: str = mod_info_json[0]["id"]
        project_hash: int = mod_info_json[0]["file"]["fileFingerprint"]

        if curseforge_hash != project_hash:
            logger.warning("[curseforge]未找到对应项目")
            return False
        
        logger.info("[curseforge]功能还没做完喵")
        return False

    except TimeoutError:
        logger.warning("[curseforge]加载时间过长")
        return False

    except KeyError:
        logger.warning(f"[curseforge]{old_file_name} 没有适配 {target_version}")
        return False

def murmur_hash2(data: bytes, seed=1):
    import struct

    length = len(data)
    h = seed ^ length
    i = 0

    while i <= length - 4:
        k = struct.unpack('<I', data[i:i+4])[0]
        k *= 0x5BD1E995
        k &= 0xFFFFFFFF
        k ^= k >> 24
        k *= 0x5BD1E995
        k &= 0xFFFFFFFF

        h *= 0x5BD1E995
        h &= 0xFFFFFFFF
        h ^= k

        i += 4

    left = length - i
    if left == 3:
        h ^= data[i] | (data[i+1] << 8) | (data[i+2] << 16)
        h *= 0x5BD1E995
        h &= 0xFFFFFFFF
    elif left == 2:
        h ^= data[i] | (data[i+1] << 8)
        h *= 0x5BD1E995
        h &= 0xFFFFFFFF
    elif left == 1:
        h ^= data[i]
        h *= 0x5BD1E995
        h &= 0xFFFFFFFF

    h ^= h >> 13
    h *= 0x5BD1E995
    h &= 0xFFFFFFFF
    h ^= h >> 15

    return h

def gen_curseforge_hash(source_dir: str, old_file_name: str):
    with open(source_dir / old_file_name, 'rb') as f:
        raw_data = f.read()

    filtered = bytearray()
    for b in raw_data:
        if b not in (9, 10, 13, 32):
            filtered.append(b)

    hash_value = murmur_hash2(filtered)
    return hash_value
