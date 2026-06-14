/**
 * 台灣求職避雷器 - 後台服務
 * 負責與後端 API 通訊、資料緩存、事件管理
 * 支援：後端 Flask API 模式 / 直接 Ollama 模式 / 本地 LSTM 模型
 */

const DEFAULT_BACKEND_URL = 'http://localhost:5000';
const DEFAULT_OLLAMA_URL  = 'http://localhost:11434';
const CACHE_DURATION      = 3600000; // 1 小時

// ── Popup log 橋接 ────────────────────────────────────────
function bgLog(type, msg) {
  const levels = { info: 'log', warn: 'warn', error: 'error', ok: 'log', dim: 'log' };
  console[levels[type] || 'log'](`[避雷器] ${msg}`);
  chrome.runtime.sendMessage({ type: 'BG_LOG', logType: type, msg }).catch(() => {});
}

// 首次安裝提示
chrome.storage.local.get(['apiKey', 'directMode', 'backendUrl'], (result) => {
  if (!result.apiKey && !result.directMode && !result.backendUrl) {
    bgLog('info', '請至「連線」頁設定後端 API 或 Ollama 端口');
  }
});

// ── 連線設定 ──────────────────────────────────────────────
function getConnectionConfig() {
  return new Promise((resolve) => {
    chrome.storage.local.get(
      ['backendUrl', 'ollamaUrl', 'ollamaModel', 'directMode', 'useLstm'],
      (result) => resolve({
        backendUrl:  result.backendUrl  || DEFAULT_BACKEND_URL,
        ollamaUrl:   result.ollamaUrl   || DEFAULT_OLLAMA_URL,
        ollamaModel: result.ollamaModel || 'llama2',
        directMode:  result.directMode  === true,
        useLstm:     result.useLstm     !== false   // 預設開啟
      })
    );
  });
}

// ── 消息監聽 ──────────────────────────────────────────────
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

  if (request.type === 'CHECK_LSTM_STATUS') {
    checkLstmStatus()
      .then(status => sendResponse({ success: true, ...status }))
      .catch(() => sendResponse({ success: false, ready: false }));
    return true;
  }
});

// ══════════════════════════════════════════════════════════
//  主分析流程
// ══════════════════════════════════════════════════════════

async function analyzeJob(jobData) {
  const cfg = await getConnectionConfig();
  const { jobTitle } = jobData;
  bgLog('dim', `分析「${jobTitle}」…`);

  // ── LSTM 優先（預設開啟）────────────────────────────
  if (cfg.useLstm) {
    const lstm = await callLstmPredict(jobData, cfg.backendUrl);
    if (lstm) {
      // LSTM 成功：直接以 LSTM 為主要結果，不再呼叫後端
      const base = { riskLevel: 'unknown', score: 50, reasons: [], recommendation: '', source: 'lstm' };
      return mergeLstmResult(base, lstm);
    }
    bgLog('warn', 'LSTM 不可用，退回後端 / 本地規則');
  }

  // ── 直接 Ollama 模式（LSTM 失敗時的備援）────────────
  if (cfg.directMode) {
    return analyzeJobDirect(jobData, cfg);
  }

  // ── 後端 API 模式（LSTM 失敗時的備援）───────────────
  try {
    const { salary, company, description } = jobData;
    const salaryStats = await getSalaryStats(jobTitle, cfg.backendUrl);

    const response = await fetch(`${cfg.backendUrl}/api/analyze`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ jobTitle, salary, company, description, salaryStats }),
      signal:  AbortSignal.timeout(8000)
    });

    if (!response.ok) throw new Error(`後端 API 回應 ${response.status}`);
    const base = await response.json();
    bgLog('ok', `後端分析完成：${jobTitle} → ${base.riskLevel} (${base.score}分)`);
    return base;

  } catch (e) {
    bgLog('warn', `後端不可用 (${e.message})，改用本地規則`);
    return analyzeJobLocal(jobData);
  }
}

