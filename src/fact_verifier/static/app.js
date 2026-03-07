const I18N = JSON.parse(document.getElementById('i18n-data').textContent);
let currentLang = 'en';

function t(key) {
  return (I18N[currentLang] && I18N[currentLang][key]) || I18N['en'][key] || key;
}

function setLang(lang) {
  document.documentElement.setAttribute('lang', lang === 'zh' ? 'zh-Hans' : lang);
  currentLang = lang;
  document.getElementById('language-input').value = lang;

  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });

  document.getElementById('app-title').textContent = t('app_title');
  document.getElementById('app-subtitle').textContent = t('app_subtitle');
  document.getElementById('claim-input').placeholder = t('input_placeholder');
  document.getElementById('upload-label').textContent = t('upload_label');
  document.getElementById('submit-btn').textContent = t('submit_button');
  document.getElementById('checking-message').textContent = t('checking_message');
  document.getElementById('step-1-label').textContent = t('step_1');
  document.getElementById('step-2-label').textContent = t('step_2');
  document.getElementById('step-3-label').textContent = t('step_3');
  document.getElementById('reset-btn').textContent = t('reset_button');
  document.getElementById('error-reset-btn').textContent = t('reset_button');
  document.getElementById('share-btn').textContent = t('share_button');
}

// Language switcher
document.querySelectorAll('.lang-btn').forEach(btn => {
  btn.addEventListener('click', () => setLang(btn.dataset.lang));
});

// --- History ---
const HISTORY_KEY = 'truthcheck_history';
const HISTORY_MAX = 50;

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
  } catch (_) {
    return [];
  }
}

function saveHistory(entries) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
}

function addHistoryEntry(entry) {
  const entries = loadHistory();
  entries.unshift(entry);
  if (entries.length > HISTORY_MAX) entries.splice(HISTORY_MAX);
  saveHistory(entries);
}

function clearHistory() {
  localStorage.removeItem(HISTORY_KEY);
}

