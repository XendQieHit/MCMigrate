from pathlib import Path
import os, sys, shutil, logging

def clean_log_folder(LOG_DIR: str):
    '''清理logs，维持日志文件数量在7个'''
    dir_path = tuple(Path(LOG_DIR).iterdir())
    if len(dir_path) <= 7: return
    for item in dir_path[:-8]:
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

def load_stylesheet(path):
    '''根据路径读取指定qss文件里的样式'''
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"加载样式表失败: {e}")
        return ""