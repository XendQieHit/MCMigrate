from PySide6 import QtWidgets, QtCore, QtGui
from typing import Callable, Dict
from enum import Enum
from dataclasses import dataclass
import sys, logging
from windows.loadStyleSheet import load_stylesheet
from utils.func import resource_path, hex_rgba_to_tuple
from utils.TreeNode import TreeNode
from DisplayMessageable import DisplayMessageable

class Level(Enum):
    INFO = (1, "#5cb7ef", "#34566c5f", "#7bccff2b", "#ffffff")
    DONE = (2, "#5adc5e", "#3068325f", "#80eb832d",  "#38413e")
    WARNING = (3, "#f6e16a", "#8a7d335f", "#f6e16a2d", "#000000")
    ERROR = (4, "#e7612c", "#981b0d5f", "#e7612c2d", "#ffffff")
    
    def __init__(self, num, color, color_bg, color_btn, color_font):
        self.num = num
        self.color = color
        self.color_bg = color_bg
        self.color_btn = color_btn
        self.color_font = color_font

class DialogWindow(QtWidgets.QWidget):
    '''
    直接浮现在窗口中心的问答框
    '''
    closed = QtCore.Signal()
    def __init__(
        self,
        title: str,
        level: Level,
        content_text: str,
        parent_widget: QtWidgets.QWidget,
        *buttons: tuple[str, Level, Callable[[], None]],
        **kwargs
    ):
        super().__init__(parent=parent_widget)
        self.parent_widget = parent_widget
        self.can_not_be_covered = False

        # 设置窗口支持透明
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # 设置自身大小为主窗口大小（作为遮罩容器）
        self.resize(parent_widget.size())

        # 背景遮罩（全屏半透明）
        self.background = QtWidgets.QFrame(self)
        self.background.setGeometry(0, 0, self.width(), self.height())  # 全屏
        self.background.setStyleSheet(f"background-color: rgba{hex_rgba_to_tuple(level.color_bg)}")
        
        # 对话框
        self.dialog_window = QtWidgets.QWidget(self)
        self.dialog_window.setFixedSize(500, 240)
        self.dialog_window.setObjectName("dialogWindow")
        self.dialog_window.setStyleSheet(load_stylesheet(resource_path("qss/dialog.qss")))
        self.dialog_window.setLayout(QtWidgets.QVBoxLayout())
        self.dialog_window.layout().setSpacing(5)
        self.dialog_window.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        self.title_label = QtWidgets.QLabel(title, self.dialog_window)
        self.title_label.setStyleSheet(f"font-size: 18px; background-color: {level.color}; color: {level.color_font}; padding: 5px;")
        self.dialog_window.layout().addWidget(self.title_label)

        # 内容文本
        self.content_text = QtWidgets.QLabel(content_text, self.dialog_window)
        self.content_text.setObjectName("contentText")
        self.content_text.setStyleSheet(load_stylesheet(resource_path("qss/dialog.qss")))
        self.content_text.setMaximumWidth(self.dialog_window.width() - 30)
        self.content_text.setWordWrap(True)
        self.content_text.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)

        # 滚动区域
        self.content_text_view = QtWidgets.QScrollArea(self.dialog_window)
        self.content_text_view.setWidget(self.content_text)
        self.content_text_view.setWidgetResizable(True)
        self.content_text_view.setObjectName('contentTextView')
        self.content_text_view.setStyleSheet(load_stylesheet(resource_path("qss/dialog.qss")))
        self.dialog_window.layout().addWidget(self.content_text_view)

        # 按钮区
        self.dialog_buttons: list[DialogWindow.DialogButton] = []
        self.button_section = QtWidgets.QWidget(self.dialog_window)
        self.button_section.setLayout(QtWidgets.QHBoxLayout())
        self.button_section.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.button_section.setObjectName("buttonSection")
        self.button_section.setStyleSheet(load_stylesheet(resource_path("qss/dialog.qss")))
        self.dialog_window.layout().addWidget(self.button_section, 0)
        # 添加按钮
        if buttons:
            for button_tuple in buttons:
                if button_tuple:
                    self.add_button(button_tuple[0], button_tuple[1], button_tuple[2])
        
        # 添加取消按钮
        if kwargs.get('add_button_cancel', True):            
            self.button_cancel = DialogWindow.DialogButton('取消', Level.INFO, self.close_with_animation)
            self.button_section.layout().addWidget(self.button_cancel)

        # 根据kwargs进行其他额外参数调整
        # 取消按钮的文字
        if text:= kwargs.get('change_cancel_btn_text', False):
            self.button_cancel.setText(text)
        # 点击任意按钮同时关闭问答框
        if kwargs.get('close_when_clicked_any_btn', False):
            for btn in self.dialog_buttons:
                btn.clicked.connect(self.close_with_animation)
        # 不可被新的问答框顶掉
        self.can_not_be_covered = kwargs.get('can_not_be_covered', False)

        # 准备动画展示，先隐藏界面
        self.effect_opacity = QtWidgets.QGraphicsOpacityEffect(opacity=0.0)
        self.setGraphicsEffect(self.effect_opacity)

    def add_button(self, text: str, level: Level, func: Callable[[], None]):
        btn = DialogWindow.DialogButton(text, level, func)
        self.button_section.layout().addWidget(btn)
        self.dialog_buttons.append(btn)
        return btn

    def show_with_animation(self):
        self.show()
        self.raise_()

        # 先将其移到中心，并设为 0 大小
        center = self.rect().center()
        self.dialog_window.move(center.x() - 250, center.y() - 120)  # 初始位置（目标中心）
        self.dialog_window.resize(0, 0)  # 从 0 开始
        self.dialog_window.show()

        # 透明度动画
        self.anim = QtCore.QPropertyAnimation(self.graphicsEffect(), b"opacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        self.anim.start()
    
    def close_with_animation(self):
        
        self.anim = QtCore.QPropertyAnimation(self.graphicsEffect(), b"opacity")
        self.anim.setDuration(100)
        self.anim.setStartValue(self.graphicsEffect().opacity())
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        self.anim.finished.connect(self.close)
        self.anim.start()
    
    def close(self):
        self.closed.emit()
        return super().close()
    
    class DialogButton(QtWidgets.QPushButton):
        def __init__(self, text: str, level: Level, func: Callable[[], None]=None, **kwargs):
            super().__init__(text)
            self.color_bg = hex_rgba_to_tuple(level.color_btn)
            self.hover_text_widget = None
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.setStyleSheet(f"""
                QPushButton {{
                    border: 2px solid {level.color};
                    border-radius: 5px;
                    font-size: 16px;
                    background-color: transparent;
                    color: {level.color};
                    padding: 2px
                }}
                QPushButton:hover {{
                    background-color: rgba{self.color_bg}
                }}
            """)
            if func: self.clicked.connect(func)

            # 根据kwargs进行功能上的调整
            # 悬浮时弹出的文本
            if hover_text:= kwargs.get('hover_text', False):
                self.hover_text_widget = QtWidgets.QLabel(hover_text)
        
        def enterEvent(self, event):
            super().enterEvent(event)
            self.hover_text_widget

class DialogSeries(QtCore.QObject):
    '''
    用于需要一连串问询用户的问答框组
    \n注意！为了知晓问答结束以及获取问答结果的数据，需要手动将finished信号连接到处理数据的函数方法！
    '''
    finished = QtCore.Signal(Dict)
    def __init__(self, beg_dialog_tree: 'DialogTreeNode', parent_widget: QtWidgets.QWidget, process_data: Dict={}):
        super().__init__()
        self.parent_widget = parent_widget
        self.current_dialog_tree = beg_dialog_tree
        self.temp_data: Dict = process_data

    def start(self):
        if not self.current_dialog_tree:
            raise RuntimeError("DialogTreeNode.dialog 为 None, 先用 create_dialog_series_window 创建一个吧")
        self.current_dialog_tree.start() # 开始质问！(?
        self.current_dialog_tree.ended.connect(lambda: self.finished.emit(self.temp_data))

    def set_dialog_tree(self, dialog_tree: 'DialogTreeNode'):
        try:
            self.current_dialog_tree.ended.disconnect()
        except RuntimeError:
            pass  # 未连接过，忽略
        self.current_dialog_tree = dialog_tree
        self.current_dialog_tree.ended.connect(lambda: self.finished.emit(self.temp_data))
        return self.current_dialog_tree

    def create_dialog_tree(self, name):
        self.current_dialog_tree = DialogSeries.DialogTreeNode(name=name, dialog_series=self, parent_widget=self.parent_widget)
        return self.current_dialog_tree

    @dataclass
    class Action:
        '''
        用于标记点击按钮之后的页面操作
        例：
        next_action = Action("NEXT", 3) -> 跳转至第二个子节点（以数组索引的形式）
        end_action = Action("END") -> 结束问答
        stay_action = Action("STAY") -> 保持窗口（其实除上面两个，其他Action都会被仍为时保持窗口
        '''
        type: str  # "NEXT" or "END" 
        jump_index: int = None


    class DialogTreeNode(QtCore.QObject):
        ended = QtCore.Signal()

        def __init__(self, dialog: 'DialogSeries.DialogSeriesWindow'=None, name=None, dialog_series: 'DialogSeries'=None, parent_widget=None):
            super().__init__()  # 必须先调用 QObject.__init__
            self.name = name
            self.dialog = dialog
            self.dialog_series = dialog_series
            self.parent_widget = parent_widget # 将会被展示在的地方
            self.children: list['DialogSeries.DialogTreeNode'] = []  # 自己维护子节点

            if not dialog_series:
                raise RuntimeError("DialogTreeNode 必须有 dialog_series 参数")
            if not parent_widget:
                raise RuntimeError("DialogTreeNode 必须有 parent_widget 参数")

        def create_dialog_series_window(self, title: str, level: Level, content_text: str):
            self.dialog = DialogSeries.DialogSeriesWindow(title, level, content_text, self.parent_widget, self.dialog_series.temp_data)
            return self.dialog

        def add_child(self, child: 'DialogSeries.DialogTreeNode'):
            child.setParent(self)  # 可选：启用 Qt 父子内存管理
            self.children.append(child)
            return child

        def add_dialog_node(self, dialog: DialogWindow, name=None) -> 'DialogSeries.DialogTreeNode':
            new_node = DialogSeries.DialogTreeNode(dialog, name, parent_widget=self.parent_widget)
            self.add_child(new_node)
            return new_node

        def when_button_clicked(self, action: 'DialogSeries.Action'):
            if action.type == "NEXT":
                self.dialog.closed.connect(self.children[action.jump_index].start) # 下一个就是你了口牙！
                self.dialog.close_with_animation()
                
            elif action.type == "END":
                self.dialog.close_with_animation()
                self.ended.emit()

        def start(self):
            self.dialog.show_with_animation()
            self.dialog.func_executed.connect(self.when_button_clicked)
        
        
    class DialogSeriesWindow(DialogWindow):
        func_executed = QtCore.Signal(object) # 其实只能转入Action类，换成object类是因为qt的Signal不支持其他自定义类
        def __init__(
            self,
            title: str,
            level: Level,
            content_text: str,
            parent_widget: QtWidgets.QWidget,
            temp_data: dict
        ):
            super().__init__(title, level, content_text, parent_widget)
            self.temp_data = temp_data
            return self
                
        def add_button(self, text: str, level: Level, action: 'DialogSeries.Action', func_set_value=None, *keys_in_temp_data, **kwargs):
            '''
            添加按钮
            Args:
                action(DialogSeries.Action): 当该按钮被点击时，该DialogSeriesWindow会向所属的DialogSeries发出该action
            '''
            # 设置按钮点击后修改 temp_data 中对应路径的值
            def set_value(data, path, val):
                for key in path[:-1]:
                    data = data[key]
                data[path[-1]] = val

            def func():
                if func_set_value is not None and keys_in_temp_data:
                    set_value(self.temp_data, keys_in_temp_data, func_set_value)
            btn = DialogSeries.DialogSeriesButton(text, level, action, func, **kwargs)
            self.button_section.layout().addWidget(btn)
            self.dialog_buttons.append(btn)
            btn.func_executed.connect(self.func_executed)
            return self

    class DialogSeriesButton(QtWidgets.QPushButton):
        func_executed = QtCore.Signal(object)
        def __init__(self, text: str, level: Level, action: 'DialogSeries.Action', func: Callable[[], None]=None, **kwargs):
            super().__init__(text)
            self.action = action
            self.func = func

            # 让func执行完后才发出信号，让后面的进行action判断，防止数据还没更新就跳转了
            def on_clicked():
                if self.func:
                    self.func()
                self.func_executed.emit(self.action)
            self.clicked.connect(on_clicked)


class Dialog():
    '''
    为前端设计的，能够显示问答框的类
    '''
    def __init__(self, parent_widget=None):
        self.parent_widget = parent_widget
        self.current_dialog: DialogWindow = None
        self.pending_dialog_requests: list[tuple[str, Level, str, QtWidgets.QWidget, tuple, dict]] = []

    def show_dialog(self, title: str, level: Level, content_text: str, *buttons, **kwargs):
        '''
        弹出问答框

        Args:
            button(tuple[str, Dialog.Level, Callable[[], None]]): 按钮 
            change_cancel_btn_text(str): 改变关闭问答框按钮的文字
            close_when_clicked_any_btn(bool): 点击任意按钮就关闭问答框
            can_not_be_cover(bool): 不可被新生成的问答框顶掉，新的问答框会在该问答框关闭后弹出
        '''
        if self.current_dialog:
            if self.current_dialog.can_not_be_covered: # 如果正在展示的问答框无法被覆盖，将该请求移至等待队列pending_dialog_requests

                if self.pending_dialog_requests == []: # 首次添加等待请求，连接更新信号
                    self.current_dialog.closed.connect(self.update_dialog)

                new_dialog_args: tuple = (title, level, content_text, self.parent_widget, buttons, kwargs)
                self.pending_dialog_requests.append(new_dialog_args)
                return
            
            # 顶掉正在展示的问答框
            self.close_and_del_current_dialog()
        
        self.current_dialog = DialogWindow(title, level, content_text, self.parent_widget, *buttons, **kwargs)
        self.current_dialog.show_with_animation()
        return self.current_dialog

    def close_and_del_current_dialog(self):
        self.current_dialog.close()
        self.current_dialog.deleteLater()
        self.current_dialog = None
    
    def update_dialog(self):
        current_dialog_tuple = self.pending_dialog_requests.pop(0)
        self.current_dialog = DialogWindow(current_dialog_tuple[0], current_dialog_tuple[1], current_dialog_tuple[2], current_dialog_tuple[3], *current_dialog_tuple[4], **current_dialog_tuple[5])
        self.current_dialog.show_with_animation()
        # 根据 正在展示窗口的属性 和 是否存在后续请求 来连接更新函数
        if self.current_dialog.can_not_be_covered and self.pending_dialog_requests != []: 
            self.current_dialog.closed.connect(self.update_dialog)

    def ask_in_series(self, dialog_series: DialogSeries, finished_func: Callable[[Dict], None]=None):
        '''
        开始连续问答
        Args:
            finished_func(Callable[[Dict], None): 问答完毕后执行的函数方法，同时向该方法传递问答结果数据dict形参
        '''
        dialog_series.start()
        if finished_func:
            dialog_series.finished.connect(finished_func)

    def gen_a_series(self, name: str, process_data: dict=None):
        '''
        生成一个问答框系列，用于连续问答
        \n使用该方法生成的series将自动创建DialogTreeNode
        Args:
            name(str): 自动创建生成的DialogTreeNode的名字（不过其实也没必要，因为字节点的检索大部分情况下是靠index进行的（倒
            process_data(dict): 问答过程中被记录处理的数据
        '''
        dialog_series = DialogSeries(None, self.parent_widget, process_data)
        dialog_series.create_dialog_tree(name)
        return dialog_series

    def info(self, title: str, content_text: str, *buttons, **kwargs):
        '''
        弹出问答框

        Args:
            button(tuple[str, Dialog.Level, Callable[[], None]]): 按钮 
            change_cancel_btn_text(str): 改变关闭问答框按钮的文字
            close_when_clicked_any_btn(bool): 点击任意按钮就关闭问答框
            can_not_be_covered(bool): 不可被新生成的问答框顶掉，新的问答框会在该问答框关闭后弹出
        '''
        return self.show_dialog(title, Level.INFO, content_text, *buttons, **kwargs)

    def warning(self, title: str, content_text: str, *buttons, **kwargs):
        '''
        弹出问答框

        Args:
            button(tuple[str, Dialog.Level, Callable[[], None]]): 按钮 
            change_cancel_btn_text(str): 改变关闭问答框按钮的文字
            close_when_clicked_any_btn(bool): 点击任意按钮就关闭问答框
            can_not_be_covered(bool): 不可被新生成的问答框顶掉，新的问答框会在该问答框关闭后弹出
        '''
        return self.show_dialog(title, Level.WARNING, content_text, *buttons, **kwargs)

    def error(self, title: str, content_text: str, *buttons, **kwargs):
        '''
        弹出问答框

        Args:
            button(tuple[str, Dialog.Level, Callable[[], None]]): 按钮 
            change_cancel_btn_text(str): 改变关闭问答框按钮的文字
            close_when_clicked_any_btn(bool): 点击任意按钮就关闭问答框
            can_not_be_covered(bool): 不可被新生成的问答框顶掉，新的问答框会在该问答框关闭后弹出
        '''
        return self.show_dialog(title, Level.ERROR, content_text, *buttons, **kwargs)

    def done(self, title: str, content_text: str, *buttons, **kwargs):
        '''
        弹出问答框

        Args:
            button(tuple[str, Dialog.Level, Callable[[], None]]): 按钮 
            change_cancel_btn_text(str): 改变关闭问答框按钮的文字
            close_when_clicked_any_btn(bool): 点击任意按钮就关闭问答框
            can_not_be_covered(bool): 不可被新生成的问答框顶掉，新的问答框会在该问答框关闭后弹出
        '''
        return self.show_dialog(title, Level.DONE, content_text, *buttons, **kwargs)
    
class Dialogable(QtCore.QObject):
    # 只定义 4 个参数：title, level, content, options（包含 buttons + kwargs）
    dialog_requested = QtCore.Signal(str, object, str, object)  # object 可容纳任何 Python 对象
    
    def send_dialog(self, title: str, level, content_text: str, *buttons, **kwargs):
        '''
        弹出问答框

        Args:
            button(tuple[str, Dialog.Level, Callable[[], None]]): 按钮 
            change_cancel_btn_text(str): 改变关闭问答框按钮的文字
            close_when_clicked_any_btn(bool): 点击任意按钮就关闭问答框
            can_not_be_covered(bool): 不可被新生成的问答框顶掉，新的问答框会在该问答框关闭后弹出
        '''
        # 打包所有可变数据到一个 dict（或自定义对象）
        payload = {
            'buttons': buttons,  # tuple of tuples
            'options': kwargs    # 其他配置
        }
        self.dialog_requested.emit(title, level, content_text, payload)