from pathlib import Path
from typing import Any
import yaml, os, logging
from message import Message
from terminal.func.utils import resource_path

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

message = Message.Messageable(logger)

CONFIG_PATH = Path('config.yml')

default_config = {
        'migrate':{
            'file': {
                'copy_option': 'keep'
            },
            'filter_rule': 'excludes',
            'excludes': [
                'assets',
                'data',
                'debug',
                'libraries',
                'logs',
                'NVIDIA',
                'PCL',
                'versions'
            ]
        }
    }
def config_exist() -> bool:
    return CONFIG_PATH.exists() and CONFIG_PATH.stat().st_size > 0

def check_and_fix() -> dict:
    '''检测并修复配置文件的完整性'''
    if not config_exist():
        gen_default_config()
        return default_config.copy()

    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError):
        gen_default_config()
        return default_config.copy()

    def check_unit(target: dict, sample: dict) -> dict:
        # 1. 补全缺失的键
        for key, default_val in sample.items():
            if key not in target:
                target[key] = default_val

        # 2. 修正类型错误 & 递归修复子 dict
        for key, current_val in list(target.items()):
            if key not in sample:
                continue  # 可选：保留用户自定义字段，或 del target[key]
            
            expected_val = sample[key]
            expected_type = type(expected_val)

            # 如果期望的是 dict，且当前值也是 dict → 递归修复
            if isinstance(expected_val, dict):
                if isinstance(current_val, dict):
                    target[key] = check_unit(current_val, expected_val)
                else:
                    # 类型不符，恢复默认 dict
                    target[key] = expected_val.copy()  # 避免引用问题
            else:
                # 期望的是非 dict（如 bool, str, list）
                if not isinstance(current_val, expected_type):
                    target[key] = expected_val  # 恢复默认值

        return target

    fixed_config = check_unit(config, default_config)

    # 将修复后的配置写回文件
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(fixed_config, f, allow_unicode=True, default_flow_style=False, indent=2)

    return fixed_config

def gen_default_config():
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False, indent=2)

def get_config() -> dict:
    if not config_exist():
        gen_default_config()
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error('读取配置文件时出现错误：' + e)

def get_config_value(*keys: str) -> Any | None:
    """
    获取配置值，支持多级嵌套访问。
    
    示例：
        get_config_dict("migrate") 
        get_config_dict("migrate", "excludes")
        get_config_dict("migrate", "excludes", 0)  # 也支持索引（但需确保是 list）
    """
    if not keys:
        return None

    try:
        if not config_exist():
            gen_default_config()
        
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        current = config
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and isinstance(key, int):
                current = current[key] if 0 <= key < len(current) else None
            else:
                return None  # 无法继续深入
            if current is None:
                break
        return current

    except (OSError, yaml.YAMLError) as e:
        logger.error(f"读取配置文件失败：{e}，正在重新生成初始配置文件")
        fixed_config = check_and_fix()
        # 递归调用自己（此时文件已修复）
        return get_config_value(*keys)