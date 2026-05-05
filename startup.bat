@echo off
REM 台灣求職避雷器 - Windows 啟動腳本

echo ========================================
echo 台灣求職避雷器 - Windows 啟動
echo ========================================

REM 檢查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 錯誤: 未找到 Python，請先安裝 Python 3.8+
    pause
    exit /b 1
)

REM 進入後端目錄
cd backend

REM 創建虛擬環境
if not exist venv (
    echo 創建虛擬環境...
    python -m venv venv
)

REM 激活虛擬環境
call venv\Scripts\activate.bat

REM 安裝依賴
if not exist venv\Lib\site-packages\flask (
    echo 安裝依賴...
    pip install -r requirements.txt
)

REM 複製環境配置
if not exist .env (
    echo 複製環境配置...
    copy .env.example .env
    echo.
    echo ⚠️  請編輯 backend\.env 文件填入 API Key
    echo.
)

REM 啟動服務
echo 啟動後端服務...
echo 服務運行在 http://localhost:5000
echo 按 Ctrl+C 停止服務
echo.

python app.py

pause
