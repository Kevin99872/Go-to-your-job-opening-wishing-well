/**
 * 台灣求職避雷器 - Content Script
 * 掃描 104 職缺卡片 → 送 background 分析（規則 + LSTM）→ 渲染雙徽章
 */

// ══════════════════════════════════════════════════════
// 狀態
// ══════════════════════════════════════════════════════
const analyzedSet    = new Set();   // 已送分析的 jobId
const titleResultMap = new Map();   // jobId → result

// ══════════════════════════════════════════════════════
// Log
// ══════════════════════════════════════════════════════
function cLog(type, msg) {
  const lvl = type === 'error' ? 'error' : type === 'warn' ? 'warn' : 'log';
  console[lvl](`[避雷器] ${msg}`);
  if (chrome.runtime?.id) {
    chrome.runtime.sendMessage({ type: 'BG_LOG', logType: type, msg }).catch(() => {});
  }
}

// ══════════════════════════════════════════════════════
// 薪資解析（從文字取出 min / max，單位：元）
// ══════════════════════════════════════════════════════
function parseSalaryFromText(text = '') {
  if (!text) return { min: 0, max: 0 };
  // 移除千分位，取所有數字段
  const nums = [...text.replace(/,/g, '').matchAll(/\d+/g)]
    .map(m => parseInt(m[0]))
    .filter(n => n > 1000);        // 過濾掉日期/編號等小數字
  if (!nums.length) return { min: 0, max: 0 };
  let lo = Math.min(...nums);
  let hi = Math.max(...nums);
  // 萬元單位（如 4萬～6萬）
  if (/萬/.test(text)) { lo *= 10000; hi *= 10000; }
  return { min: lo, max: hi };
}

// ══════════════════════════════════════════════════════
// 加班指數偵測（0=低 1=中低 2=中高 3=高）
// ══════════════════════════════════════════════════════
const OT_HIGH   = ['責任制','無休假','需配合加班','假日加班','輪班','大夜班','無限加班'];
const OT_MEDIUM = ['偶爾加班','彈性工時','專案加班','不定時'];
const OT_LOW    = ['準時下班','不需加班','週休二日','Work-Life'];

function detectOvertimeHint(text = '') {
  if (OT_HIGH.some(w => text.includes(w)))   return 3;
  if (OT_MEDIUM.some(w => text.includes(w))) return 2;
  if (OT_LOW.some(w => text.includes(w)))    return 0;
  return 1;
}

// ══════════════════════════════════════════════════════
// 從職缺卡片 DOM 擷取結構化資料
// ══════════════════════════════════════════════════════
function extractJobDataFromCard(link, card) {
  // 薪資文字：優先找含 salary/pay/薪 class 的子元素
  const salaryEl =
    card?.querySelector('[class*="salary"],[class*="pay"],[class*="wage"],[class*="b-list-tag"]') ||
    card?.querySelector('[class*="tag"]');
  const salaryText = salaryEl?.textContent.trim() || '';
  const { min: salaryMin, max: salaryMax } = parseSalaryFromText(salaryText);

  // 公司名稱
  const companyEl =
    card?.querySelector('[class*="cust"],[class*="company"],[class*="corp"],[class*="b-company"]');
  const company = (companyEl?.textContent.trim() || '').substring(0, 60);

  // 完整卡片文字（供加班偵測 & AI 分析）
  const fullText = card?.textContent?.replace(/\s+/g, ' ')?.trim() || '';

  return {
    salary:      salaryText || '薪資未標示',
    salaryMin,
    salaryMax,
    company,
    description: fullText.substring(0, 500),
    overtimeHint: detectOvertimeHint(fullText),
  };
}

