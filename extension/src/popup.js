/**
 * 台灣求職避雷器 - Popup 腳本
 * 處理擴充功能設定介面
 */

// ══════════════════════════════════════════════════════════
// Console log 工具
// ══════════════════════════════════════════════════════════
const logEl = document.getElementById('console-log');

function popupLog(type, msg) {
  const line = document.createElement('div');
  line.className = `log-line ${type}`;
  const time = new Date().toLocaleTimeString('zh-TW', { hour12: false });
  const prefix = { info: ' ', ok: ' ', warn: ' ', error:  ' ', dim: ' ' }[type] ?? '·';
  line.textContent = `[${time}] ${prefix} ${msg}`;
  logEl.appendChild(line);
  logEl.scrollTop = logEl.scrollHeight;
}

document.getElementById('clear-log').addEventListener('click', () => {
  logEl.innerHTML = '';
});

// 接收 background.js 轉發的 log
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'BG_LOG') {
    popupLog(msg.logType || 'dim', msg.msg);
  }
});

// ── 立即分析按鈕 ──────────────────────────────────────────
document.getElementById('run-btn').addEventListener('click', async () => {
  const btn = document.getElementById('run-btn');
  const statusEl = document.getElementById('run-status');

  btn.disabled = true;
  statusEl.textContent = ' 正在分析…';
  popupLog('info', '手動觸發分析…');

  try {
    // 取得目前 active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab) {
      popupLog('error', '找不到目前分頁');
      statusEl.textContent = ' 找不到分頁';
      return;
    }

    if (!tab.url?.includes('104.com.tw')) {
      popupLog('warn', `目前頁面不是 104（${tab.url?.split('/')[2] ?? '未知'}）`);
      statusEl.textContent = ' 請先前往 104.com.tw';
      return;
    }

    popupLog('dim', `分頁：${tab.url.split('?')[0]}`);

    // ── 步驟1：深度 DOM 診斷 ─────────────────────────────
    const diagResults = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const report = {};

        // 1. 計數各種選擇器
        const selectors = {
          'article':               document.querySelectorAll('article').length,
          'li':                    document.querySelectorAll('li').length,
          '[data-jobno]':          document.querySelectorAll('[data-jobno]').length,
          '[data-job-id]':         document.querySelectorAll('[data-job-id]').length,
          '.b-list-box':           document.querySelectorAll('.b-list-box').length,
          '.b-block':              document.querySelectorAll('.b-block').length,
          '.job-list-item':        document.querySelectorAll('.job-list-item').length,
          '[class*="job-list"]':   document.querySelectorAll('[class*="job-list"]').length,
          '[class*="b-block"]':    document.querySelectorAll('[class*="b-block"]').length,
          'h2 a':                  document.querySelectorAll('h2 a').length,
          'a[href*="/job/"]':      document.querySelectorAll('a[href*="/job/"]').length,
          'a[href*="jobno"]':      document.querySelectorAll('a[href*="jobno"]').length,
        };
        report.selectors = selectors;

        // 2. 取前5個 <a> 的 href，找出職缺連結模式
        const allLinks = Array.from(document.querySelectorAll('a[href]'));
        report.sampleHrefs = allLinks
          .map(a => a.getAttribute('href'))
          .filter(h => h && !h.startsWith('#') && !h.startsWith('javascript'))
          .slice(0, 20);

        // 3. 取第一個 h2 的資訊
        const firstH2 = document.querySelector('h2');
        if (firstH2) {
          report.firstH2Text = firstH2.textContent.trim().substring(0, 50);
          report.firstH2Html = firstH2.outerHTML.substring(0, 200);
        }

        // 4. 取第一個 article 或 [class*=job] 的 class 和結構
        const firstArticle = document.querySelector('article');
        if (firstArticle) {
          report.firstArticleClass = firstArticle.className;
          report.firstArticleSnippet = firstArticle.outerHTML.substring(0, 400);
        }

        // 5. 全部 li 裡，找出文字最長的前3個（可能是職缺卡片）
        const allLi = Array.from(document.querySelectorAll('li'))
          .filter(li => li.innerText?.length > 50)
          .sort((a, b) => b.innerText.length - a.innerText.length)
          .slice(0, 3);
        report.topLi = allLi.map(li => ({
          cls: li.className.substring(0, 80),
          snippet: li.outerHTML.substring(0, 300)
        }));

        return report;
      }
    });

    const diag = diagResults?.[0]?.result;
    if (diag) {
      popupLog('info', '── DOM 診斷 ──');
      Object.entries(diag.selectors || {}).forEach(([sel, cnt]) => {
        if (cnt > 0) popupLog('ok',  `${cnt}  ${sel}`);
      });
      if (diag.firstH2Html) popupLog('info', `h2: ${diag.firstH2Html.substring(0, 100)}`);
      if (diag.firstArticleClass) popupLog('info', `article.class: ${diag.firstArticleClass.substring(0, 80)}`);
      (diag.topLi || []).forEach((li, i) => popupLog('info', `li[${i}].class: ${li.cls}`));
      // 顯示包含 job 關鍵字的 href
      const jobHrefs = (diag.sampleHrefs || []).filter(h => /job|cust|jobno/i.test(h));
      if (jobHrefs.length) {
        popupLog('ok', '職缺相關連結:');
        jobHrefs.slice(0, 5).forEach(h => popupLog('dim', h.substring(0, 100)));
      } else {
        popupLog('warn', 'href 樣本: ' + (diag.sampleHrefs || []).slice(0, 5).join(' | '));
      }
    }

    // ── 步驟2：清除舊標記並觸發掃描 ────────────────────
    const scanResults = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        // 移除所有徽章
        document.querySelectorAll('.twra-badge, .twra-stats, .twra-loading').forEach(el => el.remove());
        // 移除所有 data-twra-* 屬性（新版用 data-twra-{title} 而非 data-twra-done）
        document.querySelectorAll('*').forEach(el => {
          [...el.attributes]
            .filter(a => a.name.startsWith('data-twra-'))
            .forEach(a => el.removeAttribute(a.name));
        });
        // 清除分析快取，讓重新分析能重新執行
        if (typeof analyzedSet !== 'undefined') analyzedSet.clear();
        if (typeof titleResultMap !== 'undefined') titleResultMap.clear();

        if (typeof scanJobListings === 'function') {
          scanJobListings();
          return { triggered: true };
        }
        return { triggered: false };
      }
    });

    const triggered = scanResults?.[0]?.result?.triggered;
    if (triggered) {
      popupLog('ok', '已觸發重新掃描');
      statusEl.textContent = '分析中，請查看頁面上的徽章';
    } else {
      popupLog('warn', 'content script 未就緒，重新注入…');
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['src/content.js']
      });
      popupLog('ok', 'content script 已重新注入');
      statusEl.textContent = '已重新注入，請稍等';
    }
  } catch (e) {
    popupLog('error', `執行失敗：${e.message}`);
    statusEl.textContent = ` ${e.message}`;
  } finally {
    btn.disabled = false;
    setTimeout(() => { statusEl.textContent = ''; }, 4000);
  }
});

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
  setStatus('backend-status', 'checking', ' 測試中…');
  try {
    const res = await fetch(`${url}/api/health`, { signal: AbortSignal.timeout(5000) });
    if (res.ok) {
      const data = await res.json();
      setStatus('backend-status', 'success', `已連線：${data.service || '後端服務'}`);
    } else {
      setStatus('backend-status', 'error', `伺服器回應 ${res.status}`);
    }
  } catch (e) {
    setStatus('backend-status', 'error', `無法連線（${e.message}）`);
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
  setStatus('ollama-status', 'checking', ' 測試中…');
  try {
    const models = await loadOllamaModels(url);
    setStatus('ollama-status', 'success', ` 已連線，找到 ${models.length} 個模型`);
  } catch (e) {
    setStatus('ollama-status', 'error', ` 無法連線（${e.message}）`);
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
    setStatus('ollama-status', 'success', ' 模型列表已更新');
  } catch (e) {
    setStatus('ollama-status', 'error', ` 重新整理失敗（${e.message}）`);
  }
});

