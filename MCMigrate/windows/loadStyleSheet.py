import logging

def load_stylesheet(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"加载样式表失败: {e}")
        return ""