/* ── Admin JS ──────────────────────────────────────────────────────────────── */

const BACKEND_URL = window.APP_CONFIG?.BACKEND_URL || 'https://your-render-app-name.onrender.com';

async function pingRenderWakeup() {
  if (!BACKEND_URL) return;
  try {
    await fetch(`${BACKEND_URL}/api/health`, { method: 'GET', cache: 'no-store' });
  } catch (error) {
    console.warn('Render wake-up ping failed:', error);
  }
}

setInterval(pingRenderWakeup, 4 * 60 * 1000);
window.addEventListener('focus', pingRenderWakeup);
window.addEventListener('load', pingRenderWakeup);

const loginOverlay  = document.getElementById('loginOverlay');
const adminContent  = document.getElementById('adminContent');
const loginBtn      = document.getElementById('loginBtn');
const logoutBtn     = document.getElementById('logoutBtn');
const loginError    = document.getElementById('loginError');
const toastContainer = document.getElementById('toastContainer');
const sidebar       = document.querySelector('.sidebar');

let ADMIN_PASSWORD = sessionStorage.getItem('cg_admin_password') || '';

// ── Auth ──────────────────────────────────────────────────────────────────

function authHeaders(extra = {}) {
  return { 'X-Admin-Password': ADMIN_PASSWORD, ...extra };
}

function showLoginError(msg) {
  loginError.textContent = msg;
  loginError.classList.remove('hidden');
}

function enterAdmin() {
  loginOverlay.style.display = 'none';
  adminContent.classList.remove('hidden');
  loadSources();
}

async function tryAutoLogin() {
  if (!ADMIN_PASSWORD) return;
  try {
    const r = await fetch('/api/admin/sources', { headers: authHeaders() });
    if (r.ok) enterAdmin();
  } catch {}
}

loginBtn.addEventListener('click', async () => {
  const pw = document.getElementById('adminPassword').value;
  loginBtn.disabled = true;
  loginBtn.textContent = 'Logging in…';
  try {
    const r = await fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pw }),
    });
    const d = await r.json();
    if (r.ok && d.ok) {
      ADMIN_PASSWORD = pw;
      sessionStorage.setItem('cg_admin_password', pw);
      enterAdmin();
    } else {
      showLoginError(d.error || 'Incorrect password');
    }
  } catch {
    showLoginError('Could not reach server.');
  } finally {
    loginBtn.disabled = false;
    loginBtn.textContent = 'Log In';
  }
});

document.getElementById('adminPassword').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') loginBtn.click();
});

logoutBtn.addEventListener('click', () => {
  ADMIN_PASSWORD = '';
  sessionStorage.removeItem('cg_admin_password');
  location.reload();
});

// ── Toast notifications ───────────────────────────────────────────────────

function showToast(msg, type = 'info', duration = 4000) {
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  toastContainer.appendChild(t);
  setTimeout(() => t.remove(), duration);
}

// ── Inline status ─────────────────────────────────────────────────────────

function showInlineStatus(elId, msg, type) {
  const el = document.getElementById(elId);
  el.textContent = msg;
  el.className = `status-toast ${type}`;
  el.classList.remove('hidden');
}

function hideInlineStatus(elId) {
  const el = document.getElementById(elId);
  if (el) el.classList.add('hidden');
}

// ── Progress bar ─────────────────────────────────────────────────────────

function showProgress(barId, fillId) {
  document.getElementById(barId).classList.remove('hidden');
  document.getElementById(fillId).style.width = '100%';
}

function hideProgress(barId) {
  document.getElementById(barId).classList.add('hidden');
}

// ── Drop zone ─────────────────────────────────────────────────────────────

const dropZone = document.getElementById('dropZone');
const pdfFileInput = document.getElementById('pdfFile');
const selectedFileName = document.getElementById('selectedFileName');

dropZone.addEventListener('click', () => pdfFileInput.click());

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file && file.type === 'application/pdf') {
    setSelectedFile(file);
  } else {
    showToast('Please drop a PDF file.', 'error');
  }
});

