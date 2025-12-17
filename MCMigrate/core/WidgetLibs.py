import time
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from core.func import resource_path, load_stylesheet
from windows.MainWindow import MainWindow
from pathlib import Path
from core import ClientLibs
import Animation

class CollapsibleBox(QtWidgets.QWidget):
    '''
    一个点击展开的选项卡列表
    通过selected信号传递选中选项卡的信息
    因为实现悬浮方法的原因，展开列表是附着于该类对象的parent，所以parent不能为空
    Args:
        text(str): 选项栏默认的文本
        main_window(MainWindow): 所展示在的MainWindow, 主要用于点击列表之外的区域时，自动折叠列表，若不传入则不会实现自动折叠列表功能
    '''
    # 这里的信号的触发直接交给ItemList，就不绑定信号了
    # 来自后来的MC_XQH，还是给用selected信号，来给CollapsibleBox加个current_item吧
    selected = QtCore.Signal(object)

    def __init__(self, text: str, parent=None, main_window: MainWindow=None, fold_when_clicked_item=True):
        super().__init__(parent)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(0)

        # 选项折叠条
        self.selection_bar = CollapsibleBox.SelectionBar(text, self)
        self.layout().addWidget(self.selection_bar)
        # 列表
        self.list = CollapsibleBox.ItemList(self, main_window=main_window)
        # 当前选中项
        self.current_item: 'CollapsibleBox.Item' = None
        self.selected.connect(lambda item: setattr(self, 'current_item', item))
        # 调整选项折叠条长度
        self.selection_bar.setMinimumWidth(self.list.width())
        # 关联列表展开与折叠时间
        self.selection_bar.clicked.connect(lambda: self.list.expand() if self.list.is_folded else self.list.fold())
        self.selected.connect(self.set_current_item)
        
        # 其他配置
        if fold_when_clicked_item:
            self.selected.connect(lambda: self.list.fold())
            self.selected.connect(lambda: self.selection_bar.rotate_icon())

    def get_items_text(self) -> list[str]:
        return self.list.items_text
    
    def get_items_data(self) -> list[object]:
        return self.list.items_data
    
    def set_current_item(self, item: 'CollapsibleBox.Item'):
        self.current_item = item

    def add_item(self, text: str, data=None):
        self.list.add_item(text, data)

    def set_text(self, text: str):
        self.selection_bar.set_text(text)

    def clear_items(self):
        self.list.clear()

    class SelectionBar(QtWidgets.QFrame):
        clicked = QtCore.Signal()
        def __init__(self, text: str, parent):
            super().__init__(parent)
            self.setObjectName('selection_bar')
            self.setStyleSheet(load_stylesheet(resource_path('qss/collapsible_box.qss')))
            self.setLayout(QtWidgets.QHBoxLayout())
            self.layout().setContentsMargins(5,5,5,5)

            # 文本
            self.text_label = QtWidgets.QLabel(text, self)
            self.setMaximumHeight(self.text_label.height())
            self.layout().addWidget(self.text_label, 1)
            self.layout().addStretch()
            # 小图标
            self.icon_view = QtWidgets.QGraphicsView(self)
            self.icon_view.setScene(QtWidgets.QGraphicsScene())
            self.icon = QGraphicsSvgItem(resource_path("assets/section_fold.svg"))
            self.icon_view.scene().addItem(self.icon)
            # 图标大小
            font_height = self.fontMetrics().height()
            icon_height = max(12, font_height - 4)
            scale = icon_height / self.icon.boundingRect().height()
            self.icon.setScale(scale)
            # 图标旋转中心
            self.icon.setTransformOriginPoint(self.icon.boundingRect().center())
            # 图标view设置
            self.icon_view.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed
            )
            self.icon_view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.icon_view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.icon_view.setFixedSize(24, self.text_label.height()-16)
            self.icon_view.setFrameShape(QtWidgets.QFrame.NoFrame)
            self.icon_view.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.icon_view.viewport().setAutoFillBackground(False)
            self.icon_view.adjustSize()

            self.layout().addWidget(self.icon_view, 0)
            self.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            self.adjustSize()

        def set_text(self, text: str):
            self.text_label.setText(text)
        
        def enterEvent(self, event):
            super().enterEvent(event)

        def leaveEvent(self, event):
            super().leaveEvent(event)

        def mousePressEvent(self, event):
            super().mousePressEvent(event)
            self.clicked.emit()
            self.rotate_icon()

        def rotate_icon(self):
            if hasattr(self, 'anim') and self.anim:
                self.anim = Animation.Rotate(self.icon, 180, start_rotation=self.anim.endValue())
            else:
                self.anim = Animation.Rotate(self.icon, 180.0)
            self.anim.start()

        def paintEvent(self, arg__1):
            super().paintEvent(arg__1)

    class Item(QtWidgets.QWidget):
        def __init__(self, text: str, data, parent: 'CollapsibleBox.ItemList'=None):
            super().__init__(parent)
            self.data = data
            self.parent_list = parent
            self.setLayout(QtWidgets.QHBoxLayout())
            self.text = QtWidgets.QLabel(text, self)
            self.text.setStyleSheet("font-size: 14px")
            self.setAutoFillBackground(True)
            self.layout().addWidget(self.text)
            self.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        
        def mousePressEvent(self, event):
            super().mousePressEvent(event)
            self.parent_list.selected.emit(self)

            # 动画部分
            self.anim = QtCore.QSequentialAnimationGroup()
            self.anim.addAnimation(Animation.ChangeColor(self, QtGui.QColor("#6FCBC7"), color_role=self.backgroundRole(), duration=100))  
            self.anim.addPause(120)
            self.anim.addAnimation(Animation.ChangeColor(self, QtGui.QColor("#89E1DD"), color_role=self.backgroundRole(), duration=60))
            self.anim.start()

        def enterEvent(self, event):
            super().enterEvent(event)
            self.parent_list.hover_item = self
            self.anim = Animation.ChangeColor(self, QtGui.QColor("#89E1DD"), color_role=self.backgroundRole(), duration=100)
            self.anim.start()
            
        def leaveEvent(self, event):
            super().leaveEvent(event)
            if self.parent_list.hover_item == self:
                self.parent_list.hover_item = None
            self.anim = Animation.ChangeColor(self, QtGui.QColor('#ffffff'), color_role=self.backgroundRole(), duration=100)
            self.anim.start()
    
    class ItemList(QtWidgets.QScrollArea):
        CLICKED_INTERVAL = 0.1 # 100ms点击间隔限制
        def __init__(self, parent: 'CollapsibleBox', max_height: int=200, fixed_width: int=240, main_window: MainWindow=None):
            super().__init__(parent.parent())
            self.parent_widget = parent
            self.is_folded = True
            self.max_height = max_height
            self.hover_item = None
            self.items: list[CollapsibleBox.Item] = []
            self.items_text: list[str] = []
            self.items_data: list[object] = []

            # 连接主类的信号
            self.selected = parent.selected

            # Item容器
            self.container = QtWidgets.QWidget()
            self.container.setLayout(QtWidgets.QVBoxLayout())
            self.container.layout().setSpacing(0)
            self.setFixedHeight(self.max_height)
            self.setFixedWidth(fixed_width)
            self.setWidget(self.container)
            self.setWidgetResizable(True)

            # 设置折叠和展开动画起始点
            self.parent_abs_pos: QtCore.QPoint = self.mapTo(self.parent_widget.parent(), self.parent_widget.pos())
            self.expand_pos = self.parent_abs_pos + QtCore.QPoint(self.parent_widget.selection_bar.width()-self.width()-10, self.parent_widget.selection_bar.height()+10)
            self.fold_pos = self.expand_pos + QtCore.QPoint(0, -20)

            # 点击列表之外的地方，自动折叠列表
            if main_window:
                self.latest_clicked_time = time.time()
                # 判断全局坐标是否在本列表（含滚动内容）的可视区域内
                def global_click_event(event: QtGui.QMouseEvent):
                    if not self.isVisible():
                        return

                    # 将全局坐标转换为本 widget 的局部坐标
                    pos_in_list = self.mapFromGlobal(event.globalPos())
                    pos_in_bar = parent.selection_bar.mapFromGlobal(event.globalPos())
                    current_time = time.time()
                    d = current_time - self.latest_clicked_time
                    if not self.rect().contains(pos_in_list) and not parent.selection_bar.rect().contains(pos_in_bar) and (d >= self.CLICKED_INTERVAL):
                        self.fold()
                        parent.selection_bar.rotate_icon()
                        self.latest_clicked_time = current_time

                main_window.add_global_click_event(global_click_event)
                self.destroyed.connect(lambda: main_window.remove_global_click_event(global_click_event))

            # 调整位置
            self.move(self.expand_pos)
            self.hide()
            self.fold()

        def expand(self):
            self.expand_pos = self.parent_abs_pos + QtCore.QPoint(self.parent_widget.selection_bar.width()-self.width()-10, self.parent_widget.selection_bar.height()+10)
            self.fold_pos = self.expand_pos + QtCore.QPoint(0, -20)

            self.raise_()
            self.show()
            self.is_folded = False
            self.anim_move_in = QtCore.QPropertyAnimation(self, b'pos')
            self.anim_move_in.setDuration(100)
            self.anim_move_in.setStartValue(self.fold_pos)
            self.anim_move_in.setEndValue(self.expand_pos)
            self.anim = QtCore.QParallelAnimationGroup()
            self.anim.addAnimation(self.anim_move_in)
            self.anim.addAnimation(Animation.FadeIn(self,90))
            self.anim.start()

        def fold(self):
            self.is_folded = True
            self.anim_move_out = QtCore.QPropertyAnimation(self, b'pos')
            self.anim_move_out.setDuration(100)
            self.anim_move_out.setEndValue(self.fold_pos)
            self.anim = QtCore.QParallelAnimationGroup()
            self.anim.addAnimation(self.anim_move_out)
            self.anim.addAnimation(Animation.FadeOut(self))
            self.anim.finished.connect(self.hide)
            self.anim.start()

        def add_item(self, text: str, data=None):
            item = CollapsibleBox.Item(text, data, self)
            self.items.append(item)
            self.items_text.append(text)
            self.items_data.append(data)
            self.container.layout().addWidget(item)
        
        def clear(self):
            '''清空所有选项'''
            for i in reversed(range(self.container.layout().count())):
                widget_to_remove = self.container.layout().itemAt(i).widget()
                self.container.layout().removeWidget(widget_to_remove)
                widget_to_remove.setParent(None)

