/**
 * Merge Video — Frontend App
 */

const API_URL = window.location.origin.includes('localhost')
    ? 'http://localhost:8000'
    : window.location.origin + '/api';

const USER_ID = 'web_' + getOrCreateUserId();
let urlCount = 2;

// === Init ===

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
});

// === Auth ===

function authorizeYouTube() {
    const authUrl = `${API_URL}/auth/youtube?user_id=${encodeURIComponent(USER_ID)}`;
    window.open(authUrl, '_blank', 'width=600,height=700');
    // Poll for auth completion
    const poll = setInterval(async () => {
        const ok = await checkAuth();
        if (ok) clearInterval(poll);
    }, 3000);
    setTimeout(() => clearInterval(poll), 120000);
}

async function checkAuth() {
    try {
        const resp = await fetch(`${API_URL}/auth/status?user_id=${encodeURIComponent(USER_ID)}`);
        const data = await resp.json();
        const el = document.getElementById('auth-status');
        const btn = document.getElementById('auth-btn');

        if (data.authorized) {
            el.className = 'auth-status auth-status--authorized';
            el.querySelector('.auth-status__icon').textContent = '✅';
            el.querySelector('.auth-status__text').textContent = 'YouTube connected';
            if (btn) btn.style.display = 'none';
            return true;
        }
    } catch (e) {
        console.warn('Auth check failed:', e);
    }
    return false;
}

// === URL Management ===

function addUrl() {
    if (urlCount >= 10) return;
    urlCount++;
    const list = document.getElementById('url-list');
    const row = document.createElement('div');
    row.className = 'url-row';
    row.innerHTML = `
    <span class="url-row__num">${urlCount}</span>
    <input type="url" class="url-input" placeholder="https://youtube.com/watch?v=..." data-index="${urlCount - 1}">
    <button class="url-row__remove" onclick="removeUrl(this)" title="Remove">×</button>
  `;
    list.appendChild(row);
    row.querySelector('input').focus();
}

function removeUrl(btn) {
    const row = btn.closest('.url-row');
    const list = document.getElementById('url-list');
    if (list.children.length <= 2) return; // minimum 2
    row.remove();
    urlCount--;
    renumberUrls();
}

function renumberUrls() {
    const rows = document.querySelectorAll('.url-row');
    rows.forEach((row, i) => {
        row.querySelector('.url-row__num').textContent = i + 1;
        row.querySelector('.url-input').dataset.index = i;
    });
}

function getUrls() {
    const inputs = document.querySelectorAll('.url-input:not(#video-title)');
    const urls = [];
    inputs.forEach(input => {
        const val = input.value.trim();
        if (val && isYouTubeUrl(val)) {
            urls.push(val);
        }
    });
    return urls;
}

function isYouTubeUrl(url) {
    return /^https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)[\w-]+/.test(url);
}

// === Merge ===

async function startMerge() {
    const urls = getUrls();
    if (urls.length < 2) {
        showError('Add at least 2 valid YouTube URLs');
        return;
    }

    const title = document.getElementById('video-title').value.trim() || 'Merged Video';
    const mergeBtn = document.getElementById('merge-btn');

    // Check auth first
    const authed = await checkAuth();
    if (!authed) {
        showError('Connect your YouTube account first');
        return;
    }

    // Hide previous results
    hide('result');
    hide('error');
    show('progress');
    mergeBtn.disabled = true;
    mergeBtn.textContent = '⏳ Processing...';
    updateProgress(5, 'Submitting...');

    try {
        const resp = await fetch(`${API_URL}/merge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urls, title, user_id: USER_ID }),
        });

        if (!resp.ok) {
            const err = await resp.text();
            throw new Error(err);
        }

        const data = await resp.json();
        pollJob(data.job_id);

    } catch (e) {
        showError(e.message);
        mergeBtn.disabled = false;
        mergeBtn.textContent = '🚀 Merge & Upload to YouTube';
        hide('progress');
    }
}

async function pollJob(jobId) {
    const mergeBtn = document.getElementById('merge-btn');

    const statusMap = {
        queued: { pct: 10, label: '⏳ Queued...' },
        downloading: { pct: 30, label: '⬇️ Downloading videos...' },
        merging: { pct: 60, label: '🔄 Merging videos...' },
        uploading: { pct: 85, label: '⬆️ Uploading to YouTube...' },
    };

    const poll = setInterval(async () => {
        try {
            const resp = await fetch(`${API_URL}/status/${jobId}`);
            const data = await resp.json();

            const info = statusMap[data.status];
            if (info) {
                updateProgress(info.pct, info.label);
            }

            if (data.status === 'done') {
                clearInterval(poll);
                updateProgress(100, '✅ Done!');
                setTimeout(() => {
                    hide('progress');
                    showResult(data.result_url);
                    mergeBtn.disabled = false;
                    mergeBtn.textContent = '🚀 Merge & Upload to YouTube';
                }, 500);
            }

            if (data.status === 'error') {
                clearInterval(poll);
                hide('progress');
                showError(data.error || 'Unknown error');
                mergeBtn.disabled = false;
                mergeBtn.textContent = '🚀 Merge & Upload to YouTube';
            }

        } catch (e) {
            console.warn('Poll error:', e);
        }
    }, 3000);

    // Timeout after 10 minutes
    setTimeout(() => {
        clearInterval(poll);
        showError('Processing timed out. Please try again.');
        mergeBtn.disabled = false;
        mergeBtn.textContent = '🚀 Merge & Upload to YouTube';
    }, 600000);
}

// === UI Helpers ===

function updateProgress(pct, text) {
    document.getElementById('progress-fill').style.width = pct + '%';
    document.getElementById('progress-text').textContent = text;
}

function showResult(url) {
    const el = document.getElementById('result');
    el.style.display = 'block';
    const link = document.getElementById('result-link');
    link.href = url;
    link.textContent = 'Watch on YouTube →';
}

function showError(msg) {
    const el = document.getElementById('error');
    el.textContent = '❌ ' + msg;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 8000);
}

function show(id) { document.getElementById(id).style.display = 'block'; }
function hide(id) { document.getElementById(id).style.display = 'none'; }

function getOrCreateUserId() {
    let id = localStorage.getItem('merge_video_uid');
    if (!id) {
        id = Math.random().toString(36).slice(2, 14);
        localStorage.setItem('merge_video_uid', id);
    }
    return id;
}
