# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['MCMigrate\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('MCMigrate/assets', 'assets'), ('MCMigrate/qss', 'qss')],
    hiddenimports=['windows.loadStyleSheet', 'windows.Migrate', 'windows.MigrateDetail', 'windows.SendMessageable', 'windows.Welcome'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'scipy', 'matplotlib', 'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.QtBluetooth', 'PySide6.QtMultimedia', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtNetwork', 'PySide6.QtOpenGL', 'PySide6.QtPrintSupport', 'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtUiTools', 'PySide6.QtXml'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MCMigrate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app.ico'],
)
