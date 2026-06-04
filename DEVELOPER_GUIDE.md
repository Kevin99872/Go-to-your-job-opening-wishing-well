# 台灣求職避雷器 - 開發者指南

## � 本文件涵蓋

- [環境建置](#-環境建置)
- [專案模組說明](#-專案模組說明)
- [API 端點一覽](#-api-端點一覽)
- [代碼規範](#-代碼規範)
- [測試](#-測試)
- [開發工作流](#-開發工作流)
- [自訂分析邏輯](#-自訂分析邏輯)
- [常見開發問題](#-常見開發問題)

---

## 🛠️ 環境建置

### 前置要求

- Python 3.8+
- Git
- Chrome 或 Edge 瀏覽器

### 後端安裝

```bash
cd backend

# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 安裝開發工具
pip install pytest pytest-cov black flake8 mypy

# 複製環境配置
cp .env.example .env
# 編輯 .env，填入你的 API Key（可選）

# 啟動後端
python app.py
```

後端服務運行於 `http://localhost:5000`

### AI 模型配置（.env）

```dotenv
# 使用 OpenAI
MODEL_TYPE=openai
API_KEY=sk-your-openai-api-key

# 使用 Claude
# MODEL_TYPE=claude
# API_KEY=sk-ant-your-claude-api-key

# 使用 Ollama 本地模型
# MODEL_TYPE=local
# LOCAL_URL=http://localhost:11434
```

### 安裝 Ollama（本地模型）

```bash
# 安裝：https://ollama.ai

# 啟動服務
ollama serve

# 下載推薦模型
ollama pull mistral    # 速度快，適合分析
ollama pull llama2     # 更完整，較慢
```

### 擴充功能載入

1. Chrome 輸入 `chrome://extensions`
2. 開啟右上角「**開發人員模式**」
3. 點擊「**載入未封裝項目**」→ 選擇 `extension/` 資料夾
4. 前往 **🔌 連線** 頁設定後端 URL 或 Ollama 端口

---

## 📚 專案模組說明

| 檔案 | 職責 |
|------|------|
| `backend/app.py` | Flask 應用主文件，定義所有 API 端點 |
| `backend/src/services/crawler.py` | 從 104 爬取職位數據（BeautifulSoup） |
| `backend/src/services/analyzer.py` | 職位風險評估邏輯，薪資統計比對 |
| `backend/src/services/models.py` | AI 模型統一調用介面（OpenAI/Claude/Ollama） |
| `extension/src/background.js` | 後台服務：API 通訊、緩存、Ollama 直接模式 |
| `extension/src/content.js` | 注入 104 頁面，擷取職位資料並標記 |
| `extension/src/popup.*` | 設定介面 UI（⚙️ 設定、🔌 連線、ℹ️ 關於） |

---

## 📡 API 端點一覽

### `GET /api/health`
```json
{ "status": "healthy", "service": "台灣求職避雷器" }
```

### `POST /api/analyze`
```json
// Request
{ "jobTitle": "C# 工程師", "salary": "45K~60K", "company": "ABC", "description": "..." }

// Response
{ "riskLevel": "medium", "score": 55, "reasons": ["..."], "recommendation": "..." }
```

### `GET /api/salary-stats?jobTitle=C%23+工程師`
```json
{ "median": 55000, "min": 40000, "max": 80000 }
```

### `POST /api/crawl`
```json
{ "status": "success", "jobs_count": 150, "message": "爬蟲完成" }
```

### `GET/POST /api/config`
讀寫後端 AI 模型設定。POST 時不需傳入 `api_key` 以外的敏感欄位。

### `GET /api/ollama/models`
代理 Ollama `GET /api/tags`，回傳可用模型清單（解決 CORS 問題）。

### `POST /api/ollama/generate`
代理 Ollama `POST /api/generate`（備用，擴充功能直接模式優先直連 Ollama）。

---

## 📝 代碼規範

遵循 PEP 8：

```bash
# 格式化
black backend/src

# 風格檢查
flake8 backend/src

# 類型檢查
mypy backend/src
```

---

## 🧪 測試

```bash
# 所有測試
python -m pytest

# 特定測試類
python -m pytest backend/tests.py::TestJobAnalyzer

# 含覆蓋率報告
pytest --cov=backend/src --cov-report=html
```

新增測試範例：

```python
# backend/tests.py
class TestNewFeature(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
```

---

## 🚀 開發工作流

```bash
# 1. 建立特性分支
git checkout -b feature/new-feature

# 2. 開發並提交
git add .
git commit -m "feat: add new feature"

# 3. 測試 & 代碼檢查
pytest
black --check backend/src
flake8 backend/src

# 4. 推送並建立 PR
git push origin feature/new-feature
```

---

## 🔧 自訂分析邏輯

### 修改風險評估規則

編輯 `backend/src/services/analyzer.py` 的 `_perform_analysis`：

```python
def _perform_analysis(self, ...):
    reasons = []
    score = 50  # 基礎分數

    # 自訂薪資門檻
    if salary_range['max'] < median * 0.75:  # 低於 75% 視為警示
        reasons.append('薪資低於業界中位數 25%')
        score -= 20

    # 自訂關鍵詞
    red_flags = ['急徵', '立即上班', '高壓', '責任制', '無休假', '自帶電腦']
    for flag in red_flags:
        if flag in description:
            reasons.append(f'描述含「{flag}」')
            score -= 5
    ...
```

### 新增 API 端點

```python
# backend/app.py
@app.route('/api/new-endpoint', methods=['POST'])
def new_endpoint():
    """新端點說明"""
    try:
        data = request.json
        result = do_something(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f'錯誤: {str(e)}')
        return jsonify({'error': str(e)}), 500
```

---

## 🐛 常見開發問題

**ModuleNotFoundError: No module named 'flask'**
```bash
# 確保虛擬環境已啟動
source venv/bin/activate   # 或 Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**爬蟲無法解析 HTML**  
104 網站結構可能已更新，請用瀏覽器 DevTools 重新確認 CSS 選擇器，然後更新 `crawler.py`。

**API Key 無效**  
確認 `.env` 中的 Key 未過期，且 `MODEL_TYPE` 與 Key 類型一致。

**Ollama 連線失敗**  
確認 `ollama serve` 已執行，並嘗試 `curl http://localhost:11434/api/tags` 驗證。

---

## 🔒 安全最佳實踐

- ✅ 不要在代碼中硬編碼 API Key，使用 `.env`
- ✅ 不要將 `.env` 或 `config.json` 提交到 Git
- ✅ 驗證所有使用者輸入（已在端點層處理）
- ✅ 日誌中不打印敏感資訊

---

## 📞 獲得幫助

- 查看 [FAQ.md](FAQ.md)
- 提交 [Issue](https://github.com/Kevin99872/Go-to-your-job-opening-wishing-well/issues)
- 加入 [討論](https://github.com/Kevin99872/Go-to-your-job-opening-wishing-well/discussions)


---

感謝你的貢獻！
