/**
 * 台灣求職避雷器 - Content Script
 * 在104職缺頁面上注入標記和分析功能
 */

// 監視 DOM 變化，檢查新的職位卡片
const observer = new MutationObserver(() => {
  scanJobListings();
});

observer.observe(document.body, {
  childList: true,
  subtree: true,
  attributes: false
});

// 初始掃描
scanJobListings();

/**
 * 掃描頁面上的職位列表
 */
function scanJobListings() {
  // 根據 104 網站的 HTML 結構調整選擇器
  const jobCards = document.querySelectorAll('[data-job-id], .job-item, article');
  
  jobCards.forEach(card => {
    // 避免重複處理
    if (card.hasAttribute('data-analyzed')) return;
    card.setAttribute('data-analyzed', 'true');
    
    const jobData = extractJobData(card);
    if (jobData) {
      analyzeAndMark(card, jobData);
    }
  });
}

/**
 * 從職位卡片中提取信息
 */
function extractJobData(card) {
  try {
    const jobTitle = card.querySelector('h1, h2, .job-title')?.textContent?.trim();
    const company = card.querySelector('.company-name, [data-company]')?.textContent?.trim();
    const salary = card.querySelector('.salary, [data-salary]')?.textContent?.trim();
    const description = card.querySelector('.job-description, p')?.textContent?.trim();
    
    if (!jobTitle || !salary) return null;
    
    return { jobTitle, company, salary, description: description?.substring(0, 500) };
  } catch (error) {
    console.error('提取職位數據失敗:', error);
    return null;
  }
}

/**
 * 分析職位並在頁面上標記
 */
function analyzeAndMark(card, jobData) {
  // 向後台發送分析請求
  chrome.runtime.sendMessage(
    { type: 'ANALYZE_JOB', jobData },
    (response) => {
      if (response.success && response.result) {
        const risk = response.result.riskLevel || 'unknown';
        const reasons = response.result.reasons || [];
        
        // 添加視覺標記
        addRiskBadge(card, risk, reasons);
      }
    }
  );
}

/**
 * 添加風險標誌到職位卡片
 */
function addRiskBadge(card, risk, reasons) {
  const badge = document.createElement('div');
  badge.className = `risk-badge risk-${risk}`;
  
  const riskLabels = {
    'high': '屎缺 ⚠️',
    'medium': '小心 ⚠',
    'low': '正常 ✓'
  };
  
  badge.textContent = riskLabels[risk] || '分析中...';
  badge.title = reasons.join('\\n');
  
  // 設定樣式
  badge.style.cssText = `
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 12px;
    margin-left: 8px;
  `;
  
  if (risk === 'high') {
    badge.style.backgroundColor = '#ff6b6b';
    badge.style.color = 'white';
  } else if (risk === 'medium') {
    badge.style.backgroundColor = '#ffd93d';
    badge.style.color = '#333';
  } else if (risk === 'low') {
    badge.style.backgroundColor = '#6bcf7f';
    badge.style.color = 'white';
  }
  
  // 找到職位標題並添加徽章
  const titleElement = card.querySelector('h1, h2, .job-title');
  if (titleElement) {
    titleElement.parentElement.appendChild(badge);
  }
}
