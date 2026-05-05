# 📦 部署指南

## 本地部署（已完成）

見 [快速開始](QUICKSTART.md)

## 雲端部署

### Option 1: Heroku（已停止免費）

### Option 2: Railway

```bash
# 1. 創建 Procfile
echo "web: gunicorn app:app" > Procfile

# 2. 部署
railway up
```

### Option 3: Render

1. 連接 GitHub 倉庫
2. 創建新 Web Service
3. 選擇 Python
4. 設置命令：`gunicorn app:app`
5. 添加環境變數

### Option 4: Docker (推薦)

#### 創建 Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
```

#### 創建 docker-compose.yml

```yaml
version: '3'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      MODEL_TYPE: openai
      API_KEY: ${API_KEY}
    volumes:
      - ./data:/app/data
```

#### 運行

```bash
docker-compose up
```

## GitHub Pages（用於文檔）

```bash
# 1. 創建 docs 文件夾
mkdir docs

# 2. 複製文檔
cp README.md docs/index.md
cp SETUP_GUIDE.md docs/setup.md
cp FAQ.md docs/faq.md

# 3. 推送
git add docs/
git commit -m "Add documentation"
git push
```

在 GitHub 倉庫設置中：
- Settings > Pages
- Source: main branch /docs folder

## 環境變數配置

### 在雲端平台上設置

```env
# 必需
MODEL_TYPE=openai
API_KEY=sk-your-key

# 可選
LOCAL_URL=http://localhost:11434
FLASK_ENV=production
DEBUG=0
```

## 數據庫部署（未來功能）

### PostgreSQL

```bash
# 安裝依賴
pip install psycopg2-binary sqlalchemy

# 設置連接
DATABASE_URL=postgresql://user:password@localhost/db_name
```

### MongoDB

```bash
# 安裝依賴
pip install pymongo

# 設置連接
MONGODB_URL=mongodb+srv://user:password@cluster.mongodb.net/db_name
```

## 監控與日誌

### 使用 Sentry（錯誤追蹤）

```bash
pip install sentry-sdk

# 在 app.py 中添加
import sentry_sdk
sentry_sdk.init("your-sentry-dsn")
```

### 使用 Datadog（應用監控）

```bash
pip install datadog
```

## CI/CD 配置

### GitHub Actions

創建 `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install pytest
      
      - name: Run tests
        run: pytest backend/
      
      - name: Deploy
        run: |
          # 你的部署命令
```

## 擴充功能部署

### Chrome Web Store

1. 創建開發者帳戶（$5）
2. 上傳 zip 文件
3. 填寫元數據
4. 等待審核（通常 1-3 小時）

### Edge Add-ons Store

1. 訪問 [Partner Center](https://partner.microsoft.com/edge)
2. 上傳擴充功能
3. 填寫詳細信息
4. 提交審核

## 生產環境檢查清單

- ✅ 測試完所有功能
- ✅ 更新版本號
- ✅ 編寫變更日誌
- ✅ 設置環境變數
- ✅ 備份數據庫
- ✅ 設置監控和日誌
- ✅ 測試回滾程序
- ✅ 通知用戶
- ✅ 監控性能

## 故障排除

### 部署後無法連接

1. 檢查環境變數
2. 查看日誌
3. 檢查 CORS 設置
4. 驗證 API Key

### 性能問題

1. 啟用緩存
2. 使用 CDN
3. 優化數據庫查詢
4. 增加 CPU/RAM

---

需要幫助？查看 [FAQ](FAQ.md)
