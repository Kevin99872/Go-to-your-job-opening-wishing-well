/**
 * 台灣求職避雷器 - 後台服務
 * 負責與後端 API 通訊、資料緩存、事件管理
 */

const API_BASE_URL = 'http://localhost:5000/api';
const CACHE_DURATION = 3600000; // 1 小時

// 設定存儲
chrome.storage.local.get(['apiKey', 'useLocalModel'], (result) => {
  if (!result.apiKey && !result.useLocalModel) {
    // 首次安裝，提示用戶設定
    console.log('請設定 API Key 或選擇本地模型');
  }
});

// 監聽來自 content script 的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'ANALYZE_JOB') {
    analyzeJob(request.jobData).then(result => {
      sendResponse({ success: true, result });
    }).catch(error => {
      sendResponse({ success: false, error: error.message });
    });
    return true; // 保持通道開放以進行非同步回應
  }
  
  if (request.type === 'GET_SALARY_STATS') {
    getSalaryStats(request.jobTitle).then(result => {
      sendResponse({ success: true, result });
    }).catch(error => {
      sendResponse({ success: false, error: error.message });
    });
    return true;
  }
});

/**
 * 分析職位信息
 */
async function analyzeJob(jobData) {
  const { jobTitle, salary, company, description } = jobData;
  
  try {
    // 獲取薪資統計
    const salaryStats = await getSalaryStats(jobTitle);
    
    // 呼叫後端 API 進行分析
    const response = await fetch(`${API_BASE_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jobTitle,
        salary,
        company,
        description,
        salaryStats
      })
    });
    
    if (!response.ok) throw new Error('API 請求失敗');
    
    const result = await response.json();
    return result;
  } catch (error) {
    console.error('分析職位失敗:', error);
    throw error;
  }
}

/**
 * 獲取薪資統計
 */
async function getSalaryStats(jobTitle) {
  const cacheKey = `salary_stats_${jobTitle}`;
  
  // 檢查緩存
  return new Promise((resolve) => {
    chrome.storage.local.get(cacheKey, (result) => {
      if (result[cacheKey] && Date.now() - result[cacheKey].timestamp < CACHE_DURATION) {
        resolve(result[cacheKey].data);
        return;
      }
      
      // 從後端獲取
      fetch(`${API_BASE_URL}/salary-stats?jobTitle=${encodeURIComponent(jobTitle)}`)
        .then(res => res.json())
        .then(data => {
          // 保存到緩存
          chrome.storage.local.set({
            [cacheKey]: { data, timestamp: Date.now() }
          });
          resolve(data);
        })
        .catch(error => {
          console.error('獲取薪資統計失敗:', error);
          resolve(null);
        });
    });
  });
}
