#!/bin/bash

# 启用严格模式
set -euo pipefail

# 收集 windows/ 目录下所有非 __init__.py 的模块，作为 --hidden-import
hidden_imports=""
for f in MCMigrate/windows/*.py; do
    if [[ -f "$f" ]]; then
        filename=$(basename "$f" .py)
        if [[ "$filename" != "__init__" ]]; then
            hidden_imports="$hidden_imports --hidden-import=windows.$filename"
        fi
    fi
done

# 构建命令
pyinstaller --onefile --windowed \
    --name MCMigrate \
    --icon=app.icns \
    --add-data "MCMigrate/assets:assets" \
    --add-data "MCMigrate/qss:qss" \
    $hidden_imports \
    --exclude-module numpy \
    --exclude-module scipy \
    --exclude-module matplotlib \
    --exclude-module PySide6.Qt3DCore \
    --exclude-module PySide6.Qt3DRender \
    --exclude-module PySide6.QtBluetooth \
    --exclude-module PySide6.QtMultimedia \
    --exclude-module PySide6.QtWebEngineCore \
    --exclude-module PySide6.QtWebEngineWidgets \
    --exclude-module PySide6.QtCharts \
    --exclude-module PySide6.QtDataVisualization \
    --exclude-module PySide6.QtNetwork \
    --exclude-module PySide6.QtOpenGL \
    --exclude-module PySide6.QtPrintSupport \
    --exclude-module PySide6.QtSql \
    --exclude-module PySide6.QtTest \
    --exclude-module PySide6.QtUiTools \
    --exclude-module PySide6.QtXml \
    MCMigrate/main.py