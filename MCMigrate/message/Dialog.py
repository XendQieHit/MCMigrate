import sys, logging

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # 单独调试时的代码

from PySide6 import QtWidgets, QtCore, QtGui
from typing import Callable, Dict, Any, Iterable
from enum import Enum
from dataclasses import dataclass
from windows.loadStyleSheet import load_stylesheet
from utils.func import hex_rgba_to_tuple
from core.func import resource_path
import Animation

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
        self.level = level

        # 因为要适配后端创建窗口时无parent_widget的情况，所以把之前需要parent_widget的代码移到update()，在show()的时候再更新
        
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
                    self.add_button(button_tuple[0], button_tuple[1], button_tuple[2], **button_tuple[3] if len(button_tuple) > 3 else {})
        
        # 添加取消按钮
        if kwargs.get('add_button_cancel', True):            
            self.button_cancel = DialogWindow.DialogButton(self, '取消', Level.INFO, self.close_with_animation)
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

    def add_button(self, text: str, level: Level, func: Callable[[], None], **kwargs):
        btn = DialogWindow.DialogButton(self, text, level, func, **kwargs)
        self.button_section.layout().addWidget(btn)
        self.dialog_buttons.append(btn)
        return btn
    
    def render(self): # 因为要适配后端创建窗口时无parent_widget的情况，因此在show时再更新大小
        # 设置窗口支持透明
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # 设置自身大小为主窗口大小（作为遮罩容器）
        self.resize(self.parent_widget.size())

        # 背景遮罩（全屏半透明）
        self.background = QtWidgets.QFrame(self)
        self.background.setGeometry(0, 0, self.width(), self.height())  # 全屏
        self.background.setStyleSheet(f"background-color: rgba{hex_rgba_to_tuple(self.level.color_bg)}")

        self.dialog_window.raise_()

    def show(self):
        self.render()
        super().show()

    def show_with_animation(self):
        self.show()
        self.raise_()

        # 先将其移到中心，并设为 0 大小
        center = self.rect().center()
        self.dialog_window.move(center.x() - 250, center.y() - 120)  # 初始位置（目标中心）
        self.dialog_window.resize(0, 0)  # 从 0 开始
        self.dialog_window.show()

        # 透明度动画
        self.anim = Animation.FadeIn(self)
        self.anim.start()
    
    def close_with_animation(self):
        self.anim = Animation.FadeOut(self)
        self.anim.finished.connect(self.close)
        self.anim.start()
    
    def close(self):
        self.closed.emit()
        return super().close()
    
    class DialogButton(QtWidgets.QPushButton):
        def __init__(self, dialog_window: 'DialogWindow', text: str, level: Level, func: Callable[[], None]=None, **kwargs):
            super().__init__(text)
            self.dialog_window = dialog_window
            self.color_bg = hex_rgba_to_tuple(level.color_btn)
            self.hover_text_widget: DialogWindow.DialogButton.HoverLabel = None
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
                self.hover_text_widget = DialogWindow.DialogButton.HoverLabel(hover_text, self, self.dialog_window)
        
        def enterEvent(self, event):
            super().enterEvent(event)
            if self.hover_text_widget:
                self.hover_text_widget.show_with_anim()
        
        def leaveEvent(self, event):
            super().leaveEvent(event)
            if self.hover_text_widget:
                self.hover_text_widget.hide_with_anim()
        
        class HoverLabel(QtWidgets.QLabel):
            def __init__(self, text: str, button: 'DialogWindow.DialogButton', dialog_window: QtWidgets.QWidget=None):
                super().__init__(text=text, parent=dialog_window.parentWidget())
                if dialog_window:
                    self.parent_widget = dialog_window
                self.button = button
                self.anim = None
                self.setObjectName('hoverText')
                self.setStyleSheet(load_stylesheet(resource_path("qss/dialog.qss")))
                self.adjustSize()

            def show_with_anim(self):
                self.raise_()
                if not self.parent(): self.setParent(self.parent_widget.parentWidget()) # 适配DialogSeriesButton, 防止初始化的时候parent_widget.parentWidget()为None
                self.move(self.button.mapTo(self.parentWidget(), QtCore.QPoint((self.button.width()-self.width())/2, -self.button.height()-2))) # 移动到按钮上方中央
                self.show()
                self.anim = Animation.FadeIn(self, duration=200)
                self.anim.start()

            def hide_with_anim(self):
                self.anim = Animation.FadeOut(self)
                self.anim.finished.connect(self.hide)
                self.anim.start()

