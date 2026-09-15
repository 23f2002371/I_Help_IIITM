/* ── Chat JS ───────────────────────────────────────────────────────────────── */

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

const inputEl       = document.getElementById('questionInput');
const sendBtn       = document.getElementById('sendBtn');
const messagesEl    = document.getElementById('chatMessages');
const clearBtn      = document.getElementById('clearBtn');
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar       = document.querySelector('.sidebar');
const statusDot     = document.getElementById('statusDot');
const statusText    = document.getElementById('statusText');
const adminAccess   = document.getElementById('adminAccess');
const newChatAccess = document.getElementById('newChatAccess');
const historyListEl = document.getElementById('historyList');
const HISTORY_KEY   = 'ihelp-chat-history-v1';
const SIDEBAR_KEY   = 'ihelp-sidebar-hidden';

let conversations = loadConversations();
let activeConversationId = conversations[0]?.id || null;

// ── Configure marked.js ────────────────────────────────────────────────────
marked.setOptions({
  breaks: true,     // \n → <br>
  gfm: true,
  headerIds: false,
  mangle: false,
});

// ── Helpers ────────────────────────────────────────────────────────────────

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}

function autoResize() {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
}

function scrollBottom() {
  messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: 'smooth' });
}

function typesetMath(element) {
  if (!window.MathJax?.typesetPromise) {
    element.dataset.mathPending = 'true';
    return;
  }

  const startup = window.MathJax.startup?.promise || Promise.resolve();
  startup.then(() => window.MathJax.typesetPromise([element])).catch(() => {});
}

document.addEventListener('mathjax-ready', () => {
  document.querySelectorAll('[data-math-pending]').forEach((element) => {
    delete element.dataset.mathPending;
    typesetMath(element);
  });
});

function loadConversations() {
  try {
    const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function saveConversations() {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(conversations));
}

function createConversation() {
  const conversation = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    title: 'New conversation',
    updatedAt: Date.now(),
    messages: [],
  };
  conversations.unshift(conversation);
  activeConversationId = conversation.id;
  saveConversations();
  renderHistory();
  return conversation;
}

function getActiveConversation() {
  return conversations.find(({ id }) => id === activeConversationId);
}

function renderHistory() {
  conversations.sort((a, b) => b.updatedAt - a.updatedAt);
  historyListEl.innerHTML = conversations.length
    ? conversations.slice(0, 12).map((conversation) => `
        <button class="history-item ${conversation.id === activeConversationId ? 'active' : ''}"
          type="button" data-conversation-id="${conversation.id}">
          <span class="history-item-title">${escapeHtml(conversation.title)}</span>
          <span class="history-item-count">${conversation.messages.filter(({ role }) => role === 'user').length}</span>
        </button>
      `).join('')
    : '<div class="history-empty">Your conversations will appear here.</div>';
}

function renderConversation(conversation) {
  messagesEl.innerHTML = '';
  if (!conversation || conversation.messages.length === 0) {
    renderWelcome();
    return;
  }

  conversation.messages.forEach((message) => {
    if (message.role === 'user') addUserMessage(message.text);
    if (message.role === 'assistant') addBotMessage(message.result, false);
  });
  scrollBottom();
}

function startNewChat() {
  const active = getActiveConversation();
  if (active && active.messages.length === 0) {
    renderConversation(active);
    return;
  }
  createConversation();
  renderConversation(getActiveConversation());
}

// ── Server status check ────────────────────────────────────────────────────

async function checkStatus() {
  try {
    const r = await fetch('/api/health');
    const d = await r.json();
    if (d.status === 'ok') {
      statusDot.className = 'status-dot online';
      const parts = [];
      if (d.gemini_configured) parts.push('Gemini ✓');
      if (d.web_search_configured) parts.push('Web Search ✓');
      if (d.sources_count > 0) parts.push(`${d.sources_count} docs`);
      statusText.textContent = parts.length ? parts.join(' · ') : 'Ready';
    } else {
      throw new Error();
    }
  } catch {
    statusDot.className = 'status-dot offline';
    statusText.textContent = 'Offline';
  }
}

// ── Welcome message ────────────────────────────────────────────────────────

function renderWelcome() {
  messagesEl.innerHTML = `
    <div class="welcome-state" id="welcomeState">
      <div class="welcome-icon">🎓</div>
      <div class="welcome-title">Welcome to IHelp</div>
      <div class="welcome-sub">Your AI assistant for IIT Madras BS degree course policies, grading, and more.</div>
      <div class="suggestion-chips">
        <button class="chip" onclick="sendChip(this)">What's the passing criteria for BDM?</button>
        <button class="chip" onclick="sendChip(this)">Project submission guidelines</button>
        <button class="chip" onclick="sendChip(this)">Business Analytics grading breakdown</button>
        <button class="chip" onclick="sendChip(this)">Assignment deadline policy</button>
      </div>
    </div>
  `;
}

