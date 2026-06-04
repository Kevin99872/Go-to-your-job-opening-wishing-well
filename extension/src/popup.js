/**
 * 台灣求職避雷器 - Popup 腳本
 * 處理擴充功能設定介面
 */

// ── 標籤切換 ──────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tabName = btn.getAttribute('data-tab');
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(tabName).classList.add('active');
  });
});

// ── 模型選擇（設定頁）────────────────────────────────────
document.querySelectorAll('input[name="model"]').forEach(radio => {
  radio.addEventListener('change', () => {
    document.querySelectorAll('input[type="password"], #local-url').forEach(input => {
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

// ── 保存設定頁 ────────────────────────────────────────────
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
  const showStats   = document.getElementById('show-stats').checked;

  chrome.storage.local.set({ ...config, autoAnalyze, showStats }, () => {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = '✓ 設定已保存';
    statusDiv.style.color = 'green';
    setTimeout(() => { statusDiv.textContent = ''; }, 2000);
  });
});

// ── 載入設定頁既有設定 ────────────────────────────────────
chrome.storage.local.get(['model', 'autoAnalyze', 'showStats'], (result) => {
  if (result.model) {
    const el = document.getElementById(`model-${result.model}`);
    if (el) { el.checked = true; el.dispatchEvent(new Event('change')); }
  }
  document.getElementById('auto-analyze').checked = result.autoAnalyze !== false;
  document.getElementById('show-stats').checked   = result.showStats   !== false;
});

// ══════════════════════════════════════════════════════════
// 連線設定頁
// ══════════════════════════════════════════════════════════

const DEFAULT_BACKEND = 'http://localhost:5000';
const DEFAULT_OLLAMA  = 'http://localhost:11434';

// 輔助：顯示連線狀態
function setStatus(elId, type, text) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.className = `conn-status ${type}`;
  el.textContent = text;
}

// 測試後端連線
async function testBackend() {
  const url = (document.getElementById('backend-url').value || DEFAULT_BACKEND).replace(/\/$/, '');
  const btn = document.getElementById('test-backend');
  btn.disabled = true;
  setStatus('backend-status', 'checking', '⏳ 測試中…');
  try {
    const res = await fetch(`${url}/api/health`, { signal: AbortSignal.timeout(5000) });
    if (res.ok) {
      const data = await res.json();
      setStatus('backend-status', 'success', `✅ 已連線：${data.service || '後端服務'}`);
    } else {
      setStatus('backend-status', 'error', `❌ 伺服器回應 ${res.status}`);
    }
  } catch (e) {
    setStatus('backend-status', 'error', `❌ 無法連線（${e.message}）`);
  } finally {
    btn.disabled = false;
  }
}

// 載入 Ollama 模型清單
async function loadOllamaModels(ollamaUrl) {
  const url = (ollamaUrl || DEFAULT_OLLAMA).replace(/\/$/, '');
  const select = document.getElementById('ollama-model-select');
  try {
    const res = await fetch(`${url}/api/tags`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const models = data.models || [];
    select.innerHTML = models.length
      ? models.map(m => `<option value="${m.name}">${m.name}</option>`).join('')
      : '<option value="">（尚未安裝任何模型）</option>';
    return models;
  } catch (e) {
    select.innerHTML = '<option value="">（無法取得模型清單）</option>';
    throw e;
  }
}

// 測試 Ollama 連線
async function testOllama() {
  const url = (document.getElementById('ollama-url').value || DEFAULT_OLLAMA).replace(/\/$/, '');
  const btn = document.getElementById('test-ollama');
  btn.disabled = true;
  setStatus('ollama-status', 'checking', '⏳ 測試中…');
  try {
    const models = await loadOllamaModels(url);
    setStatus('ollama-status', 'success', `✅ 已連線，找到 ${models.length} 個模型`);
  } catch (e) {
    setStatus('ollama-status', 'error', `❌ 無法連線（${e.message}）`);
  } finally {
    btn.disabled = false;
  }
}

// 保存連線設定
document.getElementById('save-connection-btn').addEventListener('click', () => {
  const backendUrl  = document.getElementById('backend-url').value.trim()  || DEFAULT_BACKEND;
  const ollamaUrl   = document.getElementById('ollama-url').value.trim()   || DEFAULT_OLLAMA;
  const ollamaModel = document.getElementById('ollama-model-select').value;
  const directMode  = document.getElementById('direct-mode').checked;

  chrome.storage.local.set({ backendUrl, ollamaUrl, ollamaModel, directMode }, () => {
    const el = document.getElementById('conn-save-status');
    el.textContent = '✓ 連線設定已保存';
    el.style.color = 'green';
    setTimeout(() => { el.textContent = ''; }, 2000);
  });
});

// 測試按鈕綁定
document.getElementById('test-backend').addEventListener('click', testBackend);
document.getElementById('test-ollama').addEventListener('click', testOllama);
document.getElementById('refresh-models').addEventListener('click', async () => {
  const url = document.getElementById('ollama-url').value || DEFAULT_OLLAMA;
  try {
    await loadOllamaModels(url);
    setStatus('ollama-status', 'success', '✅ 模型列表已更新');
  } catch (e) {
    setStatus('ollama-status', 'error', `❌ 重新整理失敗（${e.message}）`);
  }
});

// 載入連線頁既有設定
chrome.storage.local.get(
  ['backendUrl', 'ollamaUrl', 'ollamaModel', 'directMode'],
  async (result) => {
    document.getElementById('backend-url').value = result.backendUrl || DEFAULT_BACKEND;
    document.getElementById('ollama-url').value  = result.ollamaUrl  || DEFAULT_OLLAMA;
    document.getElementById('direct-mode').checked = result.directMode === true;

    if (result.ollamaUrl) {
      try {
        await loadOllamaModels(result.ollamaUrl);
        if (result.ollamaModel) {
          document.getElementById('ollama-model-select').value = result.ollamaModel;
        }
      } catch (e) { /* 離線時靜默失敗 */ 
        setStatus(' 重新整理失敗（${e.message}）');
      }
    }
  }
);