class DialogSeries(QtCore.QObject):
    '''
    用于需要一连串问询用户的问答框组
    \n注意！为了知晓问答结束以及获取问答结果的数据，需要手动将finished信号连接到处理数据的函数方法！
    '''
    finished = QtCore.Signal(object)  # 传递问答结果数据 dict 或 list
    def __init__(self, parent_widget: QtWidgets.QWidget, process_data: Dict | list):
        super().__init__(parent=parent_widget)
        self.parent_widget = parent_widget
        self.current_dialog_tree = None
        self.temp_data: Dict | list = process_data
        if not self.temp_data: self.temp_data = {'name': 'hi'}

    def start(self):
        if not self.current_dialog_tree:
            raise RuntimeError("DialogTreeNode.dialog 为 None, 先用 create_dialog_series_window 创建一个吧")
        self.current_dialog_tree.start() # 开始质问！(?

    def set_dialog_tree(self, dialog_tree: 'DialogTreeNode'):
        if self.current_dialog_tree:
            try:
                self.current_dialog_tree.ended.disconnect()
                self.current_dialog_tree.next_to.disconnect()
            except RuntimeError:
                pass  # 未连接过，忽略
        self.current_dialog_tree = dialog_tree
        self.current_dialog_tree.ended.connect(lambda: self.finished.emit(self.temp_data))
        self.current_dialog_tree.next_to.connect(self.next_to)
        logging.info(f"DialogSeries: set current_dialog_tree to {dialog_tree.name}")
        return self.current_dialog_tree
    
    @QtCore.Slot(int)
    def next_to(self, index: int):
        self.set_dialog_tree(self.current_dialog_tree.children[index]).start()

    def create_dialog_tree(self, name=None):
        self.current_dialog_tree = DialogSeries.DialogTreeNode(name=name, dialog_series=self, parent_widget=self.parent_widget)
        return self.set_dialog_tree(self.current_dialog_tree)
        
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

    @dataclass
    class Func:
        '''
        用于标记点击按钮之后要执行的函数（为了能够让DialogButton能够一次性执行多个函数方法
        \n例：
        \nfunc = Func(set_value=True, key_in_temp_data=('osu', 'is_std'))
        \n-> 将 temp_data['osu']['is_std'] 的值设为 True
        Args:
            set_value(Any): 要设置成的值
            key_in_temp_data:(tuple[Any]): 要改变值的键名，当然也支持数组索引
        '''
        set_value: Any = None  # 要设置的值
        key_in_temp_data: tuple = ()  # 要设置值的路径（键名或索引值组成的元组）


    class DialogTreeNode(QtCore.QObject):
        ended = QtCore.Signal()
        next_to = QtCore.Signal(int)

        def __init__(self, dialog: 'DialogSeries.DialogSeriesWindow'=None, name=None, dialog_series: 'DialogSeries'=None, parent_widget=None):
            super().__init__()  # 必须先调用 QObject.__init__
            self.name = name
            self.dialog = dialog
            self.dialog_series = dialog_series
            self.parent_widget = parent_widget # 将会被展示在的地方
            self.children: list['DialogSeries.DialogTreeNode'] = []  # 自己维护子节点

        def create_dialog_series_window(self, title: str, level: Level, content_text: str):
            self.dialog = DialogSeries.DialogSeriesWindow(title, level, content_text, self.parent_widget, self.dialog_series)
            return self.dialog

        def add_child(self, child: 'DialogSeries.DialogTreeNode'):
            child.setParent(self)  # 可选：启用 Qt 父子内存管理
            self.children.append(child)
            return child

        def add_new_dialog_node(self, name=None) -> 'DialogSeries.DialogTreeNode':
            new_node = DialogSeries.DialogTreeNode(name=name, dialog_series=self.dialog_series, parent_widget=self.parent_widget)
            self.add_child(new_node)
            return new_node

        @QtCore.Slot()
        def when_button_clicked(self, action: 'DialogSeries.Action'):
            self.dialog.close_with_animation()
            if action.type.upper() == "NEXT":
                self.dialog.closed.connect(lambda: self.next_to.emit(action.jump_index)) # 下一个就是你了口牙！
                
            elif action.type.upper() == "END":
                self.ended.emit()

        def start(self):
            if not self.dialog_series:
                raise RuntimeError("DialogTreeNode 必须有 dialog_series 参数")
            if not self.parent_widget:
                raise RuntimeError("DialogTreeNode 必须有 parent_widget 参数")
            self.dialog.show_with_animation()
            self.dialog.func_executed.connect(self.when_button_clicked)
        
        def get_child_by_name(self, name: str):
            for c in self.children:
                if c.name == name:
                    return c
            return None
        
    class DialogSeriesWindow(DialogWindow):
        func_executed = QtCore.Signal(object) # 其实只能转入Action类，换成object类是因为qt的Signal不支持其他自定义类
        def __init__(
            self,
            title: str,
            level: Level,
            content_text: str,
            parent_widget: QtWidgets.QWidget,
            series: 'DialogSeries'
        ):
            super().__init__(title, level, content_text, parent_widget, add_button_cancel=False)
            self.temp_data = series.temp_data
                
        def add_button(self, text: str, level: Level, action: 'DialogSeries.Action', *funcs: 'DialogSeries.Func', **kwargs):
            '''
            添加按钮
            Args:
                action(DialogSeries.Action): 当该按钮被点击时，该DialogSeriesWindow会向所属的DialogSeries发出该action
                *funcs(DialogSeries.Func): 对数据进行操作的方法的序列化对象
            '''
            # 设置按钮点击后修改 temp_data 中对应路径的值
            def set_value(data, path, val):
                logging.info(data)
                for key in path[:-1]:
                    data = data[key]
                if isinstance(data, list): # 兼容数组
                    data.append(val)
                else: data[path[-1]] = val

            def exec_funcs():
                for func in funcs:
                    if func.set_value is not None and func.key_in_temp_data:
                        set_value(self.temp_data, func.key_in_temp_data, func.set_value)
            btn = DialogSeries.DialogSeriesButton(self, text, level, action, exec_funcs, **kwargs)
            self.button_section.layout().addWidget(btn)
            self.dialog_buttons.append(btn)
            btn.func_executed.connect(self.func_executed)
            return self

    class DialogSeriesButton(DialogWindow.DialogButton):
        func_executed = QtCore.Signal(object)
        def __init__(self, dialog_window: 'DialogSeries.DialogSeriesWindow', text: str, level: Level, action: 'DialogSeries.Action', func: Callable[[], None]=None, **kwargs):
            # 让func执行完后才发出信号，让后面的进行action判断，防止数据还没更新就跳转了
            def on_clicked():
                if self.func:
                    self.func()
                self.func_executed.emit(self.action)
            super().__init__(dialog_window, text, level, **kwargs)
            self.action = action
            self.func = func

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
            dialog_series(DialogSeries): 问答框系列，之后要执行的对话流程操作主要在这进行
            finished_func(Callable[[Dict], None): 问答完毕后执行的函数方法，同时向该方法传递问答结果数据dict形参
        '''
        i=0
        if dialog_series.parent_widget == None: # 后端发出出来的窗口没有parent_widget，只能先递归修正了
            dialog_series.setParent(self.parent_widget)
            def set_parent_widget(dialog_node: DialogSeries.DialogTreeNode):
                logging.info(i)
                dialog_node.setParent(self.parent_widget)
                dialog_node.dialog.setParent(self.parent_widget)
                dialog_node.parent_widget = self.parent_widget
                dialog_node.dialog.parent_widget = self.parent_widget
                if dialog_node.children != []:
                    for child in dialog_node.children:
                        set_parent_widget(child)
            set_parent_widget(dialog_series.current_dialog_tree)
        if finished_func:
            dialog_series.finished.connect(finished_func)
        dialog_series.start()

    def gen_a_series(self, name: str, process_data: dict | list=None):
        '''
        生成一个问答框系列，用于连续问答
        \n使用该方法生成的series将自动创建DialogTreeNode
        Args:
            name(str): 自动创建生成的DialogTreeNode的名字（不过其实也没必要，因为字节点的检索大部分情况下是靠index进行的（倒
            process_data(dict): 问答过程中被记录处理的数据
        '''
        dialog_series = DialogSeries(self.parent_widget, process_data)
        dialog_series.create_dialog_tree(name)
        return dialog_series

    def info(self, title: str, content_text: str, *buttons, **kwargs):
        '''
        弹出问答框

        Args:
            button(tuple[str, Dialog.Level, Callable[[], None]], dict): 按钮，dict作为**kwargs
            change_cancel_btn_text(str): 改变关闭问答框按钮的文字
            close_when_clicked_any_btn(bool): 点击任意按钮就关闭问答框
            can_not_be_covered(bool): 不可被新生成的问答框顶掉，新的问答框会在该问答框关闭后弹出
        '''
        return self.show_dialog(title, Level.INFO, content_text, *buttons, **kwargs)

    def warning(self, title: str, content_text: str, *buttons, **kwargs):
        '''
        弹出问答框

        Args:
            button(tuple[str, Dialog.Level, Callable[[], None]], dict): 按钮，dict作为**kwargs
            change_cancel_btn_text(str): 改变关闭问答框按钮的文字
            close_when_clicked_any_btn(bool): 点击任意按钮就关闭问答框
            can_not_be_covered(bool): 不可被新生成的问答框顶掉，新的问答框会在该问答框关闭后弹出
        '''
        return self.show_dialog(title, Level.WARNING, content_text, *buttons, **kwargs)

    def error(self, title: str, content_text: str, *buttons, **kwargs):
        '''
        弹出问答框

        Args:
            button(tuple[str, Dialog.Level, Callable[[], None]], dict): 按钮，dict作为**kwargs
            change_cancel_btn_text(str): 改变关闭问答框按钮的文字
            close_when_clicked_any_btn(bool): 点击任意按钮就关闭问答框
            can_not_be_covered(bool): 不可被新生成的问答框顶掉，新的问答框会在该问答框关闭后弹出
        '''
        return self.show_dialog(title, Level.ERROR, content_text, *buttons, **kwargs)

    def done(self, title: str, content_text: str, *buttons, **kwargs):
        '''
        弹出问答框

        Args:
            button(tuple[str, Dialog.Level, Callable[[], None]], dict): 按钮，dict作为**kwargs
            change_cancel_btn_text(str): 改变关闭问答框按钮的文字
            close_when_clicked_any_btn(bool): 点击任意按钮就关闭问答框
            can_not_be_covered(bool): 不可被新生成的问答框顶掉，新的问答框会在该问答框关闭后弹出
        '''
        return self.show_dialog(title, Level.DONE, content_text, *buttons, **kwargs)
    
class Dialogable(QtCore.QObject):
    '''
    用于后端的，对前端发送问答框请求的类
    \n在使用之前，需要将dialog_requested信号连接到前端的Dialog.show_dialog槽函数中
    '''
    # 只定义 4 个参数：title, level, content, options（包含 buttons + kwargs）
    dialog_requested = QtCore.Signal(str, object, str, object)
    dialog_series_requested = QtCore.Signal(object, object) # dialog_series, finished_func
    get_widget = QtCore.Signal(object)  # 用于获取父窗口的信号，传递一个 Callable[[QtWidgets.QWidget], None] 类型的参数

    def send_dialog(self, title: str, level, content_text: str, *buttons, **kwargs):
        '''
        弹出问答框

        Args:
            button(tuple[str, Dialog.Level, Callable[[], None]], dict): 按钮，dict作为**kwargs
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

    def ask_in_series(self, dialog_series: DialogSeries, finished_func: Callable[[Dict], None]=None):
        '''
        开始连续问答
        Args:
            dialog_series(DialogSeries): 问答框系列，之后要执行的对话流程操作主要在这进行
            finished_func(Callable[[Dict], None): 问答完毕后执行的函数方法，同时向该方法传递问答结果数据dict形参
        '''
        self.dialog_series_requested.emit(dialog_series, finished_func)

    def gen_a_series(self, name: str, process_data: dict | list=None):
        '''
        生成一个问答框系列，用于连续问答
        \n使用该方法生成的series将自动创建DialogTreeNode
        \n因为后端无法获取当前对话框的前端载体，只能在调用前端ask_in_series时再修正parent_widget
        Args:
            name(str): 自动创建生成的DialogTreeNode的名字（不过其实也没必要，因为字节点的检索大部分情况下是靠index进行的（倒
            process_data(dict): 问答过程中被记录处理的数据
        '''
        dialog_series = DialogSeries(parent_widget=None, process_data=process_data)
        dialog_series.create_dialog_tree(name)
        return dialog_series