function removeWelcome() {
  const ws = document.getElementById('welcomeState');
  if (ws) ws.remove();
}

function sendChip(btn) {
  inputEl.value = btn.textContent;
  sendMessage();
}

function askFollowUp(btn) {
  inputEl.value = btn.textContent;
  sendMessage();
}

// ── Message rendering ──────────────────────────────────────────────────────

function addUserMessage(text) {
  removeWelcome();
  const row = document.createElement('div');
  row.className = 'msg-row user';
  row.innerHTML = `
    <div class="msg-avatar">👤</div>
    <div>
      <div class="msg-bubble">${escapeHtml(text)}</div>
      <div class="msg-timestamp">${formatTime(new Date())}</div>
    </div>
  `;
  messagesEl.appendChild(row);
  scrollBottom();
  return row;
}

function addTypingIndicator() {
  removeWelcome();
  const row = document.createElement('div');
  row.className = 'msg-row bot';
  row.id = 'typingIndicator';
  row.innerHTML = `
    <div class="msg-avatar">🎓</div>
    <div class="typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  messagesEl.appendChild(row);
  scrollBottom();
  return row;
}

function removeTypingIndicator() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

function getBadgeHtml(result) {
  const st = result.source_type;
  if (st === 'greeting') return `<span class="source-badge greet">👋 Greeting</span>`;
  if (st === 'documents') return `<span class="source-badge docs">📄 From Documents</span>`;
  if (st === 'web') return `<span class="source-badge web">🌐 Web Search</span>`;
  if (st === 'external_llm') return `<span class="source-badge external">⚠️ External knowledge — verify important details</span>`;
  if (st === 'none') return `<span class="source-badge err">❓ Not Found</span>`;
  if (result.used_fallback) return `<span class="source-badge fallback">⚠️ Extractive Fallback</span>`;
  return '';
}

function getCitationsHtml(citations) {
  if (!citations || citations.length === 0) return '';

  const items = citations.map((c, i) => {
    const course = c.course_name ? `<span class="citation-meta">Course: ${escapeHtml(c.course_name)}</span>` : '';
    const page = c.page_number && c.page_number !== -1 ? ` · Page ${c.page_number}` : '';
    const rel = c.relevance ? ` · Relevance: ${Math.round(c.relevance * 100)}%` : '';
    const url = c.source_url
      ? `<a href="${escapeHtml(c.source_url)}" target="_blank" rel="noopener">${escapeHtml(c.source_url)}</a>`
      : '';
    return `
      <div class="citation-item">
        <div class="citation-source">${escapeHtml(c.source_name || 'Unknown source')}${page}${rel}</div>
        ${course}
        ${url ? `<div class="citation-meta">${url}</div>` : ''}
        ${c.excerpt ? `<div class="citation-excerpt">${escapeHtml(c.excerpt)}${c.excerpt.length >= 300 ? '…' : ''}</div>` : ''}
      </div>
    `;
  }).join('');

  return `
    <div class="citations-block">
      <button class="citations-toggle" onclick="toggleCitations(this)">
        <span class="arrow">▼</span>
        <span>${citations.length} source${citations.length > 1 ? 's' : ''} used</span>
      </button>
      <div class="citations-list hidden">${items}</div>
    </div>
  `;
}

function toggleCitations(btn) {
  const list = btn.nextElementSibling;
  const isOpen = !list.classList.contains('hidden');
  list.classList.toggle('hidden', isOpen);
  btn.classList.toggle('open', !isOpen);
}

function getFollowUpQuestions(result) {
  const answer = result.answer || '';
  if (/quiz|assignment|exam|marks|score|grading|passing/i.test(answer)) {
    return ['How is the final score calculated?', 'What are the passing criteria?', 'Can you show me a worked example?'];
  }
  if (/deadline|submit|submission|date|late/i.test(answer)) {
    return ['What happens if I miss the deadline?', 'Are there any late submission rules?', 'What should I submit?'];
  }
  return ['Can you explain that more simply?', 'Can you give me an example?', 'What should I ask about next?'];
}

function getFollowUpsHtml(result) {
  return `
    <div class="follow-up-block">
      <div class="follow-up-label">Continue exploring</div>
      <div class="follow-up-list">
        ${getFollowUpQuestions(result).map((question) => `
          <button class="follow-up-btn" type="button" onclick="askFollowUp(this)">${escapeHtml(question)}</button>
        `).join('')}
      </div>
    </div>
  `;
}

function addBotMessage(result, includeFollowUps = true) {
  removeTypingIndicator();
  const row = document.createElement('div');
  row.className = 'msg-row bot';

  const badge   = getBadgeHtml(result);
  const bodyHtml = marked.parse(result.answer || '');
  const citations = getCitationsHtml(result.citations);
  const followUps = includeFollowUps ? getFollowUpsHtml(result) : '';

  row.innerHTML = `
    <div class="msg-avatar">🎓</div>
    <div style="min-width:0; flex:1;">
      <div class="msg-bubble">
        ${badge}
        <div class="markdown-body">${bodyHtml}</div>
        ${citations}
        ${followUps}
      </div>
      <div class="msg-timestamp">${formatTime(new Date())}</div>
    </div>
  `;
  messagesEl.appendChild(row);
  typesetMath(row);
  scrollBottom();
}

function addErrorMessage(msg) {
  removeTypingIndicator();
  const row = document.createElement('div');
  row.className = 'msg-row bot';
  row.innerHTML = `
    <div class="msg-avatar">🎓</div>
    <div>
      <div class="msg-bubble">
        <span class="source-badge err">⚠️ Error</span>
        <div>${escapeHtml(msg)}</div>
      </div>
      <div class="msg-timestamp">${formatTime(new Date())}</div>
    </div>
  `;
  messagesEl.appendChild(row);
  scrollBottom();
}

// ── Send logic ─────────────────────────────────────────────────────────────

async function sendMessage() {
  const question = inputEl.value.trim();
  if (!question || sendBtn.disabled) return;

  const conversation = getActiveConversation() || createConversation();
  if (conversation.messages.length === 0) {
    conversation.title = question.length > 42 ? `${question.slice(0, 42)}...` : question;
  }
  conversation.messages.push({ role: 'user', text: question });
  conversation.updatedAt = Date.now();
  saveConversations();
  renderHistory();
  addUserMessage(question);
  inputEl.value = '';
  inputEl.style.height = 'auto';
  sendBtn.disabled = true;
  addTypingIndicator();

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, top_k: 4 }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      addErrorMessage(data.error || 'Something went wrong.');
    } else {
      addBotMessage(data);
      conversation.messages.push({ role: 'assistant', text: data.answer || '', result: data });
      conversation.updatedAt = Date.now();
      saveConversations();
      renderHistory();
    }
  } catch {
    addErrorMessage('Could not reach the server. Is the backend running?');
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

// ── Events ─────────────────────────────────────────────────────────────────

sendBtn.addEventListener('click', sendMessage);

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

inputEl.addEventListener('input', autoResize);

clearBtn.addEventListener('click', startNewChat);
newChatAccess.addEventListener('click', startNewChat);

historyListEl.addEventListener('click', (event) => {
  const item = event.target.closest('[data-conversation-id]');
  if (!item) return;
  activeConversationId = item.dataset.conversationId;
  renderHistory();
  renderConversation(getActiveConversation());
});

function isMobileLayout() {
  return window.matchMedia('(max-width: 700px)').matches;
}

function updateSidebarToggle() {
  const hidden = sidebar.classList.contains('collapsed') || sidebar.classList.contains('open');
  sidebarToggle.setAttribute('aria-label', hidden ? 'Show sidebar' : 'Hide sidebar');
  sidebarToggle.setAttribute('title', hidden ? 'Show sidebar' : 'Hide sidebar');
  sidebarToggle.querySelector('.sidebar-chevron').textContent = hidden ? '›' : '‹';
}

sidebarToggle.addEventListener('click', () => {
  if (isMobileLayout()) {
    sidebar.classList.toggle('open');
  } else {
    sidebar.classList.toggle('collapsed');
    localStorage.setItem(SIDEBAR_KEY, sidebar.classList.contains('collapsed') ? 'true' : 'false');
  }
  updateSidebarToggle();
});

adminAccess.addEventListener('click', () => {
  window.location.href = '/admin';
});

// Close sidebar on message tap (mobile)
messagesEl.addEventListener('click', () => {
  if (sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
    updateSidebarToggle();
  }
});

messagesEl.addEventListener('scroll', () => {
  document.querySelector('.chat-header').classList.toggle('compact', messagesEl.scrollTop > 24);
}, { passive: true });

// ── Init ───────────────────────────────────────────────────────────────────
if (!isMobileLayout() && localStorage.getItem(SIDEBAR_KEY) === 'true') {
  sidebar.classList.add('collapsed');
}
updateSidebarToggle();
if (!activeConversationId) createConversation();
renderHistory();
renderConversation(getActiveConversation());
checkStatus();
inputEl.focus();