class TransparentColorButton(QtWidgets.QPushButton):
    def __init__(self, theme_color: QtGui.QColor, clicked_color: QtGui.QColor, icon_path: str | Path, tool_tips: str, parent=None):
        super().__init__(parent)
        self.theme_color = theme_color
        self.clicked_color = clicked_color
        self.default_color = self.palette().color(QtGui.QPalette.ColorRole.Button)
        self.icon_size = min(self.height(), self.width())
        self.icon_gen = ClientLibs.ColorIconGenerator(icon_path, theme_color)
        self.setToolTip(tool_tips)
        self.setIcon(self.icon_gen.icon(QtCore.QSize(self.icon_size, self.icon_size), self.theme_color))
        self.setContentsMargins(0,0,0,0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.anim_btn = Animation.ChangeColor(self, QtGui.QColor(self.theme_color), duration=120, color_role=QtGui.QPalette.ColorRole.Button)
        self.anim_icon = Animation.ChangeButtonIconColorTransiting(self, self.icon_gen, QtGui.QColor(self.default_color), duration=120)
        self.anim = QtCore.QParallelAnimationGroup()
        self.anim.addAnimation(self.anim_btn)
        self.anim.addAnimation(self.anim_icon)
        self.anim.start()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.anim_btn = Animation.ChangeColor(self, QtGui.QColor(self.default_color), duration=120, color_role=QtGui.QPalette.ColorRole.Button)
        self.anim_icon = Animation.ChangeButtonIconColorTransiting(self, self.icon_gen, QtGui.QColor(self.theme_color), duration=120)
        self.anim = QtCore.QParallelAnimationGroup()
        self.anim.addAnimation(self.anim_btn)
        self.anim.addAnimation(self.anim_icon)
        self.anim.start()

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        self.anim = QtCore.QSequentialAnimationGroup()
        self.anim.addAnimation(Animation.ChangeColor(self, self.clicked_color, color_role=QtGui.QPalette.ColorRole.Button, duration=100))  
        self.anim.addPause(120)
        self.anim.addAnimation(Animation.ChangeColor(self, self.theme_color, color_role=QtGui.QPalette.ColorRole.Button, duration=60))
        self.anim.start()