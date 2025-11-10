@echo on
setlocal enabledelayedexpansion

:: ????? hidden_imports ??????PyInstaller???importlib??????????????
set "hidden_imports="
:: ?? windows ????? .py ?????????
for %%f in (windows\*.py) do (
    set "filename=%%~nf"
    if "!filename!" neq "__init__" (
        set "hidden_imports=!hidden_imports! --hidden-import=windows.!filename!"
    )
)
:: ???? windows ???? windows/utils/???????????????
:: ?????????

:: ?? PyInstaller
pyinstaller --onefile --windowed ^
    --name MCMigrate ^
    --icon=app.ico ^
    --add-data "assets;assets" ^
    --add-data "qss;qss" ^
    %hidden_imports% ^
    --exclude-module numpy ^
    --exclude-module scipy ^
    --exclude-module matplotlib ^
    --exclude-module PySide6.Qt3DCore ^
    --exclude-module PySide6.Qt3DRender ^
    --exclude-module PySide6.QtBluetooth ^
    --exclude-module PySide6.QtMultimedia ^
    --exclude-module PySide6.QtWebEngineCore ^
    --exclude-module PySide6.QtWebEngineWidgets ^
    --exclude-module PySide6.QtCharts ^
    --exclude-module PySide6.QtDataVisualization ^
    --exclude-module PySide6.QtNetwork ^
    --exclude-module PySide6.QtOpenGL ^
    --exclude-module PySide6.QtPrintSupport ^
    --exclude-module PySide6.QtSql ^
    --exclude-module PySide6.QtTest ^
    --exclude-module PySide6.QtUiTools ^
    --exclude-module PySide6.QtXml ^
    main.py
pause