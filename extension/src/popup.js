/**
 * 台灣求職避雷器 - Popup 腳本
 * 處理擴充功能設定介面
 */

// 標籤切換功能
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tabName = btn.getAttribute('data-tab');
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(tabName).classList.add('active');
  });
});

// 模型選擇
document.querySelectorAll('input[name="model"]').forEach(radio => {
  radio.addEventListener('change', () => {
    document.querySelectorAll('input[type="password"], input[type="text"]').forEach(input => {
      input.classList.add('hidden');
    });
    
    const selected = document.querySelector('input[name="model"]:checked').value;
    if (selected === 'openai') {
      document.getElementById('openai-key').classList.remove('hidden');
    } else if (selected === 'claude') {
      document.getElementById('claude-key').classList.remove('hidden');
    } else if (selected === 'local') {
      document.getElementById('local-url').classList.remove('hidden');
    }
  });
});

// 保存設定
document.getElementById('save-btn').addEventListener('click', () => {
  const model = document.querySelector('input[name="model"]:checked').value;
  const config = { model };
  
  if (model === 'openai') {
    config.apiKey = document.getElementById('openai-key').value;
  } else if (model === 'claude') {
    config.apiKey = document.getElementById('claude-key').value;
  } else if (model === 'local') {
    config.localUrl = document.getElementById('local-url').value;
  }
  
  const autoAnalyze = document.getElementById('auto-analyze').checked;
  const showStats = document.getElementById('show-stats').checked;
  
  chrome.storage.local.set({
    ...config,
    autoAnalyze,
    showStats
  }, () => {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = '✓ 設定已保存';
    statusDiv.style.color = 'green';
    setTimeout(() => {
      statusDiv.textContent = '';
    }, 2000);
  });
});

// 載入已保存的設定
chrome.storage.local.get(
  ['model', 'autoAnalyze', 'showStats'],
  (result) => {
    if (result.model) {
      document.getElementById(`model-${result.model}`).checked = true;
      document.getElementById(`model-${result.model}`).dispatchEvent(new Event('change'));
    }
    document.getElementById('auto-analyze').checked = result.autoAnalyze !== false;
    document.getElementById('show-stats').checked = result.showStats !== false;
  }
);
