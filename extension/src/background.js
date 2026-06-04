/**
 * 台灣求職避雷器 - 後台服務
 * 負責與後端 API 通訊、資料緩存、事件管理
 * 支援：後端 Flask API 模式 / 直接 Ollama 模式
 */

const DEFAULT_BACKEND_URL = 'http://localhost:5000';
const DEFAULT_OLLAMA_URL  = 'http://localhost:11434';
const CACHE_DURATION = 3600000; // 1 小時

// 首次安裝提示
chrome.storage.local.get(['apiKey', 'directMode', 'backendUrl'], (result) => {
  if (!result.apiKey && !result.directMode && !result.backendUrl) {
    console.log('請至「🔌 連線」頁設定後端 API 或 Ollama 端口');
  }
});

// ── 工具：讀取連線設定 ─────────────────────────────────────
function getConnectionConfig() {
  return new Promise((resolve) => {
    chrome.storage.local.get(
      ['backendUrl', 'ollamaUrl', 'ollamaModel', 'directMode'],
      (result) => resolve({
        backendUrl:  result.backendUrl  || DEFAULT_BACKEND_URL,
        ollamaUrl:   result.ollamaUrl   || DEFAULT_OLLAMA_URL,
        ollamaModel: result.ollamaModel || 'llama2',
        directMode:  result.directMode  === true
      })
    );
  });
}

// ── 消息監聽 ───────────────────────────────────────────────
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'ANALYZE_JOB') {
    analyzeJob(request.jobData)
      .then(result => sendResponse({ success: true, result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.type === 'GET_SALARY_STATS') {
    getSalaryStats(request.jobTitle)
      .then(result => sendResponse({ success: true, result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }
});

// ── 分析職位（自動選擇模式）──────────────────────────────
async function analyzeJob(jobData) {
  const { jobTitle, salary, company, description } = jobData;
  const cfg = await getConnectionConfig();

  if (cfg.directMode) {
    return analyzeJobDirect(jobData, cfg);
  }

  // 後端 API 模式
  const salaryStats = await getSalaryStats(jobTitle, cfg.backendUrl);

  const response = await fetch(`${cfg.backendUrl}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jobTitle, salary, company, description, salaryStats })
  });

  if (!response.ok) throw new Error(`後端 API 回應 ${response.status}`);
  return response.json();
}

// ── 直接 Ollama 模式（不經後端）──────────────────────────
async function analyzeJobDirect(jobData, cfg) {
  const { jobTitle, salary, description } = jobData;

  const prompt = `你是台灣職場分析專家，請分析以下職缺的風險：
職位：${jobTitle}
薪資：${salary}
描述：${(description || '').substring(0, 400)}

請以 JSON 格式回答（只輸出 JSON，不要其他文字）：
{
  "riskLevel": "high|medium|low",
  "score": 0-100,
  "reasons": ["原因1", "原因2"],
  "recommendation": "建議..."
}`;
  console.log("已開始分析職缺，等待 Ollama 回應...");
  const response = await fetch(`${cfg.ollamaUrl}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: cfg.ollamaModel,
      prompt,
      stream: false,
      format: 'json'
    }),
    signal: AbortSignal.timeout(30000)
  });

  if (!response.ok) throw new Error(`Ollama 回應 ${response.status}`);

  const data = await response.json();
  try {
    return JSON.parse(data.response);
  } catch {
    // 若模型未輸出合法 JSON，做基本回退
    return {
      riskLevel: 'unknown',
      score: 50,
      reasons: ['AI 分析完成，但無法解析結果'],
      recommendation: data.response?.substring(0, 200) || '請檢查 Ollama 模型輸出'
    };
    console.error('Ollama 回應無法解析為 JSON:', data.response);
  }
}

// ── 獲取薪資統計 ──────────────────────────────────────────
async function getSalaryStats(jobTitle, backendUrl) {
  const cacheKey = `salary_stats_${jobTitle}`;

  return new Promise(async (resolve) => {
    chrome.storage.local.get(cacheKey, async (result) => {
      const cached = result[cacheKey];
      if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
        return resolve(cached.data);
      }

      try {
        const url = backendUrl || DEFAULT_BACKEND_URL;
        const res = await fetch(
          `${url}/api/salary-stats?jobTitle=${encodeURIComponent(jobTitle)}`,
          { signal: AbortSignal.timeout(8000) }
        );
        const data = await res.json();
        chrome.storage.local.set({ [cacheKey]: { data, timestamp: Date.now() } });
        resolve(data);
      } catch {
        resolve(null);
      }
    });
  });
}
