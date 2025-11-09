# 什么嘛，到头来还是得自己拼功能（
import shutil, sys, os
from pathlib import Path

def clear_folder(folder: Path):
    """清空文件夹内容，但保留文件夹本身"""
    for item in folder.iterdir():
        if item.is_file() or item.is_symlink():
            item.unlink()  # 删除文件或符号链接
        elif item.is_dir():
            shutil.rmtree(item)  # 递归删除子文件夹

def resource_path(relative_path):
    """获取资源文件的绝对路径（兼容打包后）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后，资源在 _MEIPASS 临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)