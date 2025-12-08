from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from core.func import resource_path, load_stylesheet
import Animation, ClientLibs

class CollapsibleBox(QtWidgets.QWidget):
    '''
    一个点击展开的选项卡列表
    通过selected信号传递选中选项卡的信息
    因为实现悬浮方法的原因，展开列表是附着于该类对象的parent，所以parent不能为空
    '''
    # 这里的信号的触发直接交给ItemList，就不绑定信号了
    selected = QtCore.Signal(object)

    def __init__(self, text: str, parent=None, fold_when_clicked_item=True):
        super().__init__(parent)
        self.setLayout(QtWidgets.QVBoxLayout())

        # 选项折叠条
        self.selection_bar = CollapsibleBox.SelectionBar(text, self)
        self.layout().addWidget(self.selection_bar)
        # 列表
        self.list = CollapsibleBox.ItemList(self)
        # 调整选项折叠条长度
        self.selection_bar.setMinimumWidth(self.list.width())
        # 关联列表展开与折叠时间
        self.selection_bar.clicked.connect(lambda: self.list.expand() if self.list.is_folded else self.list.fold())
        self.selected.connect(self.set_current_item)
        
        # 其他配置
        if fold_when_clicked_item:
            self.selected.connect(lambda: self.list.fold())
    
    def set_current_item(self, item: 'CollapsibleBox.Item'):
        print(1)
        self.current_item = item

    def add_item(self, text: str, data=None):
        self.list.add_item(text, data)

    def set_text(self, text: str):
        self.selection_bar.set_text(text)

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
            self.icon.setScale(self.text_label.height() / (self.icon.boundingRect().height()*3))
            self.icon.setTransformOriginPoint(self.icon.boundingRect().center())
            
            self.icon_view.scene().addItem(self.icon)
            self.icon_view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.icon_view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.icon_view.setFixedSize(24, self.text_label.height()-16)
            self.icon_view.setFrameShape(QtWidgets.QFrame.NoFrame)
            self.icon_view.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.icon_view.viewport().setAutoFillBackground(False)

            self.layout().addWidget(self.icon_view, 0)
            self.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        def set_text(self, text: str):
            self.text_label.setText(text)
        
        def enterEvent(self, event):
            super().enterEvent(event)

        def leaveEvent(self, event):
            super().leaveEvent(event)

        def mousePressEvent(self, event):
            super().mousePressEvent(event)
            if hasattr(self, 'anim') and self.anim:
                self.anim = Animation.Rotate(self.icon, 180, start_rotation=self.anim.endValue())
            else:
                self.anim = Animation.Rotate(self.icon, 180.0)
            self.clicked.emit()
            self.anim.start()

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
        def __init__(self, parent: 'CollapsibleBox', max_height: int=200, fixed_width: int=240):
            super().__init__(parent.parent())
            self.parent_widget = parent
            self.is_folded = True
            self.max_height = max_height
            self.hover_item = None

            # 连接主类的信号
            self.selected = parent.selected

            # Item容器
            self.container = QtWidgets.QWidget()
            self.container.setLayout(QtWidgets.QVBoxLayout())
            self.container.layout().setSpacing(0)
            self.setFixedWidth(fixed_width)
            self.setWidget(self.container)
            self.setWidgetResizable(True)

            # 设置折叠和展开动画起始点
            parent_abs_pos: QtCore.QPoint = self.mapTo(self.parent_widget.parent(), self.parent_widget.pos())
            self.expand_pos = parent_abs_pos + QtCore.QPoint(10, self.parent_widget.selection_bar.height()+10)
            self.fold_pos = self.expand_pos + QtCore.QPoint(0, -20)

            # 调整位置
            self.move(self.expand_pos)
            self.hide()
            self.fold()

        def expand(self):
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
            self.container.layout().addWidget(item)