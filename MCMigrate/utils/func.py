# 什么嘛，到头来还是得自己拼功能（
import shutil, sys, os, re
from pathlib import Path

def sort_log_folder(LOG_DIR: str):
    '''清理logs，维持日志文件数量在7个'''
    dir_path = Path(LOG_DIR).iterdir()
    if len(dir_path) <= 7: return
    for item in tuple(dir_path)[:-8]:
        if item.is_file() or item.is_symlink():
            item.unlink()  # 删除文件或符号链接
        elif item.is_dir():
            shutil.rmtree(item)  # 递归删除子文件夹

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
    return os.path.join(os.path.abspath('.'), relative_path)

def hex_rgba_to_tuple(hex_str: str) -> tuple[int, int, int, int]:
    """
    将十六进制 RGBA 字符串转换为 (R, G, B, A) 元组（均为 0–255 的整数）。
    
    支持格式：
      - 8 位: #RRGGBBAA  → 如 "#FF800080"
      - 4 位: #RGBA     → 如 "#F808"（等价于 "#FF880088"）
    
    Args:
        hex_str (str): 十六进制颜色字符串，必须以 '#' 开头
    
    Returns:
        tuple[int, int, int, int]: (R, G, B, A)
    
    Raises:
        ValueError: 格式无效
    """
    hex_str = hex_str.strip()
    if not hex_str.startswith('#'):
        raise ValueError("Hex color must start with '#'")

    hex_part = hex_str[1:]

    # 判断是 4 位还是 8 位
    if len(hex_part) == 4:
        # #RGBA → #RRGGBBAA
        r, g, b, a = hex_part
        hex_part = r + r + g + g + b + b + a + a
    elif len(hex_part) == 8:
        pass  # already #RRGGBBAA
    else:
        raise ValueError(f"Invalid hex RGBA length: {len(hex_part)} (expected 4 or 8)")

    # 检查是否为合法十六进制
    if not re.fullmatch(r"[0-9A-Fa-f]{8}", hex_part):
        raise ValueError(f"Invalid hex characters in: {hex_str}")

    # 解析
    r = int(hex_part[0:2], 16)
    g = int(hex_part[2:4], 16)
    b = int(hex_part[4:6], 16)
    a = int(hex_part[6:8], 16)

    return (r, g, b, a)