# 📦 部署指南

## 本地部署

見 [QUICKSTART.md](QUICKSTART.md)

---

## 雲端部署

### Option 1: Railway

```bash
# 建立 Procfile（在 backend/ 目錄下）
echo "web: gunicorn app:app" > backend/Procfile

# 推送後在 Railway Dashboard 設定環境變數
railway up
```

### Option 2: Render

1. 連接 GitHub 倉庫
2. 建立新 **Web Service**，選擇 Python
3. Root Directory：`backend`
4. Start Command：`gunicorn app:app`
5. 在 Environment 頁新增環境變數（見下方）

### Option 3: Docker（推薦用於自架）

**Dockerfile**（放在專案根目錄）：

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY backend/ .

EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "--workers", "2", "app:app"]
```

**docker-compose.yml**（包含後端 + Ollama）：

```yaml
version: '3.9'
services:
  backend:
    build: .
    ports:
      - "5000:5000"
    environment:
      MODEL_TYPE: ${MODEL_TYPE:-local}
      API_KEY: ${API_KEY:-}
      LOCAL_URL: http://ollama:11434
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

```bash
# 啟動所有服務
docker compose up -d

# 下載模型（首次）
docker compose exec ollama ollama pull mistral
```

---

## 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `MODEL_TYPE` | `openai` / `claude` / `local` | `openai` |
| `API_KEY` | OpenAI 或 Claude API Key | — |
| `LOCAL_URL` | Ollama 服務地址 | `http://localhost:11434` |
| `FLASK_ENV` | `production` / `development` | `development` |
| `DEBUG` | `0` 關閉除錯模式 | `1` |

---

## CI/CD（GitHub Actions）

建立 `.github/workflows/deploy.yml`：

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - run: python -m pytest backend/
      # 加入你的部署步驟（Railway / Render CLI 等）
```

---

## 監控（可選）

```bash
# Sentry 錯誤追蹤
pip install sentry-sdk[flask]
```

```python
# backend/app.py 最上方加入
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
sentry_sdk.init(dsn="your-sentry-dsn", integrations=[FlaskIntegration()])
```

---

需要幫助？查看 [FAQ.md](FAQ.md) 或 [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
