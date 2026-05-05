<!-- README in Traditional Chinese -->

# 台灣求職避雷器 🎯

> 幫助台灣勞工找到符合薪水水準的工作機會

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-green.svg)](https://chrome.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🌟 功能特色

- 🔍 **職位自動分析** - 在 104 頁面上直接標記職位風險
- 💰 **薪資對標** - 與業界標準薪資比較
- 🚨 **風險識別** - 識別低薪高用、責任制等問題職位
- 🤖 **AI 驅動** - 支援多種 AI 模型進行深度分析
- 🔒 **隱私優先** - 支援本地離線模型
- ⚡ **即時更新** - 職位信息實時爬取和分析

## 📊 風險等級

| 等級 | 標記 | 說明 |
|------|------|------|
| 🔴 高風險 | 屎缺 ⚠️ | 薪資過低，要求過高，不建議投遞 |
| 🟡 中風險 | 小心 ⚠ | 需要進一步了解，審慎考慮 |
| 🟢 低風險 | 正常 ✓ | 相對合理，值得進一步了解 |

## 🚀 快速開始

### 最簡單的方式 (Windows)

```bash
# 直接運行
double-click startup.bat

# 或在 PowerShell 中
.\startup.bat
```

### macOS / Linux

```bash
# 賦予執行權限
chmod +x startup.sh

# 運行
./startup.sh
```

### 手動設置

詳見 [SETUP_GUIDE.md](SETUP_GUIDE.md)

## 🔧 配置 AI 模型

### 選項 1: OpenAI (推薦)

```bash
# 編輯 backend/.env
MODEL_TYPE=openai
API_KEY=sk-your-openai-api-key
```

**優點:** 精準度高，支援最新模型
**缺點:** 需要付費 API

### 選項 2: Claude

```bash
# 編輯 backend/.env
MODEL_TYPE=claude
API_KEY=sk-ant-your-claude-api-key
```

**優點:** 性能均衡，回應質量好
**缺點:** 需要付費 API

### 選項 3: 本地模型 (離線，免費)

```bash
# 安裝 Ollama
# https://ollama.ai

# 運行
ollama serve

# 編輯 backend/.env
MODEL_TYPE=local
LOCAL_URL=http://localhost:11434
```

**優點:** 完全離線，隱私最佳，免費
**缺點:** 需要本地計算資源

## 📱 如何使用

### 1. 啟動後端服務

```bash
# Windows
startup.bat

# macOS/Linux
./startup.sh

# 或使用 Python
python startup.py
```

### 2. 安裝瀏覽器擴充功能

#### Chrome / Edge

1. 打開瀏覽器，進入擴充功能頁面
   - Chrome: `chrome://extensions`
   - Edge: `edge://extensions`

2. 啟用「開發人員模式」(右上角)

3. 點擊「加載未封裝的擴充功能」

4. 選擇 `extension` 文件夾

### 3. 配置設定

1. 點擊擴充功能圖標
2. 進入「⚙️ 設定」標籤
3. 選擇 AI 模型並填入 API Key
4. 點擊「💾 保存設定」

### 4. 開始使用

1. 訪問 [104 人力銀行](https://www.104.com.tw)
2. 搜尋職位
3. 每個職位旁會自動顯示風險標記
4. 將滑鼠懸停在標記上查看詳細原因

## 📖 API 文檔

### 分析職位

```http
POST /api/analyze
Content-Type: application/json

{
  "jobTitle": "C# 軟體工程師",
  "salary": "45K~60K",
  "company": "公司名稱",
  "description": "職位描述..."
}
```

**回應:**
```json
{
  "riskLevel": "medium",
  "reasons": [
    "薪資低於業界中位數 20%",
    "職位描述包含「責任制」相關詞"
  ],
  "score": 45,
  "recommendation": "審慎考慮，可與現公司比較後決定",
  "ai_insights": "此職位的薪資對於該地區來說偏低..."
}
```

### 獲取薪資統計

```http
GET /api/salary-stats?jobTitle=C# 軟體工程師
```

### 觸發爬蟲

```http
POST /api/crawl
```

## 🏗️ 項目結構

```
.
├── backend/                    # Python Flask 後端
│   ├── app.py                 # 主應用程式
│   ├── requirements.txt       # Python 依賴
│   ├── .env.example           # 環境配置示例
│   └── src/
│       └── services/
│           ├── crawler.py     # 職位爬蟲
│           ├── analyzer.py    # 職位分析引擎
│           └── models.py      # AI 模型管理
│
├── extension/                  # Chrome/Edge 擴充功能
│   ├── manifest.json          # 擴充配置
│   ├── src/
│   │   ├── background.js      # 後台服務
│   │   ├── content.js         # 內容腳本
│   │   ├── popup.html         # 設定界面
│   │   ├── popup.js           # 設定邏輯
│   │   ├── popup.css          # 設定樣式
│   │   └── styles.css         # 頁面樣式
│   └── icons/                 # 擴充圖標
│
├── SETUP_GUIDE.md             # 詳細設置指南
├── startup.bat                # Windows 啟動腳本
├── startup.sh                 # macOS/Linux 啟動腳本
└── README.md                  # 本文件
```

## ⚙️ 系統要求

- **Python**: 3.8 或更高
- **Node.js**: 可選 (用於前端開發)
- **瀏覽器**: Chrome/Edge 最新版本
- **RAM**: 至少 2GB (使用本地模型時建議 8GB+)

## 🔒 隱私與安全

- ✅ 本地模型完全離線運行
- ✅ API Key 只存儲在本地瀏覽器
- ✅ 不上傳個人數據到雲端
- ✅ 開源代碼，歡迎審計

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

### 開發指南

```bash
# 克隆項目
git clone https://github.com/Kevin99872/Go-to-your-job-opening-wishing-well.git
cd Go-to-your-job-opening-wishing-well

# 後端開發
cd backend
python -m venv venv
source venv/bin/activate  # 或 venv\Scripts\activate
pip install -r requirements.txt
python app.py

# 擴充功能開發
# 加載 extension 文件夾到瀏覽器進行調試
```

## 📝 許可

MIT License - 詳見 [LICENSE](LICENSE)

## 🙋 常見問題

**Q: 為什麼擴充功能無法連接後端？**
A: 確保後端服務運行在 `localhost:5000`，且防火牆未阻止。

**Q: 如何自定義風險判斷標準？**
A: 編輯 `backend/src/services/analyzer.py` 中的邏輯。

**Q: 爬蟲無法提取信息？**
A: 104 網站結構可能變化，需要更新 `crawler.py` 中的 HTML 選擇器。

**Q: 本地模型性能很慢？**
A: 考慮升級硬件或使用 API 模型。

## 📞 聯絡

- 📧 Email: [你的郵箱]
- 🐦 Twitter: [@你的推特]
- 💬 Discord: [你的 Discord 伺服器]

## ❤️ 致謝

感謝所有貢獻者和使用者的支持！

---

**Made with ❤️ for Taiwan Workers**

記住：你的時間和技能很值錢，不要接受不合理的薪資！💪