// ══════════════════════════════════════════════════════════
//  LSTM 相關
// ══════════════════════════════════════════════════════════

/**
 * 呼叫後端 /api/lstm/predict
 * 回傳 { label, class, probabilities } 或 null（失敗時）
 */
async function callLstmPredict(jobData, backendUrl) {
  try {
    const { jobTitle, salary = '', description = '' } = jobData;
    const { salaryMin, salaryMax } = parseSalaryText(salary);

    const payload = {
      jobTitle,
      salaryMin,
      salaryMax,
      salaryText:   salary,
      descSnippet:  description.substring(0, 400),
      overtimeHint: detectOvertimeHint(description),
    };

    const res = await fetch(`${backendUrl}/api/lstm/predict`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
      signal:  AbortSignal.timeout(6000)
    });

    if (!res.ok) throw new Error(`LSTM API ${res.status}`);
    const data = await res.json();

    if (data.error) throw new Error(data.error);
    bgLog('ok', `LSTM 預測：${jobTitle} → ${data.class} (好缺:${data.probabilities?.['好缺'] ?? '?'})`);
    return data;

  } catch (e) {
    bgLog('warn', `LSTM 預測失敗 (${e.message})，跳過`);
    return null;
  }
}

/**
 * 把 LSTM 結果合併進基礎分析結果
 * LSTM class 為主要分類依據，覆寫 riskLevel / score
 */
function mergeLstmResult(base, lstm) {
  const classMap = {
    '好缺': { riskLevel: 'low',    score: 80, recommendation: '條件良好，值得投遞' },
    '普通': { riskLevel: 'medium', score: 55, recommendation: '審慎考慮，面試時仔細確認工作條件' },
    '屎缺': { riskLevel: 'high',   score: 20, recommendation: '不建議投遞，建議繼續尋找其他機會' },
  };
  const override = classMap[lstm.class] || {};
  return {
    ...base,
    ...override,                            // LSTM 覆寫 riskLevel / score / recommendation
    lstmClass:         lstm.class,
    lstmLabel:         lstm.label,
    lstmProbabilities: lstm.probabilities,
    lstmFeatures:      lstm.features,
    source:            'lstm',
  };
}

/** 確認 LSTM 模型是否就緒 */
async function checkLstmStatus() {
  const cfg = await getConnectionConfig();
  try {
    const res = await fetch(`${cfg.backendUrl}/api/lstm/status`, {
      signal: AbortSignal.timeout(4000)
    });
    if (!res.ok) return { ready: false, message: `後端回應 ${res.status}` };
    return await res.json();
  } catch (e) {
    return { ready: false, message: e.message };
  }
}

// ══════════════════════════════════════════════════════════
//  薪資 / 加班解析工具
// ══════════════════════════════════════════════════════════

function parseSalaryText(text = '') {
  if (!text) return { salaryMin: 0, salaryMax: 0 };
  const nums = (text.match(/\d[\d,]*/g) || [])
    .map(n => parseInt(n.replace(/,/g, ''), 10))
    .filter(n => n > 0);
  if (!nums.length) return { salaryMin: 0, salaryMax: 0 };
  return { salaryMin: Math.min(...nums), salaryMax: Math.max(...nums) };
}

const _OT_HIGH   = ['責任制', '無休假', '需配合加班', '假日加班', '輪班', '大夜班'];
const _OT_MEDIUM = ['偶爾加班', '彈性工時', '專案加班'];
const _OT_LOW    = ['準時下班', '不需加班', '週休二日'];

function detectOvertimeHint(text = '') {
  if (_OT_HIGH.some(w => text.includes(w)))   return 3;
  if (_OT_MEDIUM.some(w => text.includes(w))) return 2;
  if (_OT_LOW.some(w => text.includes(w)))    return 0;
  return 1;
}

// ══════════════════════════════════════════════════════════
//  本地規則分析（後端不可用時的 fallback）
// ══════════════════════════════════════════════════════════