pdfFileInput.addEventListener('change', () => {
  if (pdfFileInput.files[0]) setSelectedFile(pdfFileInput.files[0]);
});

function setSelectedFile(file) {
  // Create a new DataTransfer to assign to the input
  const dt = new DataTransfer();
  dt.items.add(file);
  pdfFileInput.files = dt.files;
  selectedFileName.textContent = `📄 ${file.name} (${(file.size / 1024).toFixed(0)} KB)`;
  selectedFileName.classList.remove('hidden');
}

// ── Upload PDF ────────────────────────────────────────────────────────────

document.getElementById('uploadPdfBtn').addEventListener('click', async () => {
  if (!pdfFileInput.files.length) {
    showToast('Please choose or drop a PDF file first.', 'error');
    return;
  }

  const btn = document.getElementById('uploadPdfBtn');
  btn.disabled = true;
  showProgress('uploadProgress', 'uploadProgressFill');
  showInlineStatus('uploadStatus', '⏳ Uploading and indexing…', 'info');

  const formData = new FormData();
  formData.append('file', pdfFileInput.files[0]);
  formData.append('source_name', document.getElementById('pdfSourceName').value);
  formData.append('topic', document.getElementById('pdfTopic').value);
  formData.append('forced_course_name', document.getElementById('pdfCourseName').value);

  try {
    const r = await fetch('/api/admin/upload-pdf', {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    });
    const d = await r.json();
    hideProgress('uploadProgress');
    if (!r.ok) {
      showInlineStatus('uploadStatus', `❌ ${d.error || 'Upload failed'}`, 'error');
      showToast(d.error || 'Upload failed.', 'error');
    } else {
      showInlineStatus('uploadStatus', `✅ Indexed "${d.source_name}" — ${d.chunks_indexed} chunks created.`, 'success');
      showToast(`Indexed "${d.source_name}" successfully!`, 'success');
      // Reset form
      pdfFileInput.value = '';
      selectedFileName.classList.add('hidden');
      document.getElementById('pdfSourceName').value = '';
      document.getElementById('pdfTopic').value = '';
      document.getElementById('pdfCourseName').value = '';
      loadSources();
    }
  } catch {
    hideProgress('uploadProgress');
    showInlineStatus('uploadStatus', '❌ Could not reach server.', 'error');
  } finally {
    btn.disabled = false;
  }
});

// ── Add Link ──────────────────────────────────────────────────────────────

document.getElementById('addLinkBtn').addEventListener('click', async () => {
  const url = document.getElementById('linkUrl').value.trim();
  if (!url) {
    showToast('Please enter a URL.', 'error');
    return;
  }

  const btn = document.getElementById('addLinkBtn');
  btn.disabled = true;
  showInlineStatus('linkStatus', '⏳ Fetching and indexing…', 'info');

  const payload = {
    url,
    source_type: document.getElementById('linkType').value,
    source_name: document.getElementById('linkSourceName').value,
    topic: document.getElementById('linkTopic').value,
    forced_course_name: document.getElementById('linkCourseName').value,
  };

  try {
    const r = await fetch('/api/admin/add-link', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(payload),
    });
    const d = await r.json();
    if (!r.ok) {
      showInlineStatus('linkStatus', `❌ ${d.error || 'Failed to add link'}`, 'error');
      showToast(d.error || 'Failed to add link.', 'error');
    } else {
      showInlineStatus('linkStatus', `✅ Indexed "${d.source_name}" — ${d.chunks_indexed} chunks created.`, 'success');
      showToast(`Indexed "${d.source_name}" successfully!`, 'success');
      document.getElementById('linkUrl').value = '';
      document.getElementById('linkSourceName').value = '';
      document.getElementById('linkTopic').value = '';
      document.getElementById('linkCourseName').value = '';
      loadSources();
    }
  } catch {
    showInlineStatus('linkStatus', '❌ Could not reach server.', 'error');
  } finally {
    btn.disabled = false;
  }
});

// ── Sources Table ─────────────────────────────────────────────────────────

document.getElementById('refreshSourcesBtn').addEventListener('click', loadSources);

