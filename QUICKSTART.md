# 🚀 5 分鐘快速開始

## Windows 用戶

### 第 1 步：啟動後端

```bash
# 直接雙擊
startup.bat
```

完成！你應該看到：
```
 * Running on http://127.0.0.1:5000/
```

### 第 2 步：配置 AI（可選）

編輯 `backend/.env`：

**選項 A: 使用 OpenAI**
```
MODEL_TYPE=openai
API_KEY=sk-your-openai-api-key-here
```

**選項 B: 免費本地模型**
```
MODEL_TYPE=local
LOCAL_URL=http://localhost:11434
```
需要先 [安裝 Ollama](https://ollama.ai)

### 第 3 步：安裝擴充功能

1. 打開 Chrome/Edge
2. 輸入 `chrome://extensions` 或 `edge://extensions`
3. 啟用「開發人員模式」(右上角)
4. 點擊「加載未封裝的擴充功能」
5. 選擇 `extension` 文件夾

### 第 4 步：配置擴充功能

1. 點擊擴充功能圖標
2. 選擇相同的 AI 模型
3. 填入 API Key（如果使用 OpenAI 或 Claude）
4. 點擊保存

### 第 5 步：開始使用

1. 訪問 [104 人力銀行](https://www.104.com.tw)
2. 搜尋職位
3. 看著紅色 ⚠️ 標記就是「屎缺」

---

## macOS / Linux 用戶

```bash
# 1. 啟動後端
chmod +x startup.sh
./startup.sh

# 2-5. 同上
```

---

## 常見問題速解

| 問題 | 解決方案 |
|------|--------|
| 擴充功能無法連接 | 確保後端運行中 (`http://localhost:5000`) |
| 職位標記不顯示 | 重新加載擴充功能 (chrome://extensions 刷新) |
| 速度慢 | 使用本地模型 (Ollama) 或 Claude |
| 無法部署 | 查看 [SETUP_GUIDE.md](SETUP_GUIDE.md) |

---

## 下一步

- 📖 查看 [完整設置指南](SETUP_GUIDE.md)
- 🤔 查看 [FAQ](FAQ.md)
- 💻 查看 [開發者指南](DEVELOPER_GUIDE.md)

---

💡 **提示**: 首次運行會自動安裝依賴，請耐心等待。
