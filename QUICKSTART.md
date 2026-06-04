# 🚀 5 分鐘快速開始

## 第 1 步：啟動後端

### Windows

```bash
startup.bat
```

### macOS / Linux

```bash
chmod +x startup.sh && ./startup.sh
```

### 手動啟動

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

後端服務運行於 `http://localhost:5000`，可用 `GET /api/health` 驗證。

---

## 第 2 步：安裝 Chrome 擴充功能

1. 開啟 Chrome，輸入 `chrome://extensions`
2. 啟用右上角「**開發人員模式**」
3. 點擊「**載入未封裝項目**」
4. 選擇專案的 `extension/` 資料夾
5. 擴充功能出現在工具列即代表安裝成功

---

## 第 3 步：設定 AI 模型

點擊工具列的 🎯 圖示 → **⚙️ 設定** 頁

| 選項 | 填入內容 |
|------|----------|
| OpenAI API | 你的 `sk-...` API Key |
| Claude API | 你的 `sk-ant-...` API Key |
| 本地模型 (Ollama) | `http://localhost:11434`（預設值） |

點擊「💾 保存設定」。

---

## 第 4 步：設定連線端口（🔌 連線頁）

點擊 🎯 圖示 → **🔌 連線** 頁

### 選項 A：使用後端 API（預設）

1. **後端伺服器 URL** 填入 `http://localhost:5000`（或你的自訂端口）
2. 點擊「**測試**」確認 ✅ 已連線
3. 點擊「💾 保存連線設定」

### 選項 B：Ollama 直接模式（不需後端）

> 適合只想用本地 AI 分析，不需要薪資統計功能的使用者

1. 先安裝 Ollama：[https://ollama.ai](https://ollama.ai)
2. 下載模型：
   ```bash
   ollama pull llama2
   # 或更快的 mistral
   ollama pull mistral
   ```
3. 在 **🔌 連線** 頁開啟「**直接模式**」開關
4. **Ollama URL** 填入 `http://localhost:11434`
5. 點擊「**測試**」→ 等待模型清單載入
6. 從下拉選單選擇模型
7. 點擊「💾 保存連線設定」

---

## 第 5 步：開始使用

1. 前往 [104 人力銀行](https://www.104.com.tw)
2. 搜尋任意職位
3. 職位卡片上會自動出現風險標記：
   - 🔴 **屎缺** — 高風險
   - 🟡 **小心** — 中風險
   - 🟢 **正常** — 低風險

---

## 常見問題速解

| 問題 | 解決方案 |
|------|----------|
| 擴充功能無法連接後端 | 確認後端運行中；或在🔌連線頁點擊「測試」 |
| 職位標記不顯示 | 在 `chrome://extensions` 重新整理擴充功能 |
| Ollama 模型清單空白 | 先執行 `ollama serve` 並確認已安裝模型 |
| 速度慢 | 使用直接模式 + mistral（比 llama2 快 2x） |

更多問題請見 [FAQ.md](FAQ.md)


- 📖 查看 [完整設置指南](SETUP_GUIDE.md)
- 🤔 查看 [FAQ](FAQ.md)
- 💻 查看 [開發者指南](DEVELOPER_GUIDE.md)

---

💡 **提示**: 首次運行會自動安裝依賴，請耐心等待。
