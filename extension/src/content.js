/**
 * 台灣求職避雷器 - Content Script (run_at: document_start)
 *
 * 策略：直接掃描 DOM 中所有 href 包含 /job/ 的連結，
 * 不依賴 API 攔截。vue-recycle-scroller 的可見卡片
 * 都在 DOM 裡，MutationObserver 監控滾動時的新卡片。
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
// 從 DOM 擷取薪資文字
// ══════════════════════════════════════════════════════
function extractText(el, patterns) {
  if (!el) return '';
  // 找包含特定 class 關鍵字的子元素
  for (const pat of patterns) {
    const found = el.querySelector(`[class*="${pat}"]`);
    if (found?.textContent.trim()) return found.textContent.trim();
  }
  return '';
}

// ══════════════════════════════════════════════════════
// 主掃描：找所有 /job/ 連結
// ══════════════════════════════════════════════════════
function scanJobLinks() {
  if (!chrome.runtime?.id) return; // extension context 已失效

  // 104 的每個職缺卡片都有 <a href="...104.com.tw/job/XXXXX">
  const links = document.querySelectorAll('a[href*="/job/"]');
  let newCount = 0;

  for (const link of links) {
    const href = link.getAttribute('href') || '';
    const jobId = href.match(/\/job\/([a-zA-Z0-9]+)/)?.[1];
    if (!jobId || analyzedSet.has(jobId)) continue;

    const title = link.textContent.trim();
    if (!title || title.length < 2 || title.length > 60) continue;

    // 向上找卡片容器（li / article / div.b-block 等）
    const card = link.closest('li, article, [class*="b-block"], [class*="job-list"], [class*="card"]')
               ?? link.parentElement?.parentElement;

    const salary  = extractText(card, ['salary', 'pay', 'wage', '薪'])
                 || card?.querySelector('[class*="salary"]')?.textContent.trim()
                 || '';
    const company = extractText(card, ['company', 'cust', 'corp', '公司'])
                 || card?.querySelector('[class*="cust"]')?.textContent.trim()
                 || '';

    analyzedSet.add(jobId);
    newCount++;

    const jobData = {
      jobTitle:    title,
      jobId,
      company:     company.substring(0, 60),
      salary:      salary  || '薪資未標示',
      description: card?.textContent?.substring(0, 400) || ''
    };

    cLog('dim', `分析：${title}（${jobId}）`);

    chrome.runtime.sendMessage({ type: 'ANALYZE_JOB', jobData }, response => {
      if (!chrome.runtime?.id) return;
      if (chrome.runtime.lastError || !response?.success) return;
      titleResultMap.set(jobId, response.result);
      renderBadgeOnLink(link, response.result);
    });
  }

  if (newCount > 0) cLog('ok', `本次掃描：${newCount} 筆新職缺（共 ${analyzedSet.size}）`);
  return newCount;
}

// ══════════════════════════════════════════════════════
// 渲染徽章（直接插入 link 旁邊）
// ══════════════════════════════════════════════════════

// 規則分析徽章設定
const RISK_LABELS = { high: '⚠ 高風險', medium: '⚡ 注意', low: '✅ 正常', unknown: '❓' };
const RISK_COLORS = { high: '#ff4757', medium: '#ffa502', low: '#2ed573', unknown: '#747d8c' };

// LSTM 分類徽章設定
const LSTM_LABELS      = { '好缺': '🟢 好缺', '普通': '🟡 普通', '屎缺': '🔴 屎缺' };
const LSTM_COLORS      = { '好缺': '#2ed573', '普通': '#ffa502', '屎缺': '#ff4757'  };
const LSTM_TEXT_COLORS = { '好缺': '#fff',     '普通': '#333',    '屎缺': '#fff'    };

function _badgeStyle(bg, color, extra = '') {
  return [
    'display:inline-block', 'padding:1px 7px', 'border-radius:10px',
    'font-size:11px', 'font-weight:700', 'vertical-align:middle', 'margin-left:6px',
    `background:${bg}`, `color:${color}`,
    'cursor:default', 'white-space:nowrap', 'line-height:1.8',
    'position:relative', 'z-index:9999',
    extra
  ].filter(Boolean).join(';');
}

function renderBadgeOnLink(linkEl, result) {
  if (!linkEl || linkEl.parentElement?.querySelector('.twra-badge')) return;

  const {
    riskLevel = 'unknown', score = 0, reasons = [], recommendation = '',
    lstmClass, lstmProbabilities
  } = result;

  // ── 規則分析徽章 ───────────────────────────────────────
  const badge = document.createElement('span');
  badge.className = `twra-badge twra-badge--${riskLevel}`;
  badge.textContent = RISK_LABELS[riskLevel] ?? '❓';
  badge.title = [`風險分數：${score}/100`, ...reasons,
    recommendation ? `💡 ${recommendation}` : ''].filter(Boolean).join('\n');
  badge.style.cssText = _badgeStyle(
    RISK_COLORS[riskLevel] ?? '#747d8c',
    riskLevel === 'medium' ? '#333' : '#fff'
  );
  linkEl.after(badge);

  // ── LSTM 分類徽章（有結果才顯示）──────────────────────
  if (lstmClass && LSTM_LABELS[lstmClass]) {
    const prob = lstmProbabilities?.[lstmClass];
    const pct  = prob != null ? ` ${Math.round(prob * 100)}%` : '';

    const lstmBadge = document.createElement('span');
    lstmBadge.className = `twra-badge twra-badge--lstm twra-badge--lstm-${lstmClass}`;
    lstmBadge.textContent = LSTM_LABELS[lstmClass] + pct;

    const probLines = lstmProbabilities
      ? Object.entries(lstmProbabilities)
          .sort((a, b) => b[1] - a[1])
          .map(([k, v]) => `  ${k}：${Math.round(v * 100)}%`)
          .join('\n')
      : '';
    lstmBadge.title = `🤖 本地 LSTM 模型預測\n${probLines}`;
    lstmBadge.style.cssText = _badgeStyle(
      LSTM_COLORS[lstmClass],
      LSTM_TEXT_COLORS[lstmClass],
      'margin-left:3px'
    );
    badge.after(lstmBadge);
  }
}

// ══════════════════════════════════════════════════════
// 重新注入（卡片被 vue-recycle-scroller 重用時）
// ══════════════════════════════════════════════════════
function reInjectBadges() {
  for (const link of document.querySelectorAll('a[href*="/job/"]')) {
    const jobId = (link.getAttribute('href') || '').match(/\/job\/([a-zA-Z0-9]+)/)?.[1];
    if (!jobId) continue;
    const result = titleResultMap.get(jobId);
    if (result) renderBadgeOnLink(link, result);
  }
}

// ══════════════════════════════════════════════════════
// 供 popup 按鈕呼叫
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

  // DOM 就緒後第一次掃描
  const firstScan = () => {
    // 多次重試，等 Vue 渲染職缺卡片
    [500, 1500, 3000, 6000].forEach(d => setTimeout(scanJobLinks, d));
  };
  document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', firstScan)
    : firstScan();

  // MutationObserver：監控 DOM 變動（滾動、換頁）
  const debounce = (fn, ms) => { let t; return () => { clearTimeout(t); t = setTimeout(fn, ms); }; };
  const obs = new MutationObserver(debounce(() => { scanJobLinks(); reInjectBadges(); }, 600));
  const startObs = () => obs.observe(document.body, { childList: true, subtree: true });
  document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', startObs)
    : startObs();
});
