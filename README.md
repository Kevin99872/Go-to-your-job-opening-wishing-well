# 台灣求職避雷器 🎯 | Taiwan Job Alert

> **幫助你找到喜歡的公司 | Help you find a satisfying company**

[中文說明](#繁體中文) | [English](#english)

---

## 繁體中文

### 發想

現代的台灣職場偏向於讓公司覺得「值得雇傭」才雇傭人，但恰恰如此，才出現了**低薪高用**、要求與實際工作不對等的狀況。我們希望通過這個工具，幫助台灣勞工識別這類職缺，獲得符合他們薪水和能力的「strong offer」。

### 🎯 目的

- 🔍 **自動分析職位** - 在 104 人力銀行上識別風險職缺
- 💰 **薪資對標** - 與業界標準薪資比較
- 🚨 **風險警示** - 標記「低薪高用」、責任制等問題
- 🤖 **AI 驅動** - 支援多種 AI 模型進行智能分析
- 🔒 **隱私優先** - 支援本地離線模型運行

### 📊 版本規劃

**Phase 1 (當前)**: 104 人力銀行 + C# .NET 軟體工程師
- ✅ 職位爬蟲
- ✅ Chrome/Edge 擴充功能
- ✅ 基礎分析引擎
- ✅ AI 模型集成

**Phase 2**: 擴展職位類別
- 所有技術職位
- 非技術職位

**Phase 3**: 其他人力銀行
- 其他職位平台支援

### 🏗️ 技術架構

```
┌─────────────────────────────────────┐
│      Chrome/Edge 擴充功能            │
│  (JavaScript + 即時職位標記)         │
└──────────┬──────────────────────────┘
           │ HTTP API
           ▼
┌─────────────────────────────────────┐
│      Flask 後端 (Python)             │
│                                       │
│  ┌───────────────────────────────┐  │
│  │ 職位爬蟲 (104 人力銀行)       │  │
│  │ - BeautifulSoup 解析          │  │
│  │ - 薪資統計提取                │  │
│  └───────────────────────────────┘  │
│                                       │
│  ┌───────────────────────────────┐  │
│  │ 風險分析引擎                  │  │
│  │ - 薪資對標                    │  │
│  │ - 關鍵詞檢測                  │  │
│  │ - 綜合評分                    │  │
│  └───────────────────────────────┘  │
│                                       │
│  ┌───────────────────────────────┐  │
│  │ AI 模型管理                   │  │
│  │ - OpenAI 集成                 │  │
│  │ - Claude 集成                 │  │
│  │ - Ollama 本地模型             │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 📁 項目結構

```
.
├── backend/                      # Python Flask 後端
│   ├── app.py                   # 主應用程式
│   ├── requirements.txt         # 依賴清單
│   ├── .env.example             # 環境變數範例
│   ├── config.example.json      # 配置範例
│   └── src/
│       └── services/
│           ├── crawler.py       # 104 職位爬蟲
│           ├── analyzer.py      # 職位分析引擎
│           └── models.py        # AI 模型管理
│
├── extension/                    # Chrome/Edge 擴充功能
│   ├── manifest.json            # 擴充配置
│   ├── icons/                   # 擴充圖標
│   └── src/
│       ├── background.js        # 後台服務 & API 通訊
│       ├── content.js           # 內容腳本 (104 頁面注入)
│       ├── popup.html           # 設定界面
│       ├── popup.js             # 設定邏輯
│       ├── popup.css            # 設定樣式
│       └── styles.css           # 頁面標記樣式
│
├── SETUP_GUIDE.md               # 完整安裝指南
├── startup.bat                  # Windows 啟動腳本
├── startup.sh                   # macOS/Linux 啟動腳本
├── startup.py                   # 跨平台 Python 啟動
├── README.md                    # 本文件
├── README_ZH.md                 # 中文詳細說明
└── .gitignore                   # Git 配置

```

### 🚀 快速開始

#### Windows

```bash
# 最簡單：直接雙擊
double-click startup.bat

# 或在 PowerShell
.\startup.bat
```

#### macOS / Linux

```bash
chmod +x startup.sh
./startup.sh
```

詳見 [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## English

### Vision

The modern Taiwan job market tends to favor companies - people are hired only if employers think they're "worth hiring". This leads to situations of **low pay with high demands**, mismatches between job requirements and actual work, etc. We hope this tool helps Taiwan workers identify such job postings and find offers that match their skills and salary expectations.

### 🎯 Objectives

- 🔍 **Auto-Analyze Job Postings** - Identify risky positions on 104 Job Bank
- 💰 **Salary Benchmarking** - Compare with industry standards
- 🚨 **Risk Detection** - Flag "low-pay-high-demand" and problematic conditions
- 🤖 **AI-Powered** - Support multiple AI models for intelligent analysis
- 🔒 **Privacy First** - Support offline local model execution

### 📊 Roadmap

**Phase 1 (Current)**: 104 Job Bank + C#/.NET Engineers
- ✅ Job Scraper
- ✅ Chrome/Edge Extension
- ✅ Basic Analysis Engine
- ✅ AI Model Integration

**Phase 2**: Expand Job Categories
- All Tech Positions
- Non-Tech Positions

**Phase 3**: Other Job Platforms

### 🚀 Quick Start

#### Windows

```bash
double-click startup.bat
```

#### macOS / Linux

```bash
chmod +x startup.sh
./startup.sh
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions

### 📊 Risk Levels

| Level | Badge | Meaning |
|-------|-------|---------|
| 🔴 High | ⚠️ Bad Job | Low pay, high demands - Don't apply |
| 🟡 Medium | ⚠ Be Careful | Needs further review - Consider carefully |
| 🟢 Low | ✓ Normal | Reasonable position - Worth exploring |

### 🔐 Privacy & Security

- ✅ Local models run completely offline
- ✅ API keys stored only in local browser storage
- ✅ No personal data sent to cloud
- ✅ Open source - auditable code

### 🤝 Contributing

We welcome Issues and Pull Requests!

### 📝 License

MIT License

---

**Made with ❤️ for Taiwan Workers | 為台灣勞工而做**

*Your time and skills are valuable. Don't accept unreasonable salaries! 💪*


