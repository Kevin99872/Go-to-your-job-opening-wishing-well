# 常見問題 (FAQ)

## 安裝與設置

### Q1: 支援哪些作業系統？

**A:** 所有主流作業系統：
- ✅ Windows 7+
- ✅ macOS 10.12+
- ✅ Linux (任何發行版)

### Q2: 需要安裝什麼軟體？

**A:** 最少需要：
- Python 3.8+
- Chrome 或 Edge 瀏覽器

可選：
- Git (用於克隆項目)
- VS Code (用於開發)

### Q3: 如何檢查 Python 版本？

```bash
python --version
```

如果輸出 3.8 或更高，說明版本正確。

## 使用相關

### Q4: 擴充功能無法連接後端怎麼辦？

**A:** 檢查以下步驟：

1. 確保後端服務正在運行
   ```bash
   # 應該看到 "Running on http://127.0.0.1:5000"
   ```

2. 確保防火牆未阻止 localhost:5000
   - Windows: 檢查 Windows 防火牆
   - macOS: 系統偏好設置 > 安全性與隱私

3. 重新加載擴充功能
   - Chrome: chrome://extensions > 刷新按鈕

### Q5: 職位標記不顯示怎麼辦？

**A:** 

1. 確保擴充功能已安裝
2. 進入 104 職位頁面
3. 打開開發者工具 (F12) 檢查控制台錯誤
4. 重新加載頁面 (Ctrl+R)

### Q6: 如何查看詳細錯誤信息？

**A:**

後端：
```bash
# 後端會在控制台打印日誌
# 尋找 ERROR 標記的消息
```

擴充功能：
1. 打開 Chrome DevTools (F12)
2. 進入 "Console" 標籤
3. 查看紅色錯誤消息

## AI 模型相關

### Q7: 應該使用哪個 AI 模型？

**A:** 根據你的需求選擇：

| 模型 | 優點 | 缺點 | 建議 |
|------|------|------|------|
| **OpenAI** | 準確度最高 | 需要付費 API | 普通用戶 |
| **Claude** | 性能均衡 | 需要付費 API | 高級用戶 |
| **本地 (Ollama)** | 免費、隱私 | 需要本地資源 | 開發者 |

### Q8: OpenAI API 要花多少錢？

**A:** 大約每 100 次分析花費 $0.01-0.05（使用 GPT-3.5-turbo）

免費方式：
- 使用本地模型 (Ollama)
- 使用 API 免費額度

### Q9: 如何安裝 Ollama？

**A:**

1. 訪問 https://ollama.ai
2. 下載適合你作業系統的版本
3. 安裝並運行
4. 下載模型：
   ```bash
   ollama pull llama2
   ```
5. 在 `.env` 中配置：
   ```
   MODEL_TYPE=local
   LOCAL_URL=http://localhost:11434
   ```

### Q10: 本地模型性能慢怎麼辦？

**A:** 

1. 使用更小的模型
   ```bash
   ollama pull mistral  # 比 llama2 更快
   ```

2. 增加硬件資源
   - 升級 GPU
   - 增加 RAM

3. 使用 API 模型（如 OpenAI）

## 職位分析相關

### Q11: 如何判斷職位風險等級？

**A:** 系統考慮以下因素：

- 📊 **薪資水平**
  - 與業界中位數比較
  - 與最低標準比較

- 📝 **職位描述**
  - 檢查「急徵」、「責任制」等關鍵詞
  - 檢查工作時間要求

- 🏢 **公司信息**
  - 公司規模
  - 業界聲譽

### Q12: 薪資統計數據準確嗎？

**A:** 

- 數據來自 104 網站的職位信息
- 基於最近 90 天的職位發布
- 定期更新（每天一次）

建議：
- 結合多個平台數據
- 參考同行的意見
- 考慮本地市場變化

### Q13: 為什麼某個職位被標記為「屎缺」？

**A:** 可能的原因：

1. **薪資過低** - 低於業界標準 20% 以上
2. **要求過高** - 職位描述包含「急徵」、「責任制」等
3. **公司聲譽** - 已知存在勞工相關問題

懸停在標記上可以看到具體原因。

## 數據與隱私

### Q14: 我的數據會被保存嗎？

**A:** 

✅ **不會** - 除非：
- 使用 API 模型（OpenAI 會根據其隱私政策保存）
- 自己選擇保存

✅ **本地數據**：
- 爬蟲數據保存在 `backend/data/` 文件夾
- 瀏覽器緩存存儲在本地存儲

### Q15: 如何刪除我的數據？

**A:**

1. **瀏覽器數據**：
   ```
   開發者工具 (F12) > Application > Clear Site Data
   ```

