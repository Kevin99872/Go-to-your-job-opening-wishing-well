/**
 * 台灣求職避雷器 - Content Script
 * 支援：
 *   1. 104 搜尋結果列表（/jobs/search/）每張職缺卡片
 *   2. 職缺詳情頁右側「相似職缺」面板
 *   3. 任何由 Vue SPA 動態注入的職缺卡片
 */

// ── 防抖工具 ─────────────────────────────────────────────
function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ── DOM 監測（捕捉 SPA 動態載入 + 相似職缺面板） ────────
const observer = new MutationObserver(debounce(scanJobListings, 600));
observer.observe(document.body, { childList: true, subtree: true });

// 初始掃描（等頁面主架構渲染完成）
setTimeout(scanJobListings, 1200);

// ── 主掃描函式 ────────────────────────────────────────────
function scanJobListings() {
  const cards = collectCards();
  cards.forEach(card => {
    if (card.hasAttribute('data-twra-done')) return;
    card.setAttribute('data-twra-done', '1');
    const jobData = extractJobData(card);
    if (jobData) analyzeAndMark(card, jobData);
  });
}

/**
 * 收集所有職缺卡片。
 * 策略1：data-jobno / data-job-id 屬性（104 常見）
 * 策略2：從 <h2> 內含職缺連結向上找 article / li 容器
 * （同時涵蓋搜尋列表、相似職缺面板）
 */
function collectCards() {
  // 策略1
  const byAttr = document.querySelectorAll(
    'article[data-jobno], article[data-job-id], [data-jobno], [data-job-id]'
  );
  if (byAttr.length > 0) return Array.from(byAttr);

  // 策略2：以 h2 > a（指向職缺頁）為錨點
  const seen = new Set();
  const results = [];
  const anchors = document.querySelectorAll(
    'h2 a[href*="104.com.tw/job/"], h2 a[href*="r.104.com.tw/m104"]'
  );
  anchors.forEach(a => {
    // 向上最多 10 層，找 article / li / section 作為卡片邊界
    let node = a.parentElement;
    for (let i = 0; i < 10 && node && node !== document.body; i++) {
      const tag = node.tagName.toLowerCase();
      if (tag === 'article' || tag === 'li' || tag === 'section') {
        if (!seen.has(node)) { seen.add(node); results.push(node); }
        break;
      }
      node = node.parentElement;
    }
  });
  return results;
}

// ── 從卡片提取職缺資料 ────────────────────────────────────
function extractJobData(card) {
  try {
    // 職位標題 & 連結
    const titleAnchor = card.querySelector(
      'h2 a[href*="104.com.tw/job/"], h2 a[href*="r.104.com.tw/m104"], h2 a'
    );
    const jobTitle = titleAnchor?.textContent?.trim();
    if (!jobTitle) return null;

    // 職缺 ID（從 URL 解析）
    const jobId = parseJobId(titleAnchor?.href || '');

    // 公司名稱
    const companyAnchor = card.querySelector('a[href*="104.com.tw/company/"]');
    const company = companyAnchor?.textContent?.trim() || '';

    // 薪資（以正則從卡片全文中擷取）
    const cardText = card.innerText || '';
    const salary = parseSalary(cardText);

    // 描述（取前 400 字）
    const description = cardText.replace(/\s+/g, ' ').trim().substring(0, 400);

    return { jobTitle, jobId, company, salary, description };
  } catch (e) {
    console.error('[避雷器] extractJobData 失敗:', e);
    return null;
  }
}

/** 從 104 職缺 URL 中取出 job ID */
function parseJobId(href) {
  if (!href) return null;
  try {
    // 直連：https://www.104.com.tw/job/8bsnh
    let m = href.match(/104\.com\.tw\/?jobsource=search&keyword\/([a-zA-Z0-9]+)/);
    if (m) return m[1];
    // 透過 redirect：r.104.com.tw/m104?url=...
    const decoded = decodeURIComponent(href);
    m = decoded.match(/104\.com\.tw\/?jobo\/([a-zA-Z0-9]+)/);
    if (m) return m[1];
  } catch {}
  return null;
}

/** 從卡片文字中擷取薪資敘述 */
function parseSalary(text) {
  const patterns = [
    /月薪[\d,，~～、\s]+元?以?上?/,
    /年薪[\d,，~～、\s]+元?以?上?/,
    /時薪[\d,，~～、\s]+元?以?上?/,
    /\d+K\s*[~～]\s*\d+K/i,
    /待遇面議/,
  ];
  for (const re of patterns) {
    const m = text.match(re);
    if (m) return m[0].trim();
  }
  return '薪資未標示';
}

// ── 送出分析請求 ──────────────────────────────────────────
function analyzeAndMark(card, jobData) {
  chrome.runtime.sendMessage({ type: 'ANALYZE_JOB', jobData }, (response) => {
    if (chrome.runtime.lastError) return;
    if (response?.success && response?.result) {
      addRiskBadge(card, response.result);
    }
  });
}

// ── 注入風險徽章 ──────────────────────────────────────────
function addRiskBadge(card, result) {
  if (card.querySelector('.twra-badge')) return; // 防重複

  const { riskLevel = 'unknown', score = 0, reasons = [], recommendation = '' } = result;

  const LABELS = {
    high:    '⚠️ 屎缺',
    medium:  '⚡ 注意',
    low:     '✅ 正常',
    unknown: '⏳ 分析中',
  };
  const COLORS = {
    high:    '#ff4757',
    medium:  '#ffa502',
    low:     '#2ed573',
    unknown: '#747d8c',
  };

  const badge = document.createElement('span');
  badge.className = `twra-badge twra-badge--${riskLevel}`;
  badge.textContent = LABELS[riskLevel] ?? '❓';
  badge.title = [
    `風險分數：${score} / 100`,
    ...reasons,
    recommendation ? `💡 ${recommendation}` : '',
  ].filter(Boolean).join('\n');

  // 最終樣式由 styles.css 控制，這裡只補最低限度 inline
  badge.style.cssText = `
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 700;
    vertical-align: middle;
    margin-left: 6px;
    background: ${COLORS[riskLevel] ?? '#747d8c'};
    color: #fff;
    cursor: default;
    white-space: nowrap;
    line-height: 1.7;
    position: relative;
    z-index: 10000;
  `;
  if (riskLevel === 'medium') badge.style.color = '#222';

  // 插入 h2 內（標題右側），若無 h2 則插入卡片最前面
  const h2 = card.querySelector('h2');
  if (h2) {
    h2.appendChild(badge);
  } else {
    card.insertBefore(badge, card.firstChild);
  }
}
