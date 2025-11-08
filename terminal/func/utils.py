# 什么嘛，到头来还是得自己拼功能（
import shutil
from pathlib import Path

def clear_folder(folder: Path):
    """清空文件夹内容，但保留文件夹本身"""
    for item in folder.iterdir():
        if item.is_file() or item.is_symlink():
            item.unlink()  # 删除文件或符号链接
        elif item.is_dir():
            shutil.rmtree(item)  # 递归删除子文件夹