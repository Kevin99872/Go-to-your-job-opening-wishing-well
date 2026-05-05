# 台灣求職避雷器 - 開發者指南

## 🛠️ 開發環境設置

### 前置要求

- Python 3.8+
- Node.js 14+ (可選，用於前端工具)
- Git

### 安裝開發依賴

```bash
cd backend

# 創建虛擬環境
python -m venv venv

# 激活虛擬環境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 安裝開發工具
pip install pytest pytest-cov black flake8 mypy
```

## 📝 代碼風格

我們遵循 PEP 8 規範：

```bash
# 代碼格式化
black backend/src

# 風格檢查
flake8 backend/src

# 類型檢查
mypy backend/src
```

## 🧪 測試

### 運行測試

```bash
# 所有測試
python -m pytest

# 特定測試
python -m pytest backend/tests.py::TestJobAnalyzer

# 帶覆蓋率報告
pytest --cov=backend/src --cov-report=html
```

### 添加新測試

在 `backend/tests.py` 中添加新的測試類：

```python
class TestNewFeature(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
```

## 🚀 開發工作流

### 1. 建立特性分支

```bash
git checkout -b feature/new-feature
```

### 2. 進行開發

編輯文件並定期提交：

```bash
git add .
git commit -m "Add new feature"
```

### 3. 測試

```bash
# 運行測試
pytest

# 代碼檢查
black --check backend/src
flake8 backend/src
```

### 4. 提交 PR

推送分支並創建 Pull Request

## 📚 API 開發指南

### 添加新端點

編輯 `backend/app.py`：

```python
@app.route('/api/new-endpoint', methods=['POST'])
def new_endpoint():
    """新端點說明"""
    try:
        data = request.json
        
        # 處理邏輯
        result = do_something(data)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f'錯誤: {str(e)}')
        return jsonify({'error': str(e)}), 500
```

### 端點命名慣例

- `GET /api/resource` - 獲取資源列表或詳情
- `POST /api/resource` - 創建資源
- `PUT /api/resource/:id` - 更新資源
- `DELETE /api/resource/:id` - 刪除資源

## 🐛 常見問題

### 問題: ModuleNotFoundError: No module named 'flask'

**解決:**
```bash
# 確保虛擬環境已激活
source venv/bin/activate  # 或 Windows 的 venv\Scripts\activate

# 重新安裝依賴
pip install -r requirements.txt
```

### 問題: 爬蟲無法解析 HTML

**解決:**
- 檢查 104 網站的 HTML 結構是否變化
- 更新 `crawler.py` 中的 CSS 選擇器
- 使用瀏覽器開發者工具檢查元素

### 問題: API Key 無效

**解決:**
- 檢查 `.env` 文件中的 API Key
- 確保 API Key 尚未過期
- 檢查模型配置是否正確

## 📊 性能優化

### 爬蟲優化

```python
# 使用線程池加速爬取
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(fetch_page, url) for url in urls]
```

### 緩存優化

```python
# 使用 Redis 緩存薪資統計
import redis

cache = redis.Redis(host='localhost', port=6379)
cached_data = cache.get(f'salary_{job_title}')
```

## 🔒 安全最佳實踐

- ✅ 不要在代碼中硬編碼 API Key
- ✅ 使用環境變數存儲敏感信息
- ✅ 驗證所有用戶輸入
- ✅ 不要將日誌中的敏感數據打印出來
- ✅ 使用 HTTPS 進行 API 通訊

## 📖 文檔

### 生成 API 文檔

```bash
# 使用 Swagger 自動生成
pip install flask-restx
```

### 更新 README

修改 `README.md` 和 `SETUP_GUIDE.md`

## 🚀 部署

### 本地部署

```bash
python startup.py
```

### Docker 部署 (計劃中)

```bash
docker-compose up
```

### 雲端部署 (計劃中)

- Heroku
- AWS Lambda
- Google Cloud

## 📞 獲得幫助

- 查看 [常見問題](FAQ.md)
- 提交 [Issue](https://github.com/Kevin99872/Go-to-your-job-opening-wishing-well/issues)
- 加入 [討論](https://github.com/Kevin99872/Go-to-your-job-opening-wishing-well/discussions)

---

感謝你的貢獻！