// ══════════════════════════════════════════════════════
// 主掃描：找所有 /job/ 連結
// ══════════════════════════════════════════════════════
function scanJobLinks() {
  if (!chrome.runtime?.id) return 0;

  const links = document.querySelectorAll('a[href*="/job/"]');
  let newCount = 0;

  for (const link of links) {
    const href  = link.getAttribute('href') || '';
    const jobId = href.match(/\/job\/([a-zA-Z0-9]+)/)?.[1];
    if (!jobId || analyzedSet.has(jobId)) continue;

    const title = link.textContent.trim();
    if (!title || title.length < 2 || title.length > 60) continue;

    // 向上找卡片容器
    const card = link.closest('li, article, [class*="b-block"], [class*="job-list"], [class*="card"]')
               ?? link.parentElement?.parentElement;

    analyzedSet.add(jobId);
    newCount++;

    const extra = extractJobDataFromCard(link, card);

    const jobData = {
      jobTitle:    title,
      jobId,
      ...extra,
    };

    // 先渲染 loading 佔位徽章
    renderLoadingBadge(link, jobId);
    cLog('dim', `分析：${title} | 薪 ${extra.salaryMin}~${extra.salaryMax} | OT:${extra.overtimeHint}`);

    chrome.runtime.sendMessage({ type: 'ANALYZE_JOB', jobData }, response => {
      if (!chrome.runtime?.id) return;
      // 移除 loading 佔位
      removeLoadingBadge(jobId);
      if (chrome.runtime.lastError || !response?.success) {
        cLog('warn', `分析失敗：${title}`);
        return;
      }
      titleResultMap.set(jobId, response.result);
      renderBadgeOnLink(link, response.result, jobId);
    });
  }

  if (newCount > 0) cLog('ok', `本次掃描：${newCount} 筆新職缺（共 ${analyzedSet.size}）`);
  return newCount;
}

// ══════════════════════════════════════════════════════
// Loading 佔位徽章
// ══════════════════════════════════════════════════════
function renderLoadingBadge(linkEl, jobId) {
  if (linkEl.parentElement?.querySelector('.twra-loading')) return;
  const badge = document.createElement('span');
  badge.className = 'twra-loading';
  badge.dataset.jobid = jobId;
  badge.textContent = '...';
  badge.style.cssText = 'display:inline-block;margin-left:6px;font-size:12px;vertical-align:middle;opacity:0.6;';
  linkEl.after(badge);
}

function removeLoadingBadge(jobId) {
  document.querySelectorAll(`.twra-loading[data-jobid="${jobId}"]`).forEach(el => el.remove());
}

// ══════════════════════════════════════════════════════
// 徽章樣式工具
// ══════════════════════════════════════════════════════
const RISK_LABELS = { high: '[!] 高風險', medium: '[~] 注意', low: '[OK] 正常', unknown: '[?]' };
const RISK_COLORS = { high: '#ff4757', medium: '#ffa502', low: '#2ed573', unknown: '#747d8c' };
const RISK_TEXT   = { high: '#fff',    medium: '#333',    low: '#fff',   unknown: '#fff'    };

const LSTM_LABELS = { '好缺': '[+] 好缺', '普通': '[-] 普通', '屎缺': '[X] 屎缺' };
const LSTM_BG     = { '好缺': '#2ed573', '普通': '#ffa502', '屎缺': '#ff4757' };
const LSTM_TEXT   = { '好缺': '#fff',    '普通': '#333',    '屎缺': '#fff'    };

function makeBadge({ cls, text, bg, color, title: tip, dataJobid }) {
  const el = document.createElement('span');
  el.className = `twra-badge ${cls}`;
  if (dataJobid) el.dataset.jobid = dataJobid;
  el.textContent = text;
  if (tip) el.title = tip;
  el.style.cssText = [
    'display:inline-block', 'padding:2px 8px', 'border-radius:10px',
    'font-size:11px', 'font-weight:700', 'vertical-align:middle', 'margin-left:5px',
    `background:${bg}`, `color:${color}`,
    'cursor:default', 'white-space:nowrap', 'line-height:1.9',
    'position:relative', 'z-index:9999', 'letter-spacing:0.3px',
    'box-shadow:0 1px 3px rgba(0,0,0,0.15)',
  ].join(';');
  return el;
}