async function loadSources() {
  const tbody = document.getElementById('sourcesTableBody');
  const table = document.getElementById('sourcesTable');
  const empty = document.getElementById('sourcesEmpty');

  tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:24px;">Loading…</td></tr>';
  table.style.display = 'table';
  empty.style.display = 'none';

  try {
    const r = await fetch('/api/admin/sources', { headers: authHeaders() });
    const sources = await r.json();

    if (!r.ok) {
      showToast(sources.error || 'Failed to load sources.', 'error');
      return;
    }

    if (sources.length === 0) {
      table.style.display = 'none';
      empty.style.display = 'block';
      updateStats(0, 0, 0);
      return;
    }

    // Update stats
    const totalChunks = sources.reduce((s, x) => s + x.chunk_count, 0);
    const allCourses = new Set(sources.flatMap(s => s.course_names));
    updateStats(sources.length, totalChunks, allCourses.size);

    tbody.innerHTML = '';
    sources.forEach(s => {
      const courseTags = (s.course_names || [])
        .map(c => `<span class="course-tag">${escapeHtml(c)}</span>`)
        .join('');
      const lastIdx = s.last_indexed
        ? new Date(s.last_indexed).toLocaleString()
        : '—';
      const srcUrl = s.source_url
        ? `<div class="source-url-cell"><a href="${escapeHtml(s.source_url)}" target="_blank" style="color:var(--info);font-size:11px;">${escapeHtml(s.source_url.substring(0,60))}${s.source_url.length > 60 ? '…' : ''}</a></div>`
        : '';

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>
          <div class="source-name-cell">${escapeHtml(s.source_name)}</div>
          ${srcUrl}
        </td>
        <td><span class="type-pill">${escapeHtml(s.source_type || 'pdf')}</span></td>
        <td>${courseTags || '<span style="color:var(--text-muted)">—</span>'}</td>
        <td>${s.chunk_count}</td>
        <td style="color:var(--text-dim);font-size:12px;">${lastIdx}</td>
        <td>
          <div class="table-actions">
            <button class="btn-ghost btn-sm" data-action="reindex" data-source="${escapeHtml(s.source_name)}">↻ Re-index</button>
            <button class="btn-danger" data-action="delete"  data-source="${escapeHtml(s.source_name)}">Delete</button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll('[data-action="reindex"]').forEach(btn =>
      btn.addEventListener('click', () => reindexSource(btn.dataset.source))
    );
    tbody.querySelectorAll('[data-action="delete"]').forEach(btn =>
      btn.addEventListener('click', () => deleteSource(btn.dataset.source))
    );

  } catch {
    showToast('Could not reach server.', 'error');
  }
}

function updateStats(sources, chunks, courses) {
  document.getElementById('statSources').textContent = sources;
  document.getElementById('statChunks').textContent  = chunks;
  document.getElementById('statCourses').textContent = courses;
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

// ── Reindex / Delete ──────────────────────────────────────────────────────

async function reindexSource(name) {
  showToast(`Re-indexing "${name}"…`, 'info');
  try {
    const r = await fetch(`/api/admin/reindex/${encodeURIComponent(name)}`, {
      method: 'POST',
      headers: authHeaders(),
    });
    const d = await r.json();
    if (!r.ok) {
      showToast(d.error || 'Re-index failed.', 'error');
    } else {
      showToast(`Re-indexed "${name}" — ${d.chunks_indexed} chunks.`, 'success');
      loadSources();
    }
  } catch {
    showToast('Could not reach server.', 'error');
  }
}

async function deleteSource(name) {
  if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
  try {
    const r = await fetch(`/api/admin/sources/${encodeURIComponent(name)}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    const d = await r.json();
    if (!r.ok) {
      showToast(d.error || 'Delete failed.', 'error');
    } else {
      showToast(`Deleted "${name}".`, 'success');
      loadSources();
    }
  } catch {
    showToast('Could not reach server.', 'error');
  }
}

// ── Init ──────────────────────────────────────────────────────────────────
tryAutoLogin();