2. **爬蟲數據**：
   ```bash
   # 刪除 data 文件夾
   rm -rf backend/data/
   ```

## 問題排除

### Q16: 爬蟲提取不到職位信息？

**A:** 

可能原因：
- 104 網站結構已變化
- HTML 選擇器需要更新

解決：
1. 報告 [Issue](https://github.com/Kevin99872/Go-to-your-job-opening-wishing-well/issues)
2. 等待更新
3. 或自己提交 PR 修復

### Q17: 後端無法啟動？

**A:** 檢查：

1. Python 版本正確
2. 依賴已安裝
3. 端口 5000 未被占用
   ```bash
   # Windows
   netstat -ano | findstr :5000
   
   # macOS/Linux
   lsof -i :5000
   ```

4. 查看錯誤日誌
   ```bash
   python app.py  # 直接運行看錯誤
   ```

### Q18: 如何報告 Bug？

**A:**

1. 訪問 https://github.com/Kevin99872/Go-to-your-job-opening-wishing-well/issues
2. 點擊「New Issue」
3. 提供：
   - Bug 描述
   - 複現步驟
   - 預期結果 vs 實際結果
   - 系統信息（OS、Python 版本等）
   - 錯誤日誌

## 功能相關

### Q19: 支援哪些職位類別？

**A:** 

目前：
- ✅ C# 軟體工程師
- ✅ .NET 軟體工程師

計劃中：
- 🔄 所有技術職位
- 🔄 其他職位類別

### Q20: 可以分析其他網站的職位嗎？

**A:** 

目前只支援 104 人力銀行。

未來計畫支援：
- 其他人力銀行平台
- 自定義公司招聘頁面

## 貢獻相關

### Q21: 如何貢獻代碼？

**A:**

1. Fork 項目
2. 創建特性分支
3. 提交代碼
4. 發起 Pull Request

詳見 [開發者指南](DEVELOPER_GUIDE.md)

### Q22: 如何報告功能需求？

**A:**

1. 訪問 [Discussions](https://github.com/Kevin99872/Go-to-your-job-opening-wishing-well/discussions)
2. 或提交 [Issue](https://github.com/Kevin99872/Go-to-your-job-opening-wishing-well/issues)

## 🔌 連線設定相關

### Q23: 「🔌 連線」頁在哪裡？

**A:** 點擊工具列的 🎯 圖示後，點選第二個標籤「🔌 連線」即可看到後端 API 與 Ollama 的連線設定。

### Q24: 後端 API 端口可以換掉嗎？

**A:** 可以。在「🔌 連線」頁的「後端伺服器 URL」輸入你的自訂地址（例如 `http://192.168.1.10:8080`），點擊「測試」確認後保存即可。擴充功能會自動使用新的地址。

### Q25: 「直接模式」是什麼？什麼時候使用？

**A:** 開啟直接模式後，擴充功能會**繞過後端**，直接向 Ollama 發送職位分析請求。

適合的情境：
- 只想用本地 AI 分析職位，不需要薪資統計功能
- 不想啟動 Flask 後端
- 想要更快的回應速度

注意：直接模式下**薪資統計功能不可用**，分析結果僅來自 Ollama 的語言理解能力。

### Q26: 直接模式下 Ollama 回應很慢怎麼辦？

**A:** 幾個加速方案：

1. 換用較小的模型：
   ```bash
   ollama pull mistral      # 比 llama2 快約 2x
   ollama pull phi3:mini    # 更輕量
   ```

2. 在「🔌 連線」頁的模型選單切換至較小的已安裝模型

3. 確認 Ollama 有使用 GPU（若電腦有獨顯，Ollama 會自動偵測）

### Q27: 擴充功能顯示 Ollama 無法連線，但 Ollama 確實在執行？

**A:** 常見原因：

1. **Ollama 預設只監聽 127.0.0.1**，Chrome 擴充功能的請求需要對應的 host_permissions。  
   → 本專案已在 `manifest.json` 中加入 `http://localhost/*`，請確認你使用的是 `http://localhost:11434` 而非 `http://127.0.0.1:11434`（兩者均可）。

2. **Ollama CORS 問題**：Ollama 預設允許本地來源，通常不需要額外設定。  
   → 若仍有問題，可改用「後端代理模式」（關閉直接模式），透過 `/api/ollama/generate` 端點中轉請求。

3. **防火牆攔截**：確認 Windows 防火牆或防毒軟體未封鎖 port 11434。

---

**還有問題？**

- 💬 GitHub Issues: https://github.com/Kevin99872/Go-to-your-job-opening-wishing-well/issues
- 📖 開發者指南: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)

