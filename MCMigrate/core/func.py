from pathlib import Path
import os, sys, shutil, logging, json

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
    
def get_app_state() -> dict:
    '''获取用户上次关闭程序时的窗口状态'''
    try:
        with open('app_state.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return new_app_state()
    
def new_app_state() -> dict:
    '''生成初始的app_state.json文件'''
    default_state = {
        "migrate": {
            "window_size": [1024, 768],
            "splitter_state": None,
            "latest_game_folder_path": None
        }
    }
    with open('app_state.json', 'w', encoding='utf-8') as f:
        json.dump(default_state, f, indent=4)
    return default_state

def save_app_state(state: dict):
    '''保存当前窗口状态到app_state.json'''
    with open('app_state.json', 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4)

def modify_app_state(value, *keys):
    '''修改app_state.json中的指定键值'''
    state = get_app_state()
    current = state
    for key in keys[:-1]:
        current = current[key]
    current[keys[-1]] = value
    save_app_state(state)