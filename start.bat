@echo off
setlocal

cd /d "%~dp0"
set "ROOT_DIR=%~dp0"
set "PYTHONPATH=%ROOT_DIR%src"

echo.
echo [DIP查询助手] 一键启动
echo 项目目录: %ROOT_DIR%
echo.

set "PYTHON_CMD=python"
py -3.8 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.8"
)

call %PYTHON_CMD% -c "import sys; print('[Python] ' + sys.executable); print('[Version] ' + '.'.join(str(x) for x in sys.version_info[:3]))"
if errorlevel 1 (
    echo [错误] 未找到可用的 Python，请先安装 Python 3.8 x64。
    goto :fail
)

call %PYTHON_CMD% -c "import pandas, openpyxl, PySide2" >nul 2>&1
if errorlevel 1 (
    echo [错误] 缺少运行依赖。建议先执行：
    echo python -m pip install -r requirements.txt
    echo.
    echo 如果当前默认 Python 不是 3.8，请先安装 Python 3.8 x64，再执行：
    echo py -3.8 -m pip install -r requirements.txt
    goto :fail
)

echo [1/2] 重建本地查询库...
call %PYTHON_CMD% scripts\build_data.py
if errorlevel 1 (
    echo [错误] 查询库重建失败。
    goto :fail
)

echo [2/2] 启动桌面程序...
call %PYTHON_CMD% run_app.py
if errorlevel 1 (
    echo [错误] 程序启动失败。
    goto :fail
)

goto :end

:fail
echo.
echo 启动未完成，请按上面的提示处理后重试。
pause
exit /b 1

:end
endlocal
