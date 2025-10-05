from typing import List
import requests, hashlib

def modrinth(target_version: str, mod_loader: str, source_dir: str, old_file_name: str, target_dir: str, not_adapt_mods: List[str]):
    headers = {
        "User_Agent": "application/json"
    }
    request_body = {
        "loaders": [mod_loader],
        "game_versions": [target_version]
    }
    print(f"headers: {headers}\nrequest_body: {request_body}")

    # 获取该mod文件的hash值，通过modrinth api的Lastest version of project from hash接口，获取目标mc版本中，最新的mod版本
    old_version_file_hash = get_file_hash(f"{source_dir / old_file_name}")
    try:
        respone = requests.post(f"https://api.modrinth.com/v2/version_file/{old_version_file_hash}/update", headers=headers, params={"algorithm": "sha1"}, json=request_body)

        if not respone.ok: # 情况一，无适配版本
            print("[modrinth]链接炸了或无适配版本")
            return False
        latest_version_json = respone.json()

    except TimeoutError: # 情况二，加载时间过长
        print("[modrinth]加载时间过长")
        return False
    
    except KeyError:
        # 寄啦！找不到字段！没有适配
        print(f"[modrinth]{old_file_name} 没有适配 {target_version}")
        return False

    # 通过查询是否存在"files"字段来判断适配情况
    try:
        print(latest_version_json)
        download_url: str = latest_version_json["files"][0]["url"]
        file_name: str = latest_version_json["files"][0]["filename"]
        # 检索成功！
        with open(f"{target_dir / file_name}", 'wb') as file:
            file.write(requests.get(download_url).content)
            print(f"{file_name} 下载完成!")
        # 记入已下载名录缓存
        with open(f"{target_dir}dl.txt", "a") as f: f.write(f"{old_file_name}\n")
        return True

    except:
        print("怎么会写入失败呢")
        return False


def curseforge(target_version: str, mod_loader: str, resource_dir: str, old_file_name: str, target_dir: str, not_adapt_mods: List[str]):
    # 通过获取文件对应的Fingerprint，来获取改模组的工程id
    curseforge_hash: int = gen_curseforge_hash(resource_dir, old_file_name)
    print(curseforge_hash)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    request_body = {
    "fingerprints": [curseforge_hash]
    }

    try:
        response = requests.post("https://api.curseforge.com/v1/fingerprints/", headers=headers, json=request_body)
        if not response.ok: # 情况一，无适配版本
            print("[curseforge]链接炸了或无适配版本")
            return False
        mod_info_json = response.json()
        project_id: str = mod_info_json[0]["id"]
        project_hash: int = mod_info_json[0]["file"]["fileFingerprint"]

        if curseforge_hash != project_hash:
            print("[curseforge]未找到对应项目")
            return False
        
        print("[curseforge]功能还没昨晚喵")
        return False


    except TimeoutError: # 情况二，加载时间过长
        print("[curseforge]加载时间过长")
        return False

    except KeyError:
        # 寄啦！找不到字段！没有适配
        print(f"[curseforge]{old_file_name} 没有适配 {target_version}")
        return False

    return False

def murmur_hash2(data: bytes, seed=1): # md怎么还有自己的hash算法
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

    # Handle the last few bytes
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
        while chunk := f.read(8192):  # 每次读取 8KB
            hash_func.update(chunk)
    
    return hash_func.hexdigest()

def gen_curseforge_hash(source_dir: str, old_file_name: str):
    # 读取文件并过滤空白字符
    with open(source_dir / old_file_name, 'rb') as f:
        raw_data = f.read()

    filtered = bytearray()
    for b in raw_data:
        if b not in (9, 10, 13, 32):  # 跳过 Tab、LF、CR、Space
            filtered.append(b)

    hash_value = murmur_hash2(filtered)
    return hash_value