function analyzeJobLocal(jobData) {
  const { jobTitle, salary, description = '' } = jobData;
  const reasons = [];
  let score = 60;

  if (salary === '薪資未標示') {
    reasons.push('薪資未公開（可能不透明）');
    score -= 10;
  } else if (/待遇面議/.test(salary)) {
    reasons.push('待遇面議，無法評估薪資合理性');
    score -= 5;
  } else {
    const nums = salary.match(/\d[\d,]*/g);
    if (nums) {
      const parsed = nums.map(n => parseInt(n.replace(/,/g, ''), 10)).filter(n => n > 1000);
      const minSal = parsed.length > 0 ? Math.min(...parsed) : 0;
      if (minSal > 0 && minSal < 30000) {
        reasons.push(`月薪 ${minSal.toLocaleString()} 低於基本薪資標準`);
        score -= 25;
      } else if (minSal > 0 && minSal < 38000) {
        reasons.push(`月薪 ${minSal.toLocaleString()} 偏低`);
        score -= 10;
      }
    }
  }

  const redFlags = [
    ['責任制', 15], ['無休假', 15], ['高壓', 10],
    ['急徵', 5],   ['立即上班', 5], ['配合度高', 8],
    ['無經驗可', 3], ['多工', 5],   ['接受加班', 10], ['彈性工時', 5]
  ];
  for (const [flag, penalty] of redFlags) {
    if (description.includes(flag)) {
      reasons.push(`描述含「${flag}」`);
      score -= penalty;
    }
  }

  if (/助理|行政|兼職/.test(jobTitle) && score > 50) score -= 5;

  score = Math.max(0, Math.min(100, score));
  const riskLevel = score < 35 ? 'high' : score < 60 ? 'medium' : 'low';
  const recommendations = {
    high:   '不建議投遞，建議繼續尋找其他機會',
    medium: '審慎考慮，面試時仔細確認工作條件',
    low:    '條件相對合理，值得進一步了解'
  };

  bgLog('ok', `本地分析完成：${jobTitle} → ${riskLevel} (${score}分)`);
  return {
    riskLevel,
    score,
    reasons: reasons.length ? reasons : ['無明顯風險因素（本地規則分析）'],
    recommendation: recommendations[riskLevel],
    source: 'local'
  };
}

// ══════════════════════════════════════════════════════════
//  直接 Ollama 模式
// ══════════════════════════════════════════════════════════

async function analyzeJobDirect(jobData, cfg) {
  const { jobTitle, salary, description } = jobData;
  const prompt = `你是台灣職場分析專家，請分析以下職缺的風險：
職位：${jobTitle}
薪資：${salary}
描述：${(description || '').substring(0, 400)}

請以 JSON 格式回答（只輸出 JSON，不要其他文字）：
{"riskLevel":"high|medium|low","score":0-100,"reasons":["原因1","原因2"],"recommendation":"建議..."}`;

  bgLog('info', `送出 Ollama 請求 (${cfg.ollamaModel})，等待回應…`);
  const response = await fetch(`${cfg.ollamaUrl}/api/generate`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ model: cfg.ollamaModel, prompt, stream: false, format: 'json' }),
    signal:  AbortSignal.timeout(30000)
  });

  if (!response.ok) throw new Error(`Ollama 回應 ${response.status}`);
  const data = await response.json();

  try {
    const parsed = JSON.parse(data.response);
    bgLog('ok', `Ollama 分析完成 → ${parsed.riskLevel} (${parsed.score}分)`);
    return parsed;
  } catch {
    bgLog('error', `Ollama 回應無法解析為 JSON`);
    return {
      riskLevel: 'unknown', score: 50,
      reasons: ['AI 分析完成，但無法解析結果'],
      recommendation: data.response?.substring(0, 200) || '請檢查 Ollama 模型輸出'
    };
  }
}

// ══════════════════════════════════════════════════════════
//  薪資統計（快取）
// ══════════════════════════════════════════════════════════

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
