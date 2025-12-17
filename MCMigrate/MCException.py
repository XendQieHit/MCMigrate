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
    def __init__(self, msg: str, level: Message.Level):
        super().__init__(msg)
        self.level = level

class VersionsJSONFileError(MCException):
    def __init__(self, reason: str):
        super().__init__("读取versions.json时发生错误: " + reason)

class NoSuchGameFolder(MCException):
    def __init__(self, reason: str=None):
        super().__init__("指定的游戏不存在" if reason is None else reason)

class NoSuchVersion(MCException):
    def __init__(self, reason: str=None):
        super().__init__("指定的版本不存在" if reason is None else reason)