// ══════════════════════════════════════════════════════
// 主徽章渲染
// ══════════════════════════════════════════════════════
function renderBadgeOnLink(linkEl, result, jobId) {
  // 避免重複渲染
  if (linkEl.parentElement?.querySelector(`.twra-badge[data-jobid="${jobId}"]`)) return;

  const {
    riskLevel = 'unknown', score = 0, reasons = [], recommendation = '', source = '',
    lstmClass, lstmLabel, lstmProbabilities,
  } = result;

  // ── ① 規則 / AI 風險徽章 ──────────────────────────
  const riskTip = [
    `風險分數：${score}/100`,
    source ? `來源：${source}` : '',
    ...reasons,
    recommendation ? recommendation : '',
  ].filter(Boolean).join('\n');

  const riskBadge = makeBadge({
    cls:      `twra-badge--risk twra-badge--${riskLevel}`,
    text:     RISK_LABELS[riskLevel] ?? '[?]',
    bg:       RISK_COLORS[riskLevel] ?? '#747d8c',
    color:    RISK_TEXT[riskLevel]   ?? '#fff',
    title:    riskTip,
    dataJobid: jobId,
  });
  linkEl.after(riskBadge);

  // ── ② LSTM 分類徽章（有結果才顯示）──────────────
  if (lstmClass && LSTM_LABELS[lstmClass]) {
    const prob    = lstmProbabilities?.[lstmClass];
    const pct     = prob != null ? ` ${Math.round(prob * 100)}%` : '';
    const probTip = lstmProbabilities
      ? '本地 LSTM 預測\n' +
        Object.entries(lstmProbabilities)
          .sort((a, b) => b[1] - a[1])
          .map(([k, v]) => `  ${k}：${Math.round(v * 100)}%`)
          .join('\n')
      : '本地 LSTM 預測';

    const lstmBadge = makeBadge({
      cls:   `twra-badge--lstm twra-badge--lstm-${lstmClass}`,
      text:  LSTM_LABELS[lstmClass] + pct,
      bg:    LSTM_BG[lstmClass],
      color: LSTM_TEXT[lstmClass],
      title: probTip,
      dataJobid: jobId,
    });
    riskBadge.after(lstmBadge);
  }
}

// ══════════════════════════════════════════════════════
// 重新注入（vue-recycle-scroller 重用卡片時）
// ══════════════════════════════════════════════════════
function reInjectBadges() {
  for (const link of document.querySelectorAll('a[href*="/job/"]')) {
    const jobId = (link.getAttribute('href') || '').match(/\/job\/([a-zA-Z0-9]+)/)?.[1];
    if (!jobId) continue;
    const result = titleResultMap.get(jobId);
    if (result && !link.parentElement?.querySelector(`.twra-badge[data-jobid="${jobId}"]`)) {
      renderBadgeOnLink(link, result, jobId);
    }
  }
}

// ══════════════════════════════════════════════════════
// 供 popup 手動觸發
// ══════════════════════════════════════════════════════
function scanJobListings() {
  const n = scanJobLinks();
  cLog('info', `手動觸發 — 已分析 ${analyzedSet.size} 筆，本次新增 ${n}`);
}

// ══════════════════════════════════════════════════════
// 初始化
// ══════════════════════════════════════════════════════
chrome.storage.local.get(['autoAnalyze'], cfg => {
  if (cfg.autoAnalyze === false) { cLog('dim', 'autoAnalyze 關閉'); return; }
  cLog('info', `啟動：${location.pathname}`);

  // 多次延遲掃描，等 Vue 渲染完成
  const firstScan = () => {
    [500, 1500, 3000, 6000].forEach(d => setTimeout(scanJobLinks, d));
  };
  document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', firstScan)
    : firstScan();

  // MutationObserver：監控滾動 / 換頁帶來的新卡片
  const debounce = (fn, ms) => { let t; return () => { clearTimeout(t); t = setTimeout(fn, ms); }; };
  const obs = new MutationObserver(debounce(() => { scanJobLinks(); reInjectBadges(); }, 600));
  const startObs = () => obs.observe(document.body, { childList: true, subtree: true });
  document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', startObs)
    : startObs();
});
