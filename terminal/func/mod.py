from typing import List
import requests, hashlib, logging
from message import Message

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

message = Message.Messageable(logger)


# 主要功能方法

def modrinth(target_version: str, mod_loader: str, source_dir: str, old_file_name: str, target_dir: str, not_adapt_mods: List[str]):
    headers = {
        "User_Agent": "application/json"
    }
    request_body = {
        "loaders": [mod_loader],
        "game_versions": [target_version]
    }
    old_version_file_hash = get_file_hash(f"{source_dir / old_file_name}")
    logger.info(f"{old_file_name}: {old_version_file_hash}")
    
    try:
        respone = requests.post(f"https://api.modrinth.com/v2/version_file/{old_version_file_hash}/update", headers=headers, params={"algorithm": "sha1"}, json=request_body, timeout=120)

        if not respone.ok:
            logger.warning("[modrinth]链接炸了或无适配版本")
            return False
        latest_version_json = respone.json()

    except TimeoutError:
        logger.warning("[modrinth]加载时间过长")
        return False
    
    except KeyError:
        logger.warning(f"[modrinth]{old_file_name} 没有适配 {target_version}")
        return False

    try:
        logger.info(latest_version_json)
        download_url: str = latest_version_json["files"][0]["url"]
        file_name: str = latest_version_json["files"][0]["filename"]
        with open(f"{target_dir / file_name}", 'wb') as file:
            file.write(requests.get(download_url).content)
            logger.info(f"{file_name} 下载完成!")
        with open(f"{target_dir}dl.txt", "a") as f: f.write(f"{old_file_name}\n")
        return True

    except Exception as e:
        logger.error(f"怎么会写入失败呢: {e}")
        return False

# Curseforge API的使用必须要用到开发者密钥，但我暂时还不知道怎么隐藏密钥的同时能让玩家能访问API，总不可能我整一个远程服务器发密钥吧（（（
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

def get_file_hash(file_path, algorithm='sha1'):
    hash_func = getattr(hashlib, algorithm)()
    
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()

def gen_curseforge_hash(source_dir: str, old_file_name: str):
    with open(source_dir / old_file_name, 'rb') as f:
        raw_data = f.read()

    filtered = bytearray()
    for b in raw_data:
        if b not in (9, 10, 13, 32):
            filtered.append(b)

    hash_value = murmur_hash2(filtered)
    return hash_value
