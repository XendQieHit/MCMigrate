from PySide6 import QtGui, QtCore
from PySide6.QtSvg import QSvgRenderer
import re

def get_icon_average_color(icon: QtGui.QIcon, size=32) -> QtGui.QColor:
    """
    获取 QIcon 在指定尺寸下的平均非透明像素颜色。
    """
    # 1. 生成 QPixmap（使用 normal 状态和 normal 模式）
    pixmap = icon.pixmap(size, size)
    
    # 2. 转为 QImage
    image = pixmap.toImage()
    
    if image.isNull():
        return QtGui.QColor()  # 无效图像返回透明色

    total_r = total_g = total_b = total_a = count = 0

    for x in range(image.width()):
        for y in range(image.height()):
            pixel = image.pixelColor(x, y)  # 返回 QColor
            if pixel.alpha() > 0:  # 忽略完全透明像素
                total_r += pixel.red()
                total_g += pixel.green()
                total_b += pixel.blue()
                total_a += pixel.alpha()
                count += 1

    if count == 0:
        return QtGui.QColor(0, 0, 0, 0)  # 全透明

    avg_r = total_r // count
    avg_g = total_g // count
    avg_b = total_b // count
    avg_a = total_a // count

    return QtGui.QColor(avg_r, avg_g, avg_b, avg_a)

class ColorIconGenerator(QtCore.QObject):
    def __init__(self, svg_path_or_data, default_color: QtGui.QColor = QtGui.QColor('#ffffff')):
        super().__init__()
        self._original_svg_data = self._load_svg_data(svg_path_or_data)
        self._color = default_color
        self._current_renderer = None
        self._update_renderer()

    def _load_svg_data(self, svg_path_or_data):
        if isinstance(svg_path_or_data, str):
            if svg_path_or_data.endswith('.svg'):
                with open(svg_path_or_data, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return svg_path_or_data  # raw SVG string
        else:
            # Assume bytes or QByteArray
            return bytes(svg_path_or_data).decode('utf-8')

    def _update_renderer(self):
        # 替换 fill 和 stroke 颜色（简单粗暴但有效）
        svg_data = self._original_svg_data
        color_hex = self._color.name(QtGui.QColor.NameFormat.HexArgb)  # 如 #ff000000

        # 移除 alpha 通道如果不需要（或保留）
        # 如果你希望完全不透明，可用 HexRgb
        color_hex = self._color.name(QtGui.QColor.NameFormat.HexRgb)  # 如 #000000

        # 替换常见 fill/stroke 属性（忽略大小写，处理多种格式）
        # 注意：这只是一个启发式方法，复杂 SVG 可能需要更严谨的 XML 解析
        svg_data = re.sub(
            r'(?i)(fill|stroke)="[^"]*"', 
            f'\\1="{color_hex}"', 
            svg_data
        )
        # 移除 style="fill:xxx" 这类内联样式（可选，更复杂）
        # 可扩展支持 <style> 标签，但大多数图标 SVG 不包含

        self._current_renderer = QSvgRenderer(QtCore.QByteArray(svg_data.encode('utf-8')))
        if not self._current_renderer.isValid():
            raise ValueError("Generated SVG is invalid")

    def setColor(self, color: QtGui.QColor):
        if self._color != color:
            self._color = QtGui.QColor(color)  # 确保拷贝
            self._update_renderer()

    def getColor(self):
        return self._color

    color = QtCore.Property(QtGui.QColor, getColor, setColor)

    def pixmap(self, size: QtCore.QSize, color: QtGui.QColor = None) -> QtGui.QPixmap:
        if color is not None and color != self._color:
            # 临时颜色：创建临时 renderer
            temp_gen = ColorIconGenerator(self._original_svg_data, color)
            return temp_gen.pixmap(size)
        else:
            pixmap = QtGui.QPixmap(size)
            pixmap.fill(QtCore.Qt.GlobalColor.transparent)
            painter = QtGui.QPainter(pixmap)
            self._current_renderer.render(painter)
            painter.end()
            return pixmap

    def icon(self, size: QtCore.QSize, color: QtGui.QColor = None) -> QtGui.QIcon:
        return QtGui.QIcon(self.pixmap(size, color))