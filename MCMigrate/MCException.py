from message import Message

class MCException(Exception):
    def __init__(self, *args):
        super().__init__(*args)

class NotMCGameFolder(MCException):
    def __init__(self):
        super().__init__("查找不到.minecraft或游戏文件夹，请检查是否正确选取导入")

class VersionParseError(MCException):
    def __init__(self):
        super().__init__("解析版本失败")

class VersionsFolderNotFound(MCException):
    def __init__(self):
        super().__init__("未发现versions文件夹，还没下游戏吗...?")

class VersionVerifyFailed(MCException):
    def __init__(self, msg, level):
        super().__init__(msg)
        self.level = level