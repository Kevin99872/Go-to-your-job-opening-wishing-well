# 台灣求職避雷器

## 項目結構

```
.
├── backend/                      # Python Flask 後端
│   ├── app.py                   # 主應用
│   ├── requirements.txt         # Python 依賴
│   ├── .env.example             # 環境變數示例
│   └── src/
│       └── services/
│           ├── crawler.py       # 職位爬蟲
│           ├── analyzer.py      # 職位分析
│           └── models.py        # AI 模型管理
│
├── extension/                    # Chrome/Edge 擴充功能
│   ├── manifest.json            # 擴充功能配置
│   └── src/
│       ├── background.js        # 後台服務
│       ├── content.js           # 內容腳本
│       ├── popup.html           # 設定界面
│       ├── popup.js             # 設定腳本
│       ├── popup.css            # 設定樣式
│       └── styles.css           # 頁面樣式
│
└── README.md
```

## 快速開始

### 1. 後端設置

```bash
cd backend

# 創建虛擬環境
python -m venv venv

# 激活虛擬環境
# Windows:
venv\\Scripts\\activate
# macOS/Linux:
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 複製環境配置
cp .env.example .env

# 編輯 .env，填入你的 API Key
# 然後運行
python app.py
```

後端服務將運行在 `http://localhost:5000`

### 2. 擴充功能安裝

#### Chrome/Edge

1. 打開 `chrome://extensions` (Chrome) 或 `edge://extensions` (Edge)
2. 啟用「開發人員模式」
3. 點擊「加載未封裝的擴充功能」
4. 選擇 `extension` 文件夾

## 功能

### 🔍 職位分析
- 自動分析 104 職位
- 評估薪資是否合理
- 識別低薪高用職位

### ⚠️ 風險標記
- 🔴 **屎缺** - 高風險（薪資過低，要求過高）
- 🟡 **小心** - 中風險（需要進一步了解）
- 🟢 **正常** - 低風險（相對合理）

### 🤖 AI 分析
支援多種 AI 模型：
- **OpenAI** - 高準確度，需要 API Key
- **Claude** - 平衡性能，需要 API Key
- **本地模型** - 隱私優先，可離線使用 (Ollama)

## 配置

### 使用 OpenAI

```bash
# .env 中設置
MODEL_TYPE=openai
API_KEY=sk-your-openai-api-key
```

### 使用 Claude

```bash
# .env 中設置
MODEL_TYPE=claude
API_KEY=sk-ant-your-claude-api-key
```

### 使用本地模型 (Ollama)

```bash
# 安裝 Ollama: https://ollama.ai

# 運行 Ollama
ollama serve

# 下載模型
ollama pull llama2

# .env 中設置
MODEL_TYPE=local
LOCAL_URL=http://localhost:11434
```

## API 端點

### 分析職位
```
POST /api/analyze
{
  "jobTitle": "C# 軟體工程師",
  "salary": "45K~60K",
  "company": "公司名稱",
  "description": "職位描述..."
}
```

### 獲取薪資統計
```
GET /api/salary-stats?jobTitle=C# 軟體工程師
```

### 觸發爬蟲
```
POST /api/crawl
```

### 健康檢查
```
GET /api/health
```

## 開發

### 目錄結構說明

**Backend:**
- `app.py` - Flask 應用主文件，定義所有 API 端點
- `src/services/crawler.py` - 從 104 網站爬取職位數據
- `src/services/analyzer.py` - 分析職位並判斷風險等級
- `src/services/models.py` - 管理 AI 模型配置和調用

**Extension:**
- `manifest.json` - 擴充功能配置，定義權限和內容腳本
- `background.js` - 後台服務，處理 API 通訊和緩存
- `content.js` - 在 104 頁面上注入分析功能
- `popup.html/js/css` - 用戶設定界面

### 常見問題

**Q: 為什麼擴充功能無法連接後端？**
A: 確保：
- 後端服務運行在 `localhost:5000`
- CORS 已啟用（已在 app.py 中配置）
- 防火牆未阻止連接

**Q: 如何自定義風險判斷邏輯？**
A: 編輯 `backend/src/services/analyzer.py` 中的 `_perform_analysis` 方法

**Q: 爬蟲無法提取職位信息？**
A: 104 網站結構可能已更改，需要更新 `crawler.py` 中的 HTML 選擇器

## 貢獻

歡迎提交 PR 和 Issue！

## 許可

MIT License

---

💡 **提示**：
- 定期運行爬蟲以更新薪資統計
- 建議使用本地模型以保護隱私
- 給職位評分前，請確認後端已連接