// 載入連線頁既有設定
chrome.storage.local.get(
  ['backendUrl', 'ollamaUrl', 'ollamaModel', 'directMode', 'useLstm'],
  async (result) => {
    document.getElementById('backend-url').value   = result.backendUrl || DEFAULT_BACKEND;
    document.getElementById('ollama-url').value    = result.ollamaUrl  || DEFAULT_OLLAMA;
    document.getElementById('direct-mode').checked = result.directMode === true;
    document.getElementById('use-lstm').checked    = result.useLstm !== false; // 預設開啟

    if (result.ollamaUrl) {
      try {
        await loadOllamaModels(result.ollamaUrl);
        if (result.ollamaModel) {
          document.getElementById('ollama-model-select').value = result.ollamaModel;
        }
      } catch (e) {
        setStatus('ollama-status', 'error', ` 無法載入模型（${e.message}）`);
      }
    }
  }
);

// ══════════════════════════════════════════════════════════
// LSTM 模型狀態
// ══════════════════════════════════════════════════════════

async function checkLstmStatus() {
  const btn = document.getElementById('check-lstm');
  btn.disabled = true;
  setStatus('lstm-status', 'checking', ' 檢查中…');
  try {
    // 透過 background.js 查詢（避免 CORS）
    const response = await new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type: 'CHECK_LSTM_STATUS' }, (res) => {
        if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
        resolve(res);
      });
    });

    if (response?.ready) {
      setStatus('lstm-status', 'success', ' 模型已就緒，可使用 LSTM 預測');
      popupLog('ok', 'LSTM 模型載入成功');
    } else {
      const msg = response?.message || '模型未載入';
      setStatus('lstm-status', 'error', ` ${msg}`);
      popupLog('warn', `LSTM：${msg}`);
    }
  } catch (e) {
    setStatus('lstm-status', 'error', ` 無法檢查（${e.message}）`);
  } finally {
    btn.disabled = false;
  }
}

document.getElementById('check-lstm').addEventListener('click', checkLstmStatus);

// LSTM 開關變更時即時儲存
document.getElementById('use-lstm').addEventListener('change', (e) => {
  chrome.storage.local.set({ useLstm: e.target.checked }, () => {
    popupLog('info', `LSTM 預測：${e.target.checked ? '已開啟' : '已關閉'}`);
  });
});

// 保存連線設定時一起存 useLstm
const _origSaveConn = document.getElementById('save-connection-btn').onclick;
document.getElementById('save-connection-btn').addEventListener('click', () => {
  const useLstm = document.getElementById('use-lstm').checked;
  chrome.storage.local.set({ useLstm });
});