function relativeTime(isoString) {
  const diff = Math.floor((Date.now() - new Date(isoString)) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return Math.floor(diff / 86400) + 'd ago';
}

let activeHistoryId = null;

function renderHistorySidebar() {
  const entries = loadHistory();
  const list = document.getElementById('history-list');
  list.innerHTML = '';

  if (entries.length === 0) {
    list.innerHTML = '<p class="history-empty">No history yet.</p>';
    return;
  }

  entries.forEach(entry => {
    const div = document.createElement('div');
    div.className = 'history-entry' + (entry.id === activeHistoryId ? ' active' : '');
    div.dataset.id = entry.id;

    const verdictClass = 'verdict-badge verdict-' + entry.verdict;
    div.innerHTML =
      '<div class="history-entry-claim">' + escHtml(entry.claim) + '</div>' +
      '<div class="history-entry-meta">' +
        '<span class="' + escHtml(verdictClass) + '" style="font-size:10px;padding:1px 4px">' + escHtml(entry.verdict) + '</span>' +
        '<span class="history-entry-time">' + relativeTime(entry.timestamp) + '</span>' +
      '</div>';

    div.addEventListener('click', () => {
      activeHistoryId = entry.id;
      renderHistorySidebar();
      currentClaim = entry.claim;
      renderResult(
        { verdict: entry.verdict, summary: entry.summary, explanation: entry.explanation, sources: entry.sources },
        entry.shareId,
        entry.claim,
        entry.imageUrl || null
      );
      showState('result');
    });

    list.appendChild(div);
  });
}

document.getElementById('clear-history-btn').addEventListener('click', () => {
  clearHistory();
  activeHistoryId = null;
  renderHistorySidebar();
});

// Image upload
const uploadArea = document.getElementById('upload-area');
const imageInput = document.getElementById('image-input');
const previewContainer = document.getElementById('preview-container');
const imagePreview = document.getElementById('image-preview');

uploadArea.addEventListener('click', () => imageInput.click());
uploadArea.addEventListener('dragover', e => {
  e.preventDefault();
  uploadArea.style.borderColor = '#1e293b';
});
uploadArea.addEventListener('dragleave', () => {
  uploadArea.style.borderColor = '';
});
uploadArea.addEventListener('drop', e => {
  e.preventDefault();
  const file = e.dataTransfer.files[0];
  if (file) handleImageFile(file);
});

imageInput.addEventListener('change', () => {
  if (imageInput.files[0]) handleImageFile(imageInput.files[0]);
});

function handleImageFile(file) {
  const dt = new DataTransfer();
  dt.items.add(file);
  imageInput.files = dt.files;

  const reader = new FileReader();
  reader.onload = e => {
    imagePreview.src = e.target.result;
    previewContainer.hidden = false;
    document.getElementById('upload-label').hidden = true;
  };
  reader.readAsDataURL(file);
}

document.getElementById('clear-image').addEventListener('click', e => {
  e.stopPropagation();
  imageInput.value = '';
  previewContainer.hidden = true;
  document.getElementById('upload-label').hidden = false;
});

// State management
function showState(name) {
  ['input', 'loading', 'result', 'error'].forEach(s => {
    document.getElementById('state-' + s).hidden = s !== name;
  });
}

function setStep(active) {
  for (let i = 1; i <= 3; i++) {
    const el = document.getElementById('step-' + i);
    el.classList.remove('done', 'active');
    if (i < active) {
      el.querySelector('.step-icon').textContent = '\u2705';
    } else if (i === active) {
      el.querySelector('.step-icon').textContent = '\u23F3';
      el.classList.add('active');
    } else {
      el.querySelector('.step-icon').textContent = '\u25CB';
    }
  }
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function safeUrl(url) {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') return '#';
    return url;
  } catch (_) {
    return '#';
  }
}

function renderResult(data, shareId, claim, imageSrc) {
  document.getElementById('result-claim').textContent = claim || '';

  const existingImg = document.getElementById('result-image');
  if (existingImg) existingImg.remove();
  if (imageSrc) {
    const img = document.createElement('img');
    img.id = 'result-image';
    img.src = imageSrc;
    img.alt = 'Uploaded image';
    img.className = 'result-image';
    document.getElementById('result-claim').after(img);
  }

  const badge = document.getElementById('verdict-badge');
  badge.className = 'verdict-badge';
  badge.textContent = t('verdict_' + data.verdict);
  badge.classList.add('verdict-' + data.verdict);
  document.getElementById('verdict-explanation').textContent = t('verdict_' + data.verdict + '_explanation');

  document.getElementById('result-summary').textContent = data.summary || '';

  const explanationEl = document.getElementById('result-explanation');
  const bullets = (data.explanation || '').split('\n').map(s => s.trim()).filter(s => s);
  if (bullets.length > 1) {
    const ul = document.createElement('ul');
    bullets.forEach(b => {
      const li = document.createElement('li');
      li.textContent = b.replace(/^•\s*/, '');
      ul.appendChild(li);
    });
    explanationEl.innerHTML = '';
    explanationEl.appendChild(ul);
  } else {
    explanationEl.textContent = data.explanation || '';
  }
  document.getElementById('sources-title').textContent = t('sources_title');

  const shareContainer = document.getElementById('share-container');
  if (shareId) {
    const shareUrl = window.location.origin + '/share/' + shareId;
    document.getElementById('share-url').value = shareUrl;
    shareContainer.hidden = false;
  } else {
    shareContainer.hidden = true;
  }

  const list = document.getElementById('sources-list');
  list.innerHTML = '';
  (data.sources || []).forEach(source => {
    const card = document.createElement('div');
    card.className = 'source-card';
    const tierLabel = t('tier_' + source.tier) || source.tier;
    const stanceLabel = t('stance_' + source.stance) || source.stance;
    card.innerHTML =
      '<div class="source-header">' +
        '<span class="tier-badge tier-' + escHtml(source.tier) + '">' + escHtml(tierLabel) + '</span>' +
        '<span class="stance-tag stance-' + escHtml(source.stance) + '">' + escHtml(stanceLabel) + '</span>' +
        '<span class="credibility-label">' + escHtml(source.credibility_label || '') + '</span>' +
      '</div>' +
      '<div class="source-title">' + escHtml(source.title || '') + '</div>' +
      '<div class="source-url"><a href="' + escHtml(safeUrl(source.url)) + '" target="_blank" rel="noopener noreferrer">' + escHtml(source.url) + '</a></div>' +
      '<div class="source-snippet">' + escHtml(source.snippet || '') + '</div>';
    list.appendChild(card);
  });
}

// Form submission
let currentClaim = '';

document.getElementById('verify-form').addEventListener('submit', async e => {
  e.preventDefault();
  const errorEl = document.getElementById('form-error');
  errorEl.hidden = true;

  const text = document.getElementById('claim-input').value.trim();
  const hasImage = imageInput.files.length > 0;
  if (!text && !hasImage) {
    errorEl.textContent = t('error_empty');
    errorEl.hidden = false;
    return;
  }

  currentClaim = text;
  const formData = new FormData(e.target);
  showState('loading');
  setStep(1);

  let taskId;
  try {
    const res = await fetch('/verify', { method: 'POST', body: formData });
    const json = await res.json();
    if (json.error) throw new Error(json.error);
    taskId = json.task_id;
  } catch (err) {
    showState('error');
    document.getElementById('error-message').textContent = t('error_generic');
    return;
  }

  const es = new EventSource('/stream/' + taskId);

  es.addEventListener('progress', e => {
    const data = JSON.parse(e.data);
    setStep(data.step);
  });

  es.addEventListener('result', e => {
    es.close();
    const data = JSON.parse(e.data);
    const resolvedClaim = currentClaim || data.image_description || t('no_text_provided');
    const imageSrc = data.has_image && imagePreview.src ? imagePreview.src : null;
    renderResult(data.data || data, data.share_id, resolvedClaim, imageSrc);
    const resultData = data.data || data;
    const historyEntry = {
      id: crypto.randomUUID(),
      claim: resolvedClaim,
      timestamp: new Date().toISOString(),
      verdict: resultData.verdict,
      summary: resultData.summary,
      explanation: resultData.explanation,
      sources: resultData.sources || [],
      shareId: data.share_id || null,
      imageUrl: (data.has_image && data.share_id) ? '/share/' + data.share_id + '/image' : null,
    };
    addHistoryEntry(historyEntry);
    activeHistoryId = historyEntry.id;
    renderHistorySidebar();
    showState('result');
  });

  es.addEventListener('error', e => {
    es.close();
    let msg = t('error_generic');
    try { msg = t(JSON.parse(e.data).message) || msg; } catch (_) {}
    document.getElementById('error-message').textContent = msg;
    showState('error');
  });
});

// Reset buttons
document.getElementById('reset-btn').addEventListener('click', () => showState('input'));
document.getElementById('error-reset-btn').addEventListener('click', () => showState('input'));

// Share button — copy URL to clipboard
document.getElementById('share-btn').addEventListener('click', () => {
  const url = document.getElementById('share-url').value;
  navigator.clipboard.writeText(url).then(() => {
    const btn = document.getElementById('share-btn');
    const original = btn.textContent;
    btn.textContent = t('share_copied');
    setTimeout(() => { btn.textContent = original; }, 2000);
  });
});

// Initialise with English
renderHistorySidebar();
setLang('en');

// Auto-display shared result when navigating to /share/<id>
if (window.__SHARED_RESULT__) {
  renderResult(window.__SHARED_RESULT__, null, window.__SHARED_CLAIM__ || '', window.__SHARED_IMAGE_URL__ || null);
  showState('result');
}
