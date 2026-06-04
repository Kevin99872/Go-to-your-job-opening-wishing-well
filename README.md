# 台灣求職避雷器 🎯

> 幫助台灣勞工找到符合薪水水準的工作機會 | Help Taiwan workers find fair-paying jobs

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-green.svg)](https://chrome.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[繁體中文](#-關於本專案) | [English](#english)

---

## 📖 文件導覽

| 文件 | 說明 |
|------|------|
| **README.md** (本文件) | 專案總覽、架構、API 端點 |
| [QUICKSTART.md](QUICKSTART.md) | 5 分鐘快速上手 |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | 開發環境建置、貢獻指南 |
| [FAQ.md](FAQ.md) | 常見問題解答 |
| [DEPLOYMENT.md](DEPLOYMENT.md) | 雲端 / Docker 部署 |

---

## 🌟 關於本專案

現代的台灣職場偏向於讓公司覺得「值得雇傭」才雇傭人，但恰恰如此，才出現了**低薪高用**、要求與實際工作不對等的狀況。我們希望通過這個工具，幫助台灣勞工識別這類職缺，獲得符合他們薪水和能力的「strong offer」。

## 🎯 功能特色

- 🔍 **自動分析職位** - 在 104 人力銀行上即時識別風險職缺
- 💰 **薪資對標** - 與業界標準薪資比較
- 🚨 **風險警示** - 標記「低薪高用」、責任制等問題
- 🤖 **AI 驅動** - 支援 OpenAI、Claude、Ollama 本地模型
- 🔌 **靈活串接** - 可自訂後端 API 端口與 Ollama 本地端口
- 🔒 **隱私優先** - 支援完全離線的本地模型執行

## 📊 風險等級

| 等級 | 標記 | 說明 |
|------|------|------|
| 🔴 高風險 | 屎缺 ⚠️ | 薪資過低或要求過高，不建議投遞 |
| 🟡 中風險 | 小心 ⚠ | 需進一步了解，審慎考慮 |
| 🟢 低風險 | 正常 ✓ | 相對合理，值得進一步了解 |

## 📊 版本規劃

**Phase 1（當前）**：104 人力銀行 + C#/.NET 軟體工程師
- ✅ 職位爬蟲
- ✅ Chrome/Edge 擴充功能
- ✅ 基礎分析引擎
- ✅ AI 多模型集成
- ✅ 自訂 API 端口 & Ollama 直接模式

**Phase 2**：擴展職位類別（所有技術職位、非技術職位）

**Phase 3**：其他人力銀行平台

## 🏗️ 技術架構

```
┌─────────────────────────────────────────────────┐
│          Chrome/Edge 擴充功能                    │
│  background.js  │  content.js  │  popup (UI)    │
│  ┌────────────────────────────────────────────┐ │
│  │  🔌 連線設定頁                             │ │
│  │  - 自訂後端 API URL（預設 :5000）          │ │
│  │  - 直接模式切換（繞過後端直呼 Ollama）      │ │
│  │  - Ollama URL + 模型選擇（動態載入）        │ │
│  └────────────────────────────────────────────┘ │
└──────────────┬──────────────────────────────────┘
               │ HTTP  (模式 A: 後端 API)
               ▼
┌─────────────────────────────────────────────────┐
│          Flask 後端 (Python :5000)               │
│  /api/analyze        職位風險分析                │
│  /api/salary-stats   薪資統計                    │
│  /api/crawl          觸發爬蟲                    │
│  /api/config         模型配置                    │
│  /api/ollama/models  代理取得模型清單            │
│  /api/ollama/generate 代理 Ollama 生成           │
└──────────────┬──────────────────────────────────┘
               │ HTTP  (模式 B: 直接模式)
               ▼
┌─────────────────────────────────────────────────┐
│          Ollama 本地服務 (:11434)                │
│  llama2 / mistral / 其他已安裝模型              │
└─────────────────────────────────────────────────┘
```

## 📁 專案結構

```
.
├── backend/                      # Python Flask 後端
│   ├── app.py                   # 主應用（API 端點）
│   ├── requirements.txt         # 依賴清單
│   ├── .env.example             # 環境變數範例
│   ├── config.example.json      # JSON 配置範例
│   └── src/services/
│       ├── crawler.py           # 104 職位爬蟲
│       ├── analyzer.py          # 職位分析引擎
│       └── models.py            # AI 模型管理
│
├── extension/                    # Chrome/Edge 擴充功能
│   ├── manifest.json            # Manifest V3 配置
│   └── src/
│       ├── background.js        # 後台服務 & API 通訊
│       ├── content.js           # 104 頁面注入腳本
│       ├── popup.html           # 設定介面（含🔌連線頁）
│       ├── popup.js             # 設定邏輯
│       ├── popup.css            # 設定樣式
│       └── styles.css           # 頁面標記樣式
│
├── QUICKSTART.md                # ← 從這裡開始
├── DEVELOPER_GUIDE.md           # 開發者 & 安裝完整指南
├── FAQ.md                       # 常見問題
├── DEPLOYMENT.md                # 雲端 / Docker 部署
├── startup.bat                  # Windows 一鍵啟動
├── startup.sh                   # macOS/Linux 一鍵啟動
└── startup.py                   # 跨平台 Python 啟動
```

## 🚀 快速開始

### Windows

```bash
# 直接雙擊或在 PowerShell 中執行
startup.bat
```

### macOS / Linux

```bash
chmod +x startup.sh && ./startup.sh
```

詳細步驟（含 AI 模型配置與連線設定）請見 [QUICKSTART.md](QUICKSTART.md)

## 🔌 AI 模型配置

| 模型 | 配置方式 | 優點 |
|------|----------|------|
| **OpenAI** | `backend/.env` 填入 API Key | 準確度最高 |
| **Claude** | `backend/.env` 填入 API Key | 回應品質均衡 |
| **Ollama（本地）** | 擴充功能 🔌 連線頁設定 URL | 免費、完全離線 |

Ollama 直接模式可在擴充功能的「🔌 連線」頁開啟，無需後端即可分析職位。

## 📡 後端 API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| `GET` | `/api/health` | 健康檢查 |
| `POST` | `/api/analyze` | 職位風險分析 |
| `GET` | `/api/salary-stats` | 薪資統計查詢 |
| `POST` | `/api/crawl` | 觸發 104 爬蟲 |
| `GET/POST` | `/api/config` | 讀寫模型配置 |
| `GET` | `/api/ollama/models` | 取得 Ollama 模型清單 |
| `POST` | `/api/ollama/generate` | 代理 Ollama 生成 |

## 🔐 隱私與安全

- ✅ API Key 僅存於本機瀏覽器 Storage，不上傳雲端
- ✅ 本地模型完全離線執行
- ✅ 開源代碼，可自行審計
- ✅ 無個人資料蒐集

---

## English

### Vision

The modern Taiwan job market tends to favor companies — people are hired only if employers think they're "worth hiring". This leads to **low-pay high-demand** mismatches. This tool helps Taiwan workers identify such job postings and secure offers that match their skills.

### 🎯 Objectives

- 🔍 **Auto-Analyze Job Postings** on 104 Job Bank
- 💰 **Salary Benchmarking** against industry standards
- 🚨 **Risk Detection** — flag problematic conditions
- 🤖 **AI-Powered** — OpenAI, Claude, or local Ollama models
- 🔌 **Flexible Connections** — configurable API & Ollama ports
- 🔒 **Privacy First** — fully offline local model support

### 📊 Roadmap

**Phase 1 (Current)**: 104 Job Bank + C#/.NET Engineers  
**Phase 2**: All tech & non-tech positions  
**Phase 3**: Other job platforms

### 🚀 Quick Start

```bash
# Windows
startup.bat

# macOS / Linux
chmod +x startup.sh && ./startup.sh
```

See [QUICKSTART.md](QUICKSTART.md) for full instructions.

### 📊 Risk Levels

| Level | Badge | Meaning |
|-------|-------|---------|
| 🔴 High | ⚠️ Bad Job | Low pay, high demands |
| 🟡 Medium | ⚠ Be Careful | Needs further review |
| 🟢 Low | ✓ Normal | Reasonable position |

### 🤝 Contributing

Issues and Pull Requests are welcome!  
See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for contribution guidelines.

### 📝 License

MIT License

---

**Made with ❤️ for Taiwan Workers | 為台灣勞工而做**

*Your time and skills are valuable. Don't accept unreasonable salaries! 💪*


