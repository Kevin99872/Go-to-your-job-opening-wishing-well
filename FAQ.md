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

---

**還有問題？**

- 📧 Email: [你的郵箱]
- 💬 Discord: [你的 Discord 伺服器]
- 📞 GitHub Issues: https://github.com/Kevin99872/Go-to-your-job-opening-wishing-well/issues

