@echo off
echo ============================================
echo   AI 飞行仿真 Agent - 启动 Web 控制台
echo ============================================
echo.

cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] 虚拟环境已激活
) else (
    echo [WARN] 未找到虚拟环境，使用系统 Python
)

echo [INFO] 启动 Streamlit...
echo [INFO] 浏览器将自动打开 http://localhost:8501
echo.
streamlit run ui/app.py --server.port 8501 --server.headless false --theme.base dark

pause
