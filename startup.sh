#!/bin/bash
# 台灣求職避雷器 - macOS/Linux 啟動腳本

echo "========================================"
echo "台灣求職避雷器 - 啟動"
echo "========================================"

# 檢查 Python
if ! command -v python3 &> /dev/null; then
    echo "錯誤: 未找到 Python，請先安裝 Python 3.8+"
    exit 1
fi

# 進入後端目錄
cd backend

# 創建虛擬環境
if [ ! -d "venv" ]; then
    echo "創建虛擬環境..."
    python3 -m venv venv
fi

# 激活虛擬環境
source venv/bin/activate

# 安裝依賴
if ! pip freeze | grep -q Flask; then
    echo "安裝依賴..."
    pip install -r requirements.txt
fi

# 複製環境配置
if [ ! -f ".env" ]; then
    echo "複製環境配置..."
    cp .env.example .env
    echo ""
    echo "⚠️  請編輯 backend/.env 文件填入 API Key"
    echo ""
fi

# 啟動服務
echo "啟動後端服務..."
echo "服務運行在 http://localhost:5000"
echo "按 Ctrl+C 停止服務"
echo ""

python app.py
