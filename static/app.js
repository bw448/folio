/* Folio 0.8 — local-first reading & research workbench */
"use strict";

/* ------------------------------------------------------------------ utils */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const ICONS = {
  home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
  library: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  pen: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4"/><path d="M21 3v6h-6"/>',
  chart: '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  arrow: '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
  back: '<path d="M19 12H5"/><path d="m12 19-7-7 7-7"/>',
  star: '<path d="m12 3 2.9 5.9 6.5.9-4.7 4.6 1.1 6.5-5.8-3-5.8 3 1.1-6.5L3.6 9.8l6.5-.9Z"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>',
  chat: '<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4Z"/>',
  translate: '<path d="M4 5h8M8 3v2c0 4-2 7-5 9"/><path d="M4 11c2 3 5 5 8 6"/><path d="m13 21 4-10 4 10"/><path d="M14.5 17h5"/>',
  summary: '<path d="M4 6h16M4 12h16M4 18h10"/>',
  note: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h5"/>',
  highlight: '<path d="m9 11 3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
  play: '<path d="m8 5 11 7-11 7Z"/>',
  trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/>',
  more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>',
  contrast: '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18Z" fill="currentColor" stroke="none"/>',
  download: '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
  upload: '<path d="M12 21V9"/><path d="m7 14 5-5 5 5"/><path d="M5 3h14"/>',
  check: '<path d="m5 12 5 5L20 7"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  flame: '<path d="M12 2s4 4 4 8a4 4 0 0 1-8 0c0-1 .5-2 1-3-2 1-4 3-4 6a7 7 0 0 0 14 0c0-5-7-11-7-11Z"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  volume: '<path d="M11 5 6 9H3v6h3l5 4Z"/><path d="M15 9a4 4 0 0 1 0 6"/><path d="M18 6a8 8 0 0 1 0 12"/>',
  award: '<circle cx="12" cy="9" r="5"/><path d="m8.5 13.5-1 8 4.5-2 4.5 2-1-8"/>',
  scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5Z"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
  focus: '<path d="M4 9V4h5"/><path d="M20 9V4h-5"/><path d="M4 15v5h5"/><path d="M20 15v5h-5"/>',
};

const icon = (name, cls = "") =>
  `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ""}</svg>`;

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text }; }
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data);
    throw new Error(detail || `请求失败 (${response.status})`);
  }
  return data;
}

const escapeHtml = (value = "") =>
  String(value).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
const escapeAttr = escapeHtml;
const escapeRegExp = (value = "") => String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const firstLine = (value = "") => String(value).split("\n")[0].trim();
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

function inlineMd(text) {
  let out = escapeHtml(text);
  out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
  out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return out;
}

function mdToHtml(markdown = "") {
  const lines = String(markdown).split(/\r?\n/);
  let html = "";
  let list = null;
  let inCode = false;
  let code = [];
  const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
  const splitRow = (row) => row.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => inlineMd(cell.trim()));
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (line.trim().startsWith("```")) {
      if (inCode) { html += `<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`; code = []; inCode = false; }
      else { closeList(); inCode = true; }
      index += 1;
      continue;
    }
    if (inCode) { code.push(line); index += 1; continue; }
    if (/^\s*\|/.test(line) && index + 1 < lines.length && /^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$/.test(lines[index + 1])) {
      closeList();
      const header = splitRow(line);
      index += 2;
      const rows = [];
      while (index < lines.length && /^\s*\|/.test(lines[index])) {
        rows.push(splitRow(lines[index]));
        index += 1;
      }
      html += `<table class="md-table"><thead><tr>${header.map((cell) => `<th>${cell}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
      continue;
    }
    if (/^#{1,3}\s+/.test(line)) { closeList(); html += `<h3>${inlineMd(line.replace(/^#{1,3}\s+/, ""))}</h3>`; index += 1; continue; }
    if (/^\s*[-*]\s+/.test(line)) { if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; } html += `<li>${inlineMd(line.replace(/^\s*[-*]\s+/, ""))}</li>`; index += 1; continue; }
    if (/^\s*\d+\.\s+/.test(line)) { if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; } html += `<li>${inlineMd(line.replace(/^\s*\d+\.\s+/, ""))}</li>`; index += 1; continue; }
    if (/^\s*>\s?/.test(line)) { closeList(); html += `<blockquote>${inlineMd(line.replace(/^\s*>\s?/, ""))}</blockquote>`; index += 1; continue; }
    if (!line.trim()) { closeList(); index += 1; continue; }
    closeList();
    html += `<p>${inlineMd(line)}</p>`;
    index += 1;
  }
  closeList();
  if (inCode) html += `<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`;
  return html;
}

const TAG_LABELS = { cet4: "四级", cet6: "六级", ky: "考研", toefl: "托福", ielts: "雅思", gre: "GRE", gk: "高考", zk: "中考" };
function tagChips(tags = "") {
  return String(tags || "").split(/\s+/).filter(Boolean)
    .map((tag) => `<span class="tag ${escapeAttr(tag)}">${TAG_LABELS[tag] || tag.toUpperCase()}</span>`).join("");
}
const isDue = (item) => !item.due || new Date(item.due).getTime() <= Date.now();
function formatDue(due) {
  if (!due) return "待复习";
  const date = new Date(due);
  if (Number.isNaN(date.getTime())) return "";
  const days = Math.ceil((date.getTime() - Date.now()) / 86400000);
  if (days <= 0) return "待复习";
  if (days === 1) return "明天";
  return `${days} 天后`;
}
function fmtDuration(seconds = 0) {
  if (seconds < 60) return `${seconds} 秒`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} 分钟`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return `${hours} 小时${minutes ? ` ${minutes} 分` : ""}`;
}
function fmtDate(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`;
}
function debounce(fn, wait = 250) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), wait); };
}
function toast(message, type = "") {
  const box = $("#toast");
  box.textContent = message;
  box.className = "toast" + (type === "error" ? " error" : "");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => box.classList.add("hidden"), 2800);
}
const loadingHtml = (text) => `<div class="loading"><span class="spinner"></span><span>${escapeHtml(text)}</span></div>`;
const errorHtml = (message) => `<div class="error-box">${escapeHtml(message)}${/Key|配置|接口|模型/i.test(message) ? '<br><button class="ghost" data-action="open-settings">打开设置</button>' : ""}</div>`;

/* ------------------------------------------------------------------ state */
const S = {
  view: "home",
  docs: [],
  collections: [],
  home: null,
  doc: null,
  page: 1,
  scale: 1.6,
  fitPending: false,
  layout: null,
  pageText: "",
  mode: "page",
  bilingual: null,
  bilingualLoading: false,
  highlights: [],
  notes: [],
  chat: [],
  chatLoading: false,
  outline: [],
  searchHits: [],
  searchQuery: "",
  railTab: "thumbs",
  railCollapsed: false,
  focusMode: false,
  railBeforeFocus: false,
  markFilter: null,
  vocab: new Map(),
  vocabList: [],
  vocabStats: null,
  due: [],
  highlightDue: [],
  review: { queue: [], index: 0, revealed: false, session: { again: 0, hard: 0, good: 0, easy: 0 } },
  selection: null,
  currentWord: null,
  panelTab: "dict",
  panelOpen: false,
  summary: null,
  fullTranslation: null,
  cet: { analysis: null, text: "", article: null, quiz: null, answers: {}, submitted: false },
  library: {
    q: "", sort: "recent", collection: null, favorite: false, status: "",
    author: "", venue: "", yearFrom: "", yearTo: "",
  },
  settings: null,
  storage: null,
  storageRequired: false,
  mistakeCount: 0,
  mistakes: [],
  mistakeType: "",
  mistakeQuery: "",
  lastSolveQuestion: "",
  lastSolve: "",
  theme: (localStorage.getItem("folio-theme") || localStorage.getItem("readmate-theme")) === "sepia" ? "sepia" : "light",
  readingStarted: Date.now(),
  progressTimer: null,
  ocrJob: null,
  ocrTimer: null,
  stats: null,
  onboarded: (localStorage.getItem("folio-onboarded") || localStorage.getItem("readmate-onboarded")) === "1",
  topics: [],
  topicsRefreshStarted: false,
  notifications: [],
  annualReport: "",
  compareMarkdown: "",
  syncConflicts: [],
  discover: {
    query: "",
    sources: ["arxiv", "openalex"],
    days: 365,
    sort: "recent",
    papers: [],
    errors: [],
    agent: null,
    loading: false,
    mode: "search",
    importing: -1,
  },
};

/* ------------------------------------------------------------------ theme */
function applyTheme(theme, persist = true) {
  if (theme !== "sepia") theme = "light";
  S.theme = theme;
  document.documentElement.dataset.theme = theme;
  if (persist) localStorage.setItem("folio-theme", theme);
  const btn = $("#themeBtn");
  if (btn) {
    btn.innerHTML = icon(theme === "sepia" ? "sun" : "contrast");
    btn.title = theme === "sepia" ? "切换浅色" : "切换护眼纸色";
  }
}
function cycleTheme() {
  applyTheme(S.theme === "sepia" ? "light" : "sepia");
}
function hydrateIcons() {
  $$("[data-icon]").forEach((el) => { el.innerHTML = icon(el.dataset.icon); });
}

/* ----------------------------------------------------------------- router */
const VIEW_IDS = { home: "#homeView", library: "#libraryView", discover: "#discoverView", reader: "#readerView", cet: "#cetView", vocab: "#vocabView", mistakes: "#mistakesView", review: "#reviewView", stats: "#statsView" };

async function go(view, options = {}) {
  if (S.view === "reader" && view !== "reader") flushProgress();
  S.view = view;
  $$(".nav-link").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  $$(".view").forEach((node) => node.classList.add("hidden"));
  const target = $(VIEW_IDS[view]);
  if (target) target.classList.remove("hidden");
  if (view !== "reader") {
    setPanel(false);
    $("#app").classList.remove("with-panel");
    if (S.focusMode) toggleFocusMode(false);
  }
  if (view !== "reader") history.replaceState(null, "", `#${view}`);
  if (view === "home") await renderHome();
  else if (view === "library") await renderLibrary();
  else if (view === "discover") await renderDiscover();
  else if (view === "cet") await renderCET();
  else if (view === "vocab") await renderVocab();
  else if (view === "mistakes") await renderMistakes();
  else if (view === "review") await renderReview();
  else if (view === "stats") await renderStats();
}

function topbar({ crumb = "", meta = "", center = "", right = "", back = false }) {
  $("#breadcrumb").textContent = crumb;
  $("#breadcrumb").title = crumb;
  $("#docMeta").textContent = meta;
  $("#topbarCenter").innerHTML = center;
  $("#topbarRight").innerHTML = right;
  $("#backBtn").classList.toggle("hidden", !back);
}

function setPanel(open, tab) {
  S.panelOpen = open;
  if (tab) S.panelTab = tab;
  $("#panel").classList.toggle("hidden", !open);
  $("#app").classList.toggle("with-panel", open && S.view === "reader");
  if (open) renderPanel();
}

/* ---------------------------------------------------------------- sidebar */
async function loadCollections() {
  try {
    S.collections = await api("/api/collections");
    renderCollections();
  } catch { /* ignore */ }
}

function renderCollections() {
  const box = $("#collectionList");
  if (!S.collections.length) {
    box.innerHTML = '<div class="collection-empty">还没有分类</div>';
    return;
  }
  box.innerHTML = S.collections.map((collection) => `
    <div class="collection-item ${S.library.collection === collection.id ? "active" : ""}" data-collection="${collection.id}">
      <span class="collection-dot" style="background:${escapeAttr(collection.color)}"></span>
      <span>${escapeHtml(collection.name)}</span>
      <span class="count">${collection.count}</span>
      <button class="collection-del" data-del-collection="${collection.id}" title="删除分类">×</button>
    </div>`).join("");
}

async function loadVocabCache() {
  try {
    const items = await api("/api/vocab");
    S.vocab = new Map(items.map((item) => [item.word.toLowerCase(), item]));
    S.vocabList = items;
    updateBadges();
  } catch { /* ignore */ }
}

async function loadDue() {
  try {
    const [vocab, highlights] = await Promise.all([
      api("/api/review/due"),
      api("/api/review/highlights/due"),
    ]);
    S.due = vocab;
    S.highlightDue = highlights;
    updateBadges();
  } catch { /* ignore */ }
}

function updateBadges() {
  $("#vocabCount").textContent = S.vocab.size ? String(S.vocab.size) : "";
  $("#mistakeCount").textContent = S.mistakeCount ? String(S.mistakeCount) : "";
  const due = S.due.length + S.highlightDue.length;
  $("#dueBadge").textContent = due ? String(due) : "";
}

async function loadSettings() {
  try { S.settings = await api("/api/settings"); } catch { /* ignore */ }
}

async function loadMistakeCount() {
  try {
    const data = await api("/api/wrong-questions/count");
    S.mistakeCount = data.count || 0;
    updateBadges();
  } catch { /* optional */ }
}

/* ------------------------------------------------------------------- home */
function greeting() {
  const hour = new Date().getHours();
  if (hour < 6) return "夜深了";
  if (hour < 12) return "早上好";
  if (hour < 18) return "下午好";
  return "晚上好";
}

async function renderHome() {
  topbar({
    crumb: "首页",
    right: `<button class="icon" data-action="shortcuts" title="快捷键">?</button>`,
  });
  const view = $("#homeView");
  view.innerHTML = `<div class="home">${loadingHtml("正在加载你的阅读空间…")}</div>`;
  try {
    const [data] = await Promise.all([api("/api/home"), loadCollections(), loadVocabCache(), loadDue()]);
    S.home = data;
    S.docs = data.recent || [];
    S.topics = data.topics || [];
    const recent = data.recent || [];
    const continueDoc = (data.continue_reading || [])[0];
    const word = data.daily_word;
    const dueTotal = (data.due || 0) + (data.highlight_due || 0);
    const stats = [
      { icon: "book", tone: "", value: data.documents, label: "文献" },
      { icon: "book", tone: "green", value: data.vocab, label: "生词" },
      { icon: "refresh", tone: "orange", value: dueTotal, label: "今日到期" },
      { icon: "flame", tone: "purple", value: data.streak, label: "连续学习天数" },
    ];
    view.innerHTML = `
      <div class="home">
        <section class="hero">
          <div class="hero-copy">
            <div class="hero-date">${new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "long" })}</div>
            <h1>${greeting()}，今天读点什么？</h1>
            <p>读论文、查单词、问 AI、背生词。文献和四六级，放在同一张书桌上。</p>
            <div class="hero-actions">
              <button class="primary" data-action="upload">${icon("upload")}导入 PDF</button>
              <button class="ghost" data-action="review-start">${icon("refresh")}开始复习${dueTotal ? ` · ${dueTotal}` : ""}</button>
              <button class="ghost" data-action="go-discover">${icon("compass")}发现文献</button>
            </div>
          </div>
          <div class="hero-current ${continueDoc ? "" : "empty"}">
            <div class="hero-current-label">${continueDoc ? "继续阅读" : "书桌还空着"}</div>
            ${continueDoc ? `
              <div class="hero-current-body">
                <div class="hero-cover"><img src="/api/documents/${continueDoc.id}/cover?v=${encodeURIComponent(continueDoc.updated_at || "")}" alt="" loading="lazy"></div>
                <div class="hero-current-info">
                  <strong>${escapeHtml(continueDoc.title)}</strong>
                  <span>${escapeHtml(continueDoc.authors || "未填写作者")}${continueDoc.year ? ` · ${continueDoc.year}` : ""}</span>
                  <div class="progress-track"><div class="progress-fill" style="width:${Math.round((continueDoc.progress || 0) * 100)}%"></div></div>
                  <div class="progress-meta"><span>第 ${continueDoc.last_page || 1} / ${continueDoc.pages} 页</span><span>${Math.round((continueDoc.progress || 0) * 100)}%</span></div>
                </div>
              </div>
              <button class="hero-current-action" data-action="open-doc" data-id="${continueDoc.id}" data-page="${continueDoc.last_page || 1}">${icon("arrow")}从上次位置继续</button>` : `
              <div class="hero-current-empty">
                <span class="hero-empty-mark">第一篇</span>
                <p>导入第一篇英文 PDF，Folio 会替你建好文献库、目录和阅读进度。</p>
                <button class="primary" data-action="upload">${icon("upload")}选择 PDF</button>
              </div>`}
          </div>
        </section>

        <section class="stat-strip">
          ${stats.map((stat) => `
            <div class="stat">
              <div class="stat-value">${stat.value}</div>
              <div class="stat-label">${stat.label}</div>
            </div>`).join("")}
        </section>

        <div class="home-columns">
          <section class="card daily-word">
            <div class="card-head"><h3>今日单词</h3><span class="eyebrow">每日一词</span></div>
            <div class="card-body">
              ${word ? `
                <div class="word">${escapeHtml(word.word)}</div>
                <div class="phonetic">/${escapeHtml(word.phonetic || "")}/</div>
                <div class="tag-row">${tagChips(word.tag)}</div>
                <div class="meaning">${escapeHtml(firstLine(word.translation) || firstLine(word.definition) || "—")}</div>
                <div class="daily-actions">
                  <button class="soft small" data-action="speak" data-text="${escapeAttr(word.word)}">${icon("volume")}朗读</button>
                  <button class="soft small" data-action="open-word" data-word="${escapeAttr(word.word)}">${icon("search")}详情</button>
                  <button class="ghost small" data-action="review-word" data-id="${word.id}">${icon("refresh")}复习</button>
                </div>` : `
                <div class="empty-state" style="padding:18px 0">
                  <p>还没有生词。读文献时划词收藏，这里会出现每日单词。</p>
                  <button class="ghost" data-action="go-vocab">打开生词本</button>
                </div>`}
            </div>
          </section>

          <section class="card desk-card">
            <div class="card-head"><h3>${S.topics.length ? "关注主题" : "快速开始"}</h3><span class="eyebrow">${S.topics.length ? "每日新论文" : "四件事"}</span></div>
            <div class="card-body" ${S.topics.length ? 'id="homeTopics"' : ""}>${S.topics.length ? homeTopicsHtml() : `
              <div class="quick-list">
                <button class="quick-row" data-action="go-discover"><span>${icon("compass")}发现最新文献</span><em>arXiv · OpenAlex</em></button>
                <button class="quick-row" data-action="web-import-modal"><span>${icon("download")}从网页导入文章</span><em>正文提取</em></button>
                <button class="quick-row" data-action="go-cet"><span>${icon("pen")}四六级精读</span><em>词汇分析</em></button>
                <button class="quick-row" data-action="go-vocab"><span>${icon("book")}整理生词本</span><em>FSRS 复习</em></button>
              </div>`}
            </div>
          </section>
        </div>

        <section class="recent-section">
          <div class="section-title"><h2>最近文献</h2><button class="text-link" data-action="go-library">查看全部 ${icon("arrow")}</button></div>
          ${recent.length ? `<div class="recent-grid">${recent.map((doc) => docCard(doc)).join("")}</div>` : `
            <div class="card"><div class="empty-state" style="padding:44px 20px">
              <div class="mark">PDF</div><h2>图书馆还是空的</h2><p>把英文 PDF 拖进窗口，或在图书馆里导入。</p>
              <button class="primary" data-action="upload">导入第一篇 PDF</button>
            </div></div>`}
        </section>

        <section class="card heatmap-card">
          <div class="card-head"><h3>学习热力图</h3><span class="eyebrow">最近 120 天</span></div>
          <div class="card-body">${heatmapHtml(data.heatmap, 120)}</div>
        </section>
      </div>`;
    maybeRefreshTopics();
  } catch (error) {
    view.innerHTML = `<div class="home">${errorHtml(error.message)}</div>`;
  }
}

/* --------------------------------------------------------------- library */
function docCard(doc) {
  const color = doc.cover_color || "#0071e3";
  return `
    <article class="doc-card" data-action="open-doc" data-id="${doc.id}">
      <div class="doc-cover" style="background:${escapeAttr(color)}">
        <img src="/api/documents/${doc.id}/cover?v=${encodeURIComponent(doc.updated_at || "")}" alt="" loading="lazy">
        <span class="doc-badge">${doc.kind === "epub" ? "EPUB" : `${doc.pages} 页`}</span>
        <button class="doc-fav ${doc.favorite ? "on" : ""}" data-action="fav-doc" data-id="${doc.id}" title="收藏">${icon("star")}</button>
      </div>
      <div class="doc-body">
        <div class="doc-title">${escapeHtml(doc.title)}</div>
        <div class="doc-sub">${escapeHtml(doc.authors || "未填写作者")}${doc.year ? ` · ${doc.year}` : ""}</div>
        <div class="doc-foot">
          <div class="progress-track"><div class="progress-fill" style="width:${Math.round((doc.progress || 0) * 100)}%"></div></div>
          <span class="pages">${Math.round((doc.progress || 0) * 100)}%</span>
        </div>
      </div>
    </article>`;
}

async function renderLibrary() {
  topbar({ crumb: "图书馆" });
  const view = $("#libraryView");
  view.innerHTML = `
    <div class="library">
      <div class="page-head">
        <div><h1>图书馆</h1><p id="librarySub">所有文献都在这里</p></div>
        <div class="page-head-actions">
          <button class="ghost" data-action="library-more">${icon("more")}更多</button>
          <button class="primary" data-action="upload">${icon("upload")}导入 PDF</button>
        </div>
      </div>
      <div class="library-toolbar">
        <div class="search-box">${icon("search")}<input id="libSearch" placeholder="搜索标题、作者、标签…" value="${escapeAttr(S.library.q)}"></div>
        <div class="filter-row" id="libFilters">
          <button class="chip ${!S.library.favorite && !S.library.status ? "active" : ""}" data-action="lib-filter" data-filter="all">全部</button>
          <button class="chip ${S.library.favorite ? "active" : ""}" data-action="lib-filter" data-filter="favorite">收藏</button>
          <button class="chip ${S.library.status === "unread" ? "active" : ""}" data-action="lib-filter" data-filter="unread">未读</button>
          <button class="chip ${S.library.status === "reading" ? "active" : ""}" data-action="lib-filter" data-filter="reading">在读</button>
          <button class="chip ${S.library.status === "finished" ? "active" : ""}" data-action="lib-filter" data-filter="finished">读完</button>
        </div>
        <select class="sort-select" id="libSort">
          <option value="recent" ${S.library.sort === "recent" ? "selected" : ""}>最近阅读</option>
          <option value="added" ${S.library.sort === "added" ? "selected" : ""}>最近添加</option>
          <option value="title" ${S.library.sort === "title" ? "selected" : ""}>标题 A-Z</option>
          <option value="year" ${S.library.sort === "year" ? "selected" : ""}>年份</option>
          <option value="pages" ${S.library.sort === "pages" ? "selected" : ""}>页数</option>
        </select>
      </div>
      <div class="library-advanced">
        <input id="libAuthor" placeholder="作者" value="${escapeAttr(S.library.author)}">
        <input id="libVenue" placeholder="期刊 / 会议" value="${escapeAttr(S.library.venue)}">
        <input id="libYearFrom" type="number" placeholder="起始年" value="${escapeAttr(S.library.yearFrom)}">
        <span class="faint">–</span>
        <input id="libYearTo" type="number" placeholder="结束年" value="${escapeAttr(S.library.yearTo)}">
        <button class="ghost small" data-action="lib-reset">重置筛选</button>
      </div>
      <div class="library-meta"><span id="libraryMeta"></span><span>${S.library.collection ? "已按分类筛选" : ""}</span></div>
      <div id="libraryGrid" class="doc-grid"></div>
    </div>`;
  $("#libSearch").addEventListener("input", debounce((event) => {
    S.library.q = event.target.value.trim();
    refreshLibrary();
  }, 260));
  $("#libSort").addEventListener("change", (event) => {
    S.library.sort = event.target.value;
    refreshLibrary();
  });
  $("#libAuthor").addEventListener("input", debounce((event) => { S.library.author = event.target.value.trim(); refreshLibrary(); }, 300));
  $("#libVenue").addEventListener("input", debounce((event) => { S.library.venue = event.target.value.trim(); refreshLibrary(); }, 300));
  $("#libYearFrom").addEventListener("change", (event) => { S.library.yearFrom = event.target.value; refreshLibrary(); });
  $("#libYearTo").addEventListener("change", (event) => { S.library.yearTo = event.target.value; refreshLibrary(); });
  await refreshLibrary();
}

async function refreshLibrary() {
  const params = new URLSearchParams();
  if (S.library.q) params.set("q", S.library.q);
  if (S.library.sort) params.set("sort", S.library.sort);
  if (S.library.collection) params.set("collection_id", S.library.collection);
  if (S.library.favorite) params.set("favorite", "1");
  if (S.library.status) params.set("status", S.library.status);
  if (S.library.author) params.set("author", S.library.author);
  if (S.library.venue) params.set("venue", S.library.venue);
  if (S.library.yearFrom) params.set("year_from", S.library.yearFrom);
  if (S.library.yearTo) params.set("year_to", S.library.yearTo);
  try {
    const docs = await api(`/api/documents?${params.toString()}`);
    S.docs = docs;
    $("#libraryCount").textContent = docs.length ? String(docs.length) : "";
    $("#libraryMeta").textContent = `${docs.length} 篇文献${S.library.q ? ` · 搜索 “${S.library.q}”` : ""}`;
    $("#libraryGrid").innerHTML = docs.length ? docs.map((doc) => docCard(doc)).join("") : `
      <div class="empty-state" style="grid-column:1/-1">
        <div class="mark">PDF</div>
        <h2>${S.library.q ? "没有匹配的文献" : "图书馆还是空的"}</h2>
        <p>${S.library.q ? "换个关键词试试。" : "把英文 PDF 拖进窗口，或点击导入。"}</p>
        <button class="primary" data-action="upload">导入 PDF</button>
      </div>`;
  } catch (error) {
    $("#libraryGrid").innerHTML = errorHtml(error.message);
  }
}

/* --------------------------------------------------------------- discover */
const DISCOVER_SOURCE_LABELS = {
  arxiv: "arXiv", openalex: "OpenAlex", crossref: "Crossref",
  semantic: "Semantic Scholar", pubmed: "PubMed",
};

async function renderDiscover() {
  topbar({ crumb: "发现", right: `<button class="icon" data-action="shortcuts" title="快捷键">?</button>` });
  const view = $("#discoverView");
  view.innerHTML = `
    <div class="page">
      <div class="page-head">
        <div><h1>发现</h1><p>跨来源搜索最新文献，或让 AI 研究员做一轮检索 + 综述。</p></div>
      </div>
      <div id="topicBar" class="topic-bar"></div>
      <section class="card discover-console">
        <div class="discover-search">
          <div class="search-box" style="max-width:none;flex:1">${icon("search")}<input id="discoverQuery" placeholder="例如：remote sensing foundation models / 城市热岛 / 四六级阅读" value="${escapeAttr(S.discover.query)}"></div>
          <button class="primary" data-action="discover-search">${icon("search")}搜索</button>
          <button class="ghost" data-action="agent-run">${icon("compass")}AI 研究员</button>
        </div>
        <div class="discover-options">
          <div class="filter-row" id="discoverSources">
            ${Object.entries(DISCOVER_SOURCE_LABELS).map(([key, label]) => `<button class="chip ${S.discover.sources.includes(key) ? "active" : ""}" data-source="${key}">${label}</button>`).join("")}
          </div>
          <select id="discoverDays" class="sort-select">
            <option value="7" ${S.discover.days === 7 ? "selected" : ""}>最近 7 天</option>
            <option value="30" ${S.discover.days === 30 ? "selected" : ""}>最近 30 天</option>
            <option value="90" ${S.discover.days === 90 ? "selected" : ""}>最近 90 天</option>
            <option value="365" ${S.discover.days === 365 ? "selected" : ""}>最近一年</option>
            <option value="0" ${S.discover.days === 0 ? "selected" : ""}>全部时间</option>
          </select>
          <select id="discoverSort" class="sort-select">
            <option value="recent" ${S.discover.sort === "recent" ? "selected" : ""}>按时间</option>
            <option value="citations" ${S.discover.sort === "citations" ? "selected" : ""}>按引用</option>
          </select>
        </div>
        <div class="quick-topics">
          <span class="faint">快速主题</span>
          ${["遥感基础模型", "地理空间大模型", "多模态遥感", "城市热岛", "Transformer"].map((topic) => `<button class="chip" data-action="discover-topic" data-text="${topic}">${topic}</button>`).join("")}
        </div>
      </section>
      <div id="discoverTrace"></div>
      <div id="discoverResults"></div>
    </div>`;
  $("#discoverQuery").addEventListener("keydown", (event) => {
    if (event.key === "Enter") runDiscoverSearch();
  });
  $$("#discoverSources .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const source = chip.dataset.source;
      S.discover.sources = S.discover.sources.includes(source)
        ? S.discover.sources.filter((item) => item !== source)
        : [...S.discover.sources, source];
      chip.classList.toggle("active");
    });
  });
  $("#discoverDays").addEventListener("change", (event) => { S.discover.days = Number(event.target.value); });
  $("#discoverSort").addEventListener("change", (event) => { S.discover.sort = event.target.value; });
  renderTopicsBar();
  renderDiscoverTrace();
  renderDiscoverResults();
  loadTopics();
}

function homeTopicsHtml() {
  if (!S.topics.length) return "";
  return S.topics.map((topic) => `
    <div class="topic-row">
      <div class="topic-main">
        <b>${escapeHtml(topic.name)}</b>
        <span>${escapeHtml(topic.query)}${topic.new_count ? ` · <em>${topic.new_count} 篇新论文</em>` : ""}</span>
      </div>
      <button class="ghost small" data-action="view-topic" data-id="${topic.id}">查看</button>
      <button class="icon" data-action="refresh-topic" data-id="${topic.id}" title="刷新">${icon("refresh")}</button>
      <button class="icon" data-action="delete-topic" data-id="${topic.id}" title="取消关注">×</button>
    </div>`).join("");
}

function renderHomeTopics() {
  const box = $("#homeTopics");
  if (box) box.innerHTML = homeTopicsHtml();
}

function renderTopicsBar() {
  const box = $("#topicBar");
  if (!box) return;
  if (!S.topics.length) {
    box.innerHTML = `<button class="chip" data-action="add-topic">＋ 关注一个主题，每天自动看新论文</button>`;
    return;
  }
  box.innerHTML = `
    <span class="eyebrow">关注主题</span>
    ${S.topics.map((topic) => `<button class="topic-chip" data-action="view-topic" data-id="${topic.id}">${escapeHtml(topic.name)}${topic.new_count ? `<em>${topic.new_count}</em>` : ""}</button>`).join("")}
    <button class="chip" data-action="add-topic">＋ 关注</button>
    <button class="chip" data-action="refresh-due-topics">刷新今日</button>`;
}

async function loadNotifications() {
  try {
    S.notifications = await api("/api/notifications?limit=40");
    const unread = S.notifications.filter((item) => !item.read).length;
    $("#notifyBadge").textContent = unread ? String(unread) : "";
  } catch { /* optional */ }
}

function openNotificationsModal() {
  const items = S.notifications;
  openModal(`
    <div class="modal-head"><h2>通知</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <div class="row" style="margin-top:0;justify-content:space-between">
      <span class="faint" style="font-size:11px">关注主题有新论文时会出现在这里</span>
      <button class="ghost small" data-action="notifications-read-all">全部已读</button>
    </div>
    <div style="margin-top:8px">
      ${items.length ? items.map((item) => `
        <div class="notify-item ${item.read ? "" : "unread"}" data-action="notification-open" data-id="${item.id}" data-link="${escapeAttr(item.link || "")}">
          <div style="flex:1;min-width:0">
            <div class="notify-title">${escapeHtml(item.title)}</div>
            ${item.body ? `<div class="notify-body">${escapeHtml(item.body)}</div>` : ""}
            <div class="notify-time">${fmtDate(item.created_at)}</div>
          </div>
        </div>`).join("") : '<div class="panel-empty">还没有通知。</div>'}
    </div>`);
}

async function openNotification(id, link) {
  try {
    await api(`/api/notifications/${id}/read`, { method: "POST" });
    await loadNotifications();
    closeModal();
    if (link.startsWith("topic:")) await viewTopic(Number(link.split(":")[1]));
    else if (link.startsWith("doc:")) await openDoc(Number(link.split(":")[1]));
  } catch (error) { toast(error.message, "error"); }
}

async function openAnnualReport() {
  openModal(`<div class="modal-head"><h2>年度报告</h2><button class="icon" data-close-modal>${icon("x")}</button></div><div id="annualReportBody">${loadingHtml("生成年度报告…")}</div>`, { wide: true });
  try {
    const data = await api("/api/report/annual");
    S.annualReport = data.markdown;
    $("#annualReportBody").innerHTML = `<div class="md">${mdToHtml(data.markdown)}</div>
      <div class="modal-actions"><button class="ghost" data-action="download-report">${icon("download")}下载 Markdown</button><button class="ghost" data-action="copy-text" data-text="${escapeAttr(data.markdown)}">${icon("copy")}复制</button></div>`;
  } catch (error) {
    $("#annualReportBody").innerHTML = errorHtml(error.message);
  }
}

function downloadAnnualReport() {
  if (!S.annualReport) return;
  const blob = new Blob([S.annualReport], { type: "text/markdown;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "folio-annual-report.md";
  link.click();
  URL.revokeObjectURL(link.href);
}

async function loadTopics() {
  try {
    S.topics = await api("/api/topics");
    renderTopicsBar();
    if (S.view === "home") renderHomeTopics();
  } catch { /* optional */ }
}

function maybeRefreshTopics() {
  if (!S.topics.length || S.topicsRefreshStarted) return;
  S.topicsRefreshStarted = true;
  api("/api/topics/refresh-due", { method: "POST" })
    .then(() => setTimeout(() => loadTopics(), 9000))
    .catch(() => {});
}

function openTopicModal() {
  openModal(`
    <div class="modal-head"><h2>关注主题</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">给主题起个名字，写英文检索式。每次打开首页会检查超过 20 小时未更新的主题。</p>
    <label>名称<input id="topicName" placeholder="例如：遥感基础模型"></label>
    <label>英文检索式<input id="topicQuery" placeholder="remote sensing foundation model"></label>
    <label>时间范围<select id="topicDays"><option value="7">最近 7 天</option><option value="30" selected>最近 30 天</option><option value="90">最近 90 天</option><option value="365">最近一年</option></select></label>
    <label>来源<div class="filter-row" id="topicSources">
      ${Object.entries(DISCOVER_SOURCE_LABELS).map(([key, label]) => `<button class="chip ${["arxiv", "openalex"].includes(key) ? "active" : ""}" data-topic-source="${key}">${label}</button>`).join("")}
    </div></label>
    <div class="modal-actions"><button class="ghost" data-close-modal>取消</button><button class="primary" data-action="save-topic">关注</button></div>`);
  $$("#topicSources .chip").forEach((chip) => chip.addEventListener("click", () => chip.classList.toggle("active")));
  $("#topicName").focus();
}

async function createTopic() {
  const name = $("#topicName")?.value.trim() || "";
  const query = $("#topicQuery")?.value.trim() || "";
  const sources = $$("#topicSources .chip.active").map((chip) => chip.dataset.topicSource);
  if (!name || !query) { toast("名称和检索式都要填", "error"); return; }
  if (!sources.length) { toast("至少选一个来源", "error"); return; }
  try {
    const result = await api("/api/topics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, query, sources: sources.join(","), days: Number($("#topicDays").value) }),
    });
    closeModal();
    toast("已关注，正在抓取最新论文…");
    await loadTopics();
    refreshTopic(result.id, true);
  } catch (error) { toast(error.message, "error"); }
}

async function viewTopic(topicId, silent = false) {
  try {
    if (S.view !== "discover") await go("discover");
    const data = await api(`/api/topics/${topicId}/items`);
    S.discover.papers = data.papers || [];
    S.discover.agent = null;
    S.discover.loading = false;
    S.discover.errors = [];
    S.discover.query = data.topic.name;
    const input = $("#discoverQuery");
    if (input) input.value = data.topic.name;
    renderDiscoverTrace();
    renderDiscoverResults();
    await api(`/api/topics/${topicId}/seen`, { method: "POST" });
    await loadTopics();
    if (!silent) toast(`已更新「${data.topic.name}」`);
  } catch (error) { toast(error.message, "error"); }
}

async function refreshTopic(topicId, silent = false) {
  if (!silent) toast("正在抓取最新论文…");
  try {
    const result = await api(`/api/topics/${topicId}/refresh`, { method: "POST" });
    await loadTopics();
    if (S.view === "discover") await viewTopic(topicId, true);
    if (!silent) toast(result.new_count ? `新增 ${result.new_count} 篇` : "没有新论文");
  } catch (error) { toast(error.message, "error"); }
}

async function deleteTopic(topicId) {
  if (!confirm("取消关注这个主题？")) return;
  try {
    await api(`/api/topics/${topicId}`, { method: "DELETE" });
    await loadTopics();
    toast("已取消关注");
  } catch (error) { toast(error.message, "error"); }
}

async function refreshDueTopics() {
  try {
    const result = await api("/api/topics/refresh-due", { method: "POST" });
    toast(result.started ? `正在刷新 ${result.started} 个主题…` : "所有主题都是最新的");
    setTimeout(() => loadTopics(), 9000);
  } catch (error) { toast(error.message, "error"); }
}

async function runDiscoverSearch() {
  const query = $("#discoverQuery")?.value.trim() || "";
  if (!query) { toast("先输入一个主题", "error"); return; }
  S.discover.query = query;
  S.discover.loading = true;
  S.discover.mode = "search";
  S.discover.agent = null;
  S.discover.papers = [];
  renderDiscoverTrace();
  renderDiscoverResults();
  const params = new URLSearchParams({
    q: query,
    sources: S.discover.sources.join(","),
    days: String(S.discover.days),
    sort: S.discover.sort,
    limit: "12",
  });
  try {
    const data = await api(`/api/discover/search?${params.toString()}`);
    S.discover.papers = data.papers || [];
    S.discover.errors = data.errors || [];
    S.discover.loading = false;
    renderDiscoverTrace();
    renderDiscoverResults();
  } catch (error) {
    S.discover.loading = false;
    S.discover.errors = [{ source: "搜索", message: error.message }];
    renderDiscoverTrace();
    renderDiscoverResults();
  }
}

async function runAgent() {
  const query = $("#discoverQuery")?.value.trim() || "";
  if (!query) { toast("先输入一个研究主题", "error"); return; }
  S.discover.query = query;
  S.discover.loading = true;
  S.discover.mode = "agent";
  S.discover.agent = null;
  S.discover.papers = [];
  renderDiscoverTrace("<div class=\"agent-card card\">" + loadingHtml("AI 研究员正在规划检索式、抓取论文并写综述…") + "</div>");
  renderDiscoverResults();
  try {
    const data = await api("/api/agent/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        sources: S.discover.sources.join(","),
        days: S.discover.days,
        limit: 12,
      }),
    });
    S.discover.agent = data;
    S.discover.papers = data.papers || [];
    S.discover.errors = data.errors || [];
    S.discover.loading = false;
    renderDiscoverTrace();
    renderDiscoverResults();
  } catch (error) {
    S.discover.loading = false;
    S.discover.errors = [{ source: "AI 研究员", message: error.message }];
    renderDiscoverTrace(errorHtml(error.message));
    renderDiscoverResults();
  }
}

function renderDiscoverTrace(override = "") {
  const box = $("#discoverTrace");
  if (!box) return;
  if (override) { box.innerHTML = override; return; }
  if (S.discover.loading) {
    const label = S.discover.mode === "agent"
      ? "AI 研究员正在规划检索式、抓取论文并写综述…"
      : `正在检索 ${S.discover.sources.map((source) => DISCOVER_SOURCE_LABELS[source]).join(" / ")}…`;
    box.innerHTML = `<div class="agent-card card">${loadingHtml(label)}</div>`;
    return;
  }
  if (!S.discover.agent) { box.innerHTML = ""; return; }
  const agent = S.discover.agent;
  const plan = agent.plan || {};
  box.innerHTML = `
    <section class="agent-card card">
      <div class="card-head"><h3>AI 研究简报</h3><span class="eyebrow">AI 研究简报</span></div>
      <div class="card-body">
        <div class="agent-plan">
          <span class="sum-label">检索计划</span>
          <div class="pill-list">${(plan.queries || []).map((item) => `<div class="pill">${escapeHtml(item)}</div>`).join("")}</div>
          <div class="faint" style="font-size:11px;margin-top:6px">${escapeHtml(plan.focus || "")} · ${(plan.sources || []).join(" / ")} · ${plan.days || S.discover.days} 天</div>
        </div>
        <div class="md agent-md">${mdToHtml(agent.markdown || "")}</div>
      </div>
    </section>`;
}

function renderDiscoverResults() {
  const box = $("#discoverResults");
  if (!box) return;
  if (S.discover.loading) {
    box.innerHTML = `<div class="paper-grid">${Array.from({ length: 4 }, () => '<div class="paper-card card"><div class="skeleton" style="height:14px;width:40%"></div><div class="skeleton" style="height:20px;width:90%;margin-top:10px"></div><div class="skeleton" style="height:60px;margin-top:10px"></div></div>').join("")}</div>`;
    return;
  }
  const errors = (S.discover.errors || []).map((error) => `<div class="discover-warning">${escapeHtml(error.source)} 暂时不可用${error.message ? `：${escapeHtml(error.message)}` : ""}</div>`).join("");
  if (!S.discover.papers.length) {
    box.innerHTML = `${errors}<div class="empty-state" style="padding:50px 20px"><div class="mark">✦</div><h2>搜一下最近的研究</h2><p>选好来源和时间范围，输入主题；或者点「AI 研究员」让它自己规划。</p></div>`;
    return;
  }
  box.innerHTML = `${errors}
    <div class="results-head"><span>${S.discover.papers.length} 篇结果</span><span class="faint">来源：${S.discover.sources.map((source) => DISCOVER_SOURCE_LABELS[source]).join(" / ")}</span></div>
    <div class="paper-grid">${S.discover.papers.map((paper, index) => paperCard(paper, index)).join("")}</div>`;
}

function paperCard(paper, index) {
  const authors = (paper.authors || []).slice(0, 5).join(", ") + ((paper.authors || []).length > 5 ? " 等" : "");
  const importing = S.discover.importing === index;
  return `
    <article class="paper-card card">
      <div class="paper-top">
        <span class="source-badge source-${paper.source.toLowerCase().replace(/\s+/g, "-")}">${escapeHtml(paper.source)}</span>
        <span class="faint">${escapeHtml(paper.year || "")}${paper.venue ? ` · ${escapeHtml(paper.venue)}` : ""}</span>
        <span class="spacer"></span>
        ${paper.citations ? `<span class="faint">${paper.citations} 引用</span>` : ""}
      </div>
      <h3 class="paper-title">${paper.url ? `<a href="${escapeAttr(paper.url)}" target="_blank" rel="noopener">${escapeHtml(paper.title)}</a>` : escapeHtml(paper.title)}</h3>
      <div class="paper-authors">${escapeHtml(authors)}</div>
      <p class="paper-abstract">${escapeHtml(paper.abstract || "（没有摘要）")}</p>
      <div class="paper-actions">
        ${paper.pdf_url ? `<button class="primary small" data-action="import-paper" data-index="${index}" ${importing ? "disabled" : ""}>${icon("download")}${importing ? "导入中…" : "导入 PDF"}</button>` : '<span class="chip">无开放 PDF</span>'}
        ${paper.url ? `<a class="ghost small" href="${escapeAttr(paper.url)}" target="_blank" rel="noopener">${icon("arrow")}原文</a>` : ""}
        <button class="ghost small" data-action="cite-paper" data-index="${index}">${icon("copy")}引用</button>
      </div>
    </article>`;
}

async function importPaper(index) {
  const paper = S.discover.papers[index];
  if (!paper) return;
  S.discover.importing = index;
  renderDiscoverResults();
  try {
    const result = await api("/api/discover/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paper }),
    });
    await Promise.all([loadCollections(), loadVocabCache()]);
    toast("已导入图书馆");
    S.discover.importing = -1;
    await openDoc(result.id);
  } catch (error) {
    S.discover.importing = -1;
    renderDiscoverResults();
    toast(error.message, "error");
  }
}

async function copyPaperCitation(index) {
  const paper = S.discover.papers[index];
  if (!paper) return;
  const first = (paper.authors?.[0] || "folio").split(" ").slice(-1)[0] || "folio";
  const citation = `@article{${first}${paper.year || ""},
  title = {${paper.title}},
  author = {${(paper.authors || []).join(", ")}},
  year = {${paper.year || ""}},
  journal = {${paper.venue || ""}},
  doi = {${paper.doi || ""}}
}`;
  try {
    await navigator.clipboard.writeText(citation);
    toast("BibTeX 已复制");
  } catch {
    openModal(`<div class="modal-head"><h2>引用</h2><button class="icon" data-close-modal>${icon("x")}</button></div><textarea style="width:100%;min-height:180px">${escapeHtml(citation)}</textarea>`);
  }
}

/* ---------------------------------------------------------------- upload */
async function uploadFiles(files) {
  const list = Array.from(files || []).filter((file) => /\.(pdf|epub)$/i.test(file.name));
  if (!list.length) { toast("只支持 PDF / EPUB 文件", "error"); return; }
  let lastId = null;
  for (const file of list) {
    const form = new FormData();
    form.append("file", file);
    toast(`正在解析 ${file.name}…`);
    try {
      const result = await api("/api/documents", { method: "POST", body: form });
      lastId = result.id;
    } catch (error) {
      toast(`${file.name}：${error.message}`, "error");
    }
  }
  await Promise.all([loadCollections(), loadVocabCache()]);
  if (lastId) {
    toast("导入完成");
    await openDoc(lastId);
  } else if (S.view === "library") {
    await refreshLibrary();
  }
}

/* ----------------------------------------------------------------- reader */
async function openDoc(id, page) {
  try {
    const [doc, highlights, notes, chat, outline] = await Promise.all([
      api(`/api/documents/${id}`),
      api(`/api/highlights/${id}`),
      api(`/api/notes/${id}`),
      api(`/api/chat/${id}`),
      api(`/api/documents/${id}/outline`),
    ]);
    S.doc = doc;
    S.highlights = highlights;
    S.notes = notes;
    S.chat = chat;
    S.outline = outline;
    S.summary = doc.summary || null;
    S.page = clamp(page || doc.last_page || 1, 1, Math.max(1, doc.pages));
    S.layout = null;
    S.pageText = "";
    S.bilingual = null;
    S.mode = "page";
    S.searchHits = [];
    S.searchQuery = "";
    S.currentWord = null;
    S.fullTranslation = null;
    S.readingStarted = Date.now();
    S.ocrJob = null;
    S.view = "reader";
    if (S.focusMode) toggleFocusMode(false);
    $$(".nav-link").forEach((button) => button.classList.remove("active"));
    $$(".view").forEach((node) => node.classList.add("hidden"));
    $("#readerView").classList.remove("hidden");
    setPanel(true, "dict");
    S.fitPending = true;
    S.scale = defaultScale();
    renderReaderShell();
    await renderPage();
    history.replaceState(null, "", `#reader/${id}`);
  } catch (error) {
    toast(error.message, "error");
  }
}

function toggleFocusMode(force) {
  const next = typeof force === "boolean" ? force : !S.focusMode;
  if (next === S.focusMode) return;
  S.focusMode = next;
  const app = $("#app");
  app.classList.toggle("focus-mode", next);
  if (next) {
    S.railBeforeFocus = S.railCollapsed;
    S.railCollapsed = true;
  } else {
    S.railCollapsed = !!S.railBeforeFocus;
  }
  $("#readerView")?.classList.toggle("rail-hidden", S.railCollapsed);
  $("#focusBtn")?.classList.toggle("active", next);
}

function renderReaderShell() {
  const doc = S.doc;
  if (!doc) return;
  topbar({
    crumb: doc.title,
    meta: [doc.authors, doc.year, doc.venue].filter(Boolean).join(" · "),
    back: true,
    center: `
      <button id="prevPage" class="icon" title="上一页">‹</button>
      <input id="pageInput" class="page-input" type="number" min="1" value="${S.page}">
      <span class="page-total">/ ${doc.pages}</span>
      <button id="nextPage" class="icon" title="下一页">›</button>
      <span class="divider"></span>
      <button id="zoomOut" class="icon" title="缩小">−</button>
      <span class="zoom-label">${Math.round(S.scale * 100)}%</span>
      <button id="zoomIn" class="icon" title="放大">＋</button>
      <span class="divider"></span>
      <button id="modeBtn" class="soft" title="切换双语对照">${icon("translate")}<span class="btn-label">${S.mode === "page" ? "双语对照" : "原文页面"}</span></button>`,
    right: `
      <button class="icon" id="focusBtn" title="专注阅读 (F)">${icon("focus")}</button>
      <button class="icon" id="railBtn" title="缩略图/目录">${icon("library")}</button>
      <button class="primary" id="summarizeBtn" title="AI 总结">${icon("summary")}<span class="btn-label">AI 总结</span></button>
      <button class="icon" id="panelToggle" title="AI / 词典面板">${icon("chat")}</button>
      <button class="icon" id="moreBtn" title="更多">${icon("more")}</button>`,
  });
  $("#backBtn").onclick = () => go("library");
  $("#prevPage").onclick = () => goPage(S.page - 1);
  $("#nextPage").onclick = () => goPage(S.page + 1);
  $("#pageInput").onchange = (event) => goPage(Number(event.target.value));
  $("#zoomOut").onclick = () => changeZoom(-1);
  $("#zoomIn").onclick = () => changeZoom(1);
  $("#modeBtn").onclick = () => {
    S.mode = S.mode === "page" ? "bilingual" : "page";
    $("#pageWrap").classList.toggle("hidden", S.mode !== "page");
    $("#bilingualPane").classList.toggle("hidden", S.mode !== "bilingual");
    $("#modeBtn").innerHTML = `${icon("translate")}<span class="btn-label">${S.mode === "page" ? "双语对照" : "原文页面"}</span>`;
    if (S.mode === "bilingual") renderBilingual();
    else renderPage();
  };
  $("#railBtn").onclick = () => { S.railCollapsed = !S.railCollapsed; $("#readerView").classList.toggle("rail-hidden", S.railCollapsed); };
  $("#focusBtn").onclick = () => toggleFocusMode();
  $("#summarizeBtn").onclick = () => summarizeDoc();
  $("#panelToggle").onclick = () => setPanel(!S.panelOpen, S.panelTab);
  $("#moreBtn").onclick = openDocMenu;
  $("#readerView").classList.toggle("rail-hidden", S.railCollapsed);
  $("#pageWrap").classList.toggle("hidden", S.mode !== "page");
  $("#bilingualPane").classList.toggle("hidden", S.mode !== "bilingual");
  renderRail();
  renderReaderBanner();
}

function renderReaderBanner() {
  const banner = $("#readerBanner");
  if (!banner || !S.doc) return;
  const job = S.ocrJob;
  if (job && ["queued", "running"].includes(job.status)) {
    const percent = job.total ? Math.round((job.done / job.total) * 100) : 0;
    banner.classList.remove("hidden");
    banner.innerHTML = `<span class="spinner"></span><b>OCR 识别中</b><span>${job.done} / ${job.total} 页</span><div class="progress-track"><div class="progress-fill" style="width:${percent}%"></div></div><span class="spacer"></span><span class="faint">${job.message || ""}</span>`;
    return;
  }
  if (!S.doc.searchable) {
    banner.classList.remove("hidden");
    banner.innerHTML = `<b>扫描版 PDF</b><span>没有文字层，划词 / 搜索 / 翻译暂时不可用。</span><span class="spacer"></span><button class="primary small" data-action="ocr-start">运行 OCR</button>`;
    return;
  }
  banner.classList.add("hidden");
}

async function startOCR() {
  if (!S.doc) return;
  try {
    S.ocrJob = await api(`/api/documents/${S.doc.id}/ocr`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force: false }),
    });
    renderReaderBanner();
    pollOCR();
  } catch (error) {
    toast(error.message, "error");
  }
}

function pollOCR() {
  clearTimeout(S.ocrTimer);
  S.ocrTimer = setTimeout(async () => {
    if (!S.doc) return;
    try {
      const job = await api(`/api/documents/${S.doc.id}/ocr/status`);
      S.ocrJob = job;
      renderReaderBanner();
      if (job.status === "done" || job.status === "error") {
        S.doc = await api(`/api/documents/${S.doc.id}`);
        renderReaderShell();
        await renderPage();
        if (S.panelOpen) renderPanel();
        toast(job.status === "done" ? `OCR 完成：${job.text_pages} 页可读` : `OCR 失败：${job.message}`, job.status === "done" ? "" : "error");
      } else {
        pollOCR();
      }
    } catch (error) {
      toast(error.message, "error");
    }
  }, 1400);
}

function defaultScale() {
  const width = $("#readerStage").clientWidth - 56;
  return clamp(Math.round((width / 612) * 100) / 100, 0.8, 1.6);
}

async function renderPage() {
  if (!S.doc || S.mode !== "page") return;
  if (!S.scale) S.scale = defaultScale();
  renderPage.token = (renderPage.token || 0) + 1;
  const token = renderPage.token;
  const page = S.page;
  const scale = S.scale;
  try {
    const layout = await api(`/api/documents/${S.doc.id}/pages/${page}/layout?scale=${scale}`);
    if (token !== renderPage.token) return;
    const stageWidth = $("#readerStage").clientWidth - 56;
    if (S.fitPending && layout.width > stageWidth) {
      S.fitPending = false;
      S.scale = Math.max(0.8, Math.floor((stageWidth / layout.width) * scale * 100) / 100);
      return renderPage();
    }
    S.fitPending = false;
    S.layout = layout;
    const wrap = $("#pageWrap");
    wrap.style.width = `${layout.width}px`;
    wrap.style.height = `${layout.height}px`;
    $("#pageImg").src = `/api/documents/${S.doc.id}/pages/${page}/image?scale=${scale}&v=${encodeURIComponent(S.doc.updated_at || "")}`;
    buildTextLayer(layout.words);
    renderHighlights();
    renderSearchLayer();
    $("#readerStage").scrollTop = 0;
    $("#pageInput").value = page;
    $(".page-total") && ($(".page-total").textContent = `/ ${S.doc.pages}`);
    S.pageText = "";
    api(`/api/documents/${S.doc.id}/pages/${page}/text`)
      .then((data) => { if (token === renderPage.token) { S.pageText = data.text || ""; updateReaderStatus(); } })
      .catch(() => {});
    updateReaderStatus();
    scheduleProgress();
    document.querySelectorAll(".thumb").forEach((thumb) => thumb.classList.toggle("active", Number(thumb.dataset.page) === page));
  } catch (error) {
    toast(error.message, "error");
  }
}

function buildTextLayer(words) {
  const layer = $("#textLayer");
  layer.innerHTML = "";
  const fragment = document.createDocumentFragment();
  for (const word of words) {
    if (!word.text) continue;
    const span = document.createElement("span");
    span.className = "tw";
    const key = word.text.toLowerCase().replace(/[^a-z'’-]/g, "");
    if (S.vocab.has(key)) span.classList.add("saved");
    span.dataset.word = word.text;
    span.textContent = `${word.text} `;
    span.style.left = `${word.x}px`;
    span.style.top = `${word.y}px`;
    span.style.width = `${Math.max(2, word.w + 4)}px`;
    span.style.height = `${word.h}px`;
    span.style.fontSize = `${Math.max(5, word.h * 0.94)}px`;
    fragment.appendChild(span);
  }
  layer.appendChild(fragment);
}

function renderHighlights() {
  const layer = $("#hlLayer");
  layer.innerHTML = "";
  if (!S.layout) return;
  for (const highlight of S.highlights.filter((item) => item.page === S.page)) {
    for (const rect of highlight.rects || []) {
      const div = document.createElement("div");
      div.className = `hl ${highlight.color || "yellow"}`;
      div.style.left = `${rect.x * 100}%`;
      div.style.top = `${rect.y * 100}%`;
      div.style.width = `${rect.w * 100}%`;
      div.style.height = `${rect.h * 100}%`;
      div.title = highlight.note || highlight.text || "";
      layer.appendChild(div);
    }
  }
}

function renderSearchLayer() {
  const layer = $("#searchLayer");
  layer.innerHTML = "";
  for (const hit of S.searchHits.filter((item) => item.page === S.page)) {
    for (const rect of hit.rects || []) {
      const div = document.createElement("div");
      div.className = "search-hit-rect";
      div.style.left = `${rect.x * 100}%`;
      div.style.top = `${rect.y * 100}%`;
      div.style.width = `${rect.w * 100}%`;
      div.style.height = `${rect.h * 100}%`;
      layer.appendChild(div);
    }
  }
}

function updateReaderStatus() {
  if (!S.doc) return;
  const words = (S.pageText || "").split(/\s+/).filter(Boolean).length;
  const progress = Math.round((S.page / Math.max(1, S.doc.pages)) * 100);
  $("#readerStatus").innerHTML = `
    <span class="dot"></span><span>第 ${S.page} / ${S.doc.pages} 页</span>
    <span>${progress}%</span><span>${words ? `${words} 词` : "无文字层"}</span>
    <span>${fmtDuration(S.doc.reading_seconds || 0)}</span>
    <span class="spacer"></span>
    <span>${S.doc.title}</span>`;
}

function goPage(page) {
  if (!S.doc) return;
  const target = clamp(page, 1, Math.max(1, S.doc.pages));
  if (target === S.page) { renderSearchLayer(); return; }
  flushProgress();
  S.page = target;
  S.layout = null;
  S.bilingual = null;
  if (S.mode === "page") renderPage();
  else renderBilingual();
  document.querySelectorAll(".thumb").forEach((thumb) => thumb.classList.toggle("active", Number(thumb.dataset.page) === target));
}

const ZOOMS = [1.0, 1.2, 1.4, 1.6, 2.0, 2.4];
function changeZoom(direction) {
  if (!S.doc) return;
  let index = ZOOMS.findIndex((zoom) => Math.abs(zoom - S.scale) < 0.01);
  if (index === -1) index = 3;
  S.scale = ZOOMS[clamp(index + direction, 0, ZOOMS.length - 1)];
  S.layout = null;
  renderPage();
}

function scheduleProgress() {
  clearTimeout(S.progressTimer);
  S.progressTimer = setTimeout(() => flushProgress(), 1200);
}

function flushProgress() {
  if (!S.doc) return;
  const seconds = Math.max(0, Math.round((Date.now() - S.readingStarted) / 1000));
  S.readingStarted = Date.now();
  if (seconds < 2) return;
  api(`/api/documents/${S.doc.id}/progress?page=${S.page}&seconds=${seconds}`, { method: "POST" })
    .then(() => { if (S.doc) S.doc.reading_seconds = (S.doc.reading_seconds || 0) + seconds; })
    .catch(() => {});
}

/* ---------------------------------------------------------------- reader rail */
function renderRail() {
  $$(".rail-tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.rail === S.railTab));
  if (S.railTab === "thumbs") renderThumbs();
  else if (S.railTab === "outline") renderOutline();
  else renderSearchRail();
}

function renderThumbs() {
  const pages = S.doc ? S.doc.pages : 0;
  $("#railBody").innerHTML = `<div class="thumb-list">${Array.from({ length: pages }, (_, index) => `
    <div class="thumb ${index + 1 === S.page ? "active" : ""}" data-page="${index + 1}">
      <img loading="lazy" src="/api/documents/${S.doc.id}/pages/${index + 1}/image?scale=0.32&v=${encodeURIComponent(S.doc.updated_at || "")}" alt="">
      <span>${index + 1}</span>
    </div>`).join("")}</div>`;
}

function renderOutline() {
  if (!S.outline.length) {
    $("#railBody").innerHTML = '<div class="panel-empty">这篇 PDF 没有目录。</div>';
    return;
  }
  $("#railBody").innerHTML = `<div class="outline-list">${S.outline.map((item) => `
    <div class="outline-item level-${item.level}" data-page="${item.page}">
      <span>${escapeHtml(item.title)}</span><span class="pg">${item.page}</span>
    </div>`).join("")}</div>`;
}

function renderSearchRail() {
  $("#railBody").innerHTML = `
    <div class="rail-search">
      <input id="railSearchInput" placeholder="搜索全文…" value="${escapeAttr(S.searchQuery)}">
      <div class="search-results" id="searchResults">
        ${S.searchHits.length ? S.searchHits.map((hit) => `
          <div class="search-hit" data-page="${hit.page}">
            <div class="hit-page">第 ${hit.page} 页</div>
            <div class="hit-text">${escapeHtml(hit.snippet)}</div>
          </div>`).join("") : (S.searchQuery ? '<div class="panel-empty">没有结果</div>' : "")}
      </div>
    </div>`;
  const input = $("#railSearchInput");
  input.addEventListener("keydown", (event) => { if (event.key === "Enter") searchInDoc(input.value.trim()); });
}

async function searchInDoc(query) {
  if (!query || !S.doc) return;
  S.searchQuery = query;
  try {
    const data = await api(`/api/documents/${S.doc.id}/search?q=${encodeURIComponent(query)}`);
    S.searchHits = data.hits || [];
    renderSearchRail();
    if (S.searchHits.length) {
      if (S.searchHits[0].page === S.page) renderSearchLayer();
      else goPage(S.searchHits[0].page);
    } else toast("没有找到匹配的内容");
  } catch (error) {
    toast(error.message, "error");
  }
}

/* ------------------------------------------------------------ bilingual */
async function renderBilingual() {
  if (!S.doc || !S.page) return;
  const pane = $("#bilingualPane");
  if (!S.bilingual || S.bilingual.page !== S.page) {
    S.bilingualLoading = true;
    pane.innerHTML = `<div class="bilingual-pane">${loadingHtml("AI 正在逐段翻译这一页…")}</div>`;
    try {
      let data = await api(`/api/translate/page?doc_id=${S.doc.id}&page=${S.page}`).catch(() => null);
      if (!data) {
        data = await api("/api/translate/page", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ doc_id: S.doc.id, page: S.page }),
        });
      }
      S.bilingual = { page: S.page, paragraphs: data.paragraphs || [] };
    } catch (error) {
      S.bilingualLoading = false;
      pane.innerHTML = `<div class="bilingual-pane">${errorHtml(error.message)}</div>`;
      return;
    }
    S.bilingualLoading = false;
  }
  const paragraphs = S.bilingual.paragraphs || [];
  pane.innerHTML = `
    <div class="bilingual-pane">
      <div class="bilingual-head"><span>第 ${S.page} / ${S.doc.pages} 页 · 原文 / 译文</span><button class="ghost small" data-action="retranslate-page">重新翻译</button></div>
      ${paragraphs.map((pair) => `
        <div class="bilingual-row">
          <div class="en">${escapeHtml(pair.en)}</div>
          <div class="zh">${escapeHtml(pair.zh)}</div>
        </div>`).join("") || '<div class="panel-empty">这一页没有可翻译的段落。</div>'}
    </div>`;
}

async function translatePage(force = false) {
  if (!S.doc) return;
  if (S.mode !== "bilingual") {
    S.mode = "bilingual";
    $("#pageWrap").classList.add("hidden");
    $("#bilingualPane").classList.remove("hidden");
    $("#modeBtn").textContent = "原文页面";
  }
  if (force) S.bilingual = null;
  await renderBilingual();
}

/* ---------------------------------------------------------------- panel */
function renderPanel() {
  $$(".panel-tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === S.panelTab));
  const body = $("#panelBody");
  if (!S.doc) { body.innerHTML = '<div class="panel-empty">打开一篇文献后，这里会显示词典、AI、翻译和笔记。</div>'; return; }
  if (S.panelTab === "dict") renderDictPanel();
  else if (S.panelTab === "chat") renderChatPanel();
  else if (S.panelTab === "translate") renderTranslatePanel();
  else if (S.panelTab === "summary") renderSummaryPanel();
  else renderMarksPanel();
  body.scrollTop = 0;
}

function renderDictPanel() {
  const body = $("#panelBody");
  const current = S.currentWord;
  const search = `<div class="search-box" style="max-width:none;margin-bottom:12px">${icon("search")}<input id="panelDictSearch" placeholder="输入单词或短语…" value="${escapeAttr(current?.word || "")}"></div>`;
  if (!current) {
    body.innerHTML = `${search}<div class="panel-empty">划选 PDF 里的单词，或在上方输入查询。<br>词典含音标、词形变化、四六级标签。</div>`;
  } else if (current.loading) {
    body.innerHTML = `${search}${loadingHtml("查词典…")}`;
  } else {
    body.innerHTML = `${search}${dictHtml(current.entry, current.word)}${current.ai ? `<div class="panel-section-title" style="margin-top:20px">AI 扩展</div><div class="md">${mdToHtml(current.ai)}</div>` : ""}`;
  }
  $("#panelDictSearch").addEventListener("keydown", (event) => {
    if (event.key === "Enter") lookupWord(event.target.value.trim(), "", { modal: false });
  });
}

function dictHtml(entry, query) {
  if (!entry || !entry.found) {
    return `
      <div class="dict-head"><div class="dict-word">${escapeHtml(query)}</div></div>
      <div class="panel-empty">ECDICT 没有收录这个词。可以让 AI 结合上下文解释。</div>
      <div class="dict-actions">
        <button class="primary" data-action="ai-word" data-word="${escapeAttr(query)}">AI 解释</button>
        <button class="ghost" data-action="add-vocab" data-word="${escapeAttr(query)}">＋ 生词本</button>
      </div>`;
  }
  const tags = (entry.tag || []).map((tag) => `<span class="tag ${escapeAttr(tag)}">${TAG_LABELS[tag] || tag.toUpperCase()}</span>`).join("");
  const stars = "★".repeat(Math.max(0, Math.min(5, parseInt(entry.collins || "0", 10) || 0)));
  const translations = (entry.translation || "").split("\n").filter(Boolean).map((line) => `<li>${escapeHtml(line)}</li>`).join("");
  const definitions = (entry.definition || "").split("\n").filter(Boolean).slice(0, 8).map((line) => `<li>${escapeHtml(line)}</li>`).join("");
  const forms = (entry.exchange || []).map((item) => `<span>${escapeHtml(item.label)} <b>${escapeHtml(item.word)}</b></span>`).join("");
  return `
    <div class="dict-head">
      <div class="dict-word">${escapeHtml(entry.word)}</div>
      ${entry.phonetic ? `<div class="dict-phonetic">/${escapeHtml(entry.phonetic)}/</div>` : ""}
      <button class="icon" data-action="speak" data-text="${escapeAttr(entry.word)}" title="朗读">${icon("volume")}</button>
    </div>
    <div class="tag-row">${tags}${entry.oxford ? '<span class="tag">牛津3000</span>' : ""}${stars ? `<span class="tag">柯林斯 ${stars}</span>` : ""}</div>
    ${translations ? `<div class="dict-section"><h4>中文释义</h4><ul class="trans-list">${translations}</ul></div>` : ""}
    ${definitions ? `<div class="dict-section"><h4>English definition</h4><ul class="def-list">${definitions}</ul></div>` : ""}
    ${forms ? `<div class="dict-section"><h4>词形变化</h4><div class="exchange">${forms}</div></div>` : ""}
    <div class="dict-actions">
      <button class="primary" data-action="ai-word" data-word="${escapeAttr(entry.word)}">AI 搭配 / 词根 / 例句</button>
      <button class="ghost" data-action="add-vocab" data-word="${escapeAttr(entry.word)}">＋ 生词本</button>
    </div>`;
}

async function lookupWord(word, context = "", options = {}) {
  if (!word) return;
  S.currentWord = { word, context: context || S.selection?.context || "", entry: null, ai: null, loading: true };
  if (options.modal) { openWordModal(word, context, false); return; }
  setPanel(true, "dict");
  renderDictPanel();
  try {
    const entry = await api(`/api/dict/${encodeURIComponent(word)}`);
    S.currentWord.entry = entry;
    S.currentWord.word = entry.word || word;
    S.currentWord.loading = false;
    if (S.panelOpen && S.panelTab === "dict") renderDictPanel();
  } catch (error) {
    S.currentWord.loading = false;
    S.currentWord.entry = { found: false };
    if (S.panelOpen) renderDictPanel();
    toast(error.message, "error");
  }
}

function renderChatPanel() {
  const body = $("#panelBody");
  const messages = S.chat || [];
  body.innerHTML = `
    <div class="chat-wrap">
      <div class="chat-messages" id="chatMessages">
        ${messages.length ? messages.map((message) => chatMessageHtml(message)).join("") : `
          <div class="panel-empty" style="padding:20px 4px 6px">问这篇论文任何问题。AI 只根据检索到的页面回答，并标注页码。</div>
          <div class="chat-suggestions">
            <button class="suggestion" data-action="chat-suggest" data-text="这篇论文的核心贡献是什么？">这篇论文的核心贡献是什么？</button>
            <button class="suggestion" data-action="chat-suggest" data-text="用简单的话解释一下它的方法。">用简单的话解释一下它的方法。</button>
            <button class="suggestion" data-action="chat-suggest" data-text="列出论文里最重要的 5 个术语。">列出最重要的 5 个术语</button>
          </div>`}
        ${S.chatLoading ? `<div class="chat-msg assistant"><div class="chat-role">Folio</div><div class="chat-bubble"><span class="spinner"></span> 正在读论文…</div></div>` : ""}
      </div>
      <div class="chat-input-wrap">
        <div class="chat-input-box">
          <textarea id="chatInput" rows="1" placeholder="问关于这篇论文的问题…"></textarea>
          <button class="chat-send" id="chatSend" title="发送">${icon("arrow")}</button>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:6px">
          <span class="faint" style="font-size:10px">回答会标注 [p.页码]</span>
          <button class="chat-clear" data-action="clear-chat">清空对话</button>
        </div>
      </div>
    </div>`;
  const input = $("#chatInput");
  input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = `${Math.min(110, input.scrollHeight)}px`; });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendChat(input.value); }
  });
  $("#chatSend").onclick = () => sendChat(input.value);
  const box = $("#chatMessages");
  box.scrollTop = box.scrollHeight;
}

function chatMessageHtml(message) {
  const citations = (message.citations || []).map((page) => `<span class="citation" data-page="${page}">p.${page}</span>`).join("");
  return `
    <div class="chat-msg ${message.role}">
      <div class="chat-role">${message.role === "user" ? "你" : "Folio"}</div>
      <div class="chat-bubble">${message.role === "assistant" ? `<div class="md">${mdToHtml(message.content)}</div>` : escapeHtml(message.content)}</div>
      ${citations ? `<div class="chat-citations">${citations}</div>` : ""}
    </div>`;
}

async function sendChat(message) {
  const text = (message || "").trim();
  if (!text || !S.doc || S.chatLoading) return;
  S.chat.push({ role: "user", content: text, citations: [] });
  S.chatLoading = true;
  renderChatPanel();
  try {
    const data = await api("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_id: S.doc.id, message: text, page: S.page }),
    });
    S.chat.push({ role: "assistant", content: data.answer, citations: data.citations || [] });
  } catch (error) {
    S.chat.push({ role: "assistant", content: `⚠️ ${error.message}`, citations: [] });
  } finally {
    S.chatLoading = false;
    if (S.panelOpen && S.panelTab === "chat") renderChatPanel();
  }
}

function renderTranslatePanel() {
  const body = $("#panelBody");
  body.innerHTML = `
    <div class="panel-section-title">逐段翻译</div>
    <p class="faint" style="font-size:11.5px;line-height:1.65;margin:0 0 10px">保留原文与译文的段落对照，译文会缓存，不重复消耗 token。</p>
    <div class="dict-actions" style="margin-top:0">
      <button class="primary" data-action="translate-page">${icon("translate")}翻译本页</button>
      <button class="ghost" data-action="translate-all">翻译全文</button>
      ${S.bilingual ? '<button class="ghost" data-action="retranslate-page">重新翻译本页</button>' : ""}
    </div>
    ${S.bilingual ? `<div class="panel-section-title" style="margin-top:18px">第 ${S.page} 页对照</div>
      ${S.bilingual.paragraphs.map((pair) => `<div class="sum-card"><div class="sum-label">原文</div><div class="sum-value" style="font-family:var(--serif)">${escapeHtml(pair.en)}</div><div class="sum-label" style="margin-top:8px">译文</div><div class="sum-value muted">${escapeHtml(pair.zh)}</div></div>`).join("")}` : ""}
    ${S.fullTranslation ? `<div class="panel-section-title" style="margin-top:18px">全文译文</div><div class="md">${mdToHtml(S.fullTranslation)}</div>` : ""}`;
}

function renderSummaryPanel() {
  const body = $("#panelBody");
  if (!S.summary) {
    body.innerHTML = `
      <div class="panel-empty" style="padding:30px 8px 18px">让 AI 通读全文，提取 TL;DR、研究问题、方法、数据、结果、贡献、局限、关键术语和核心 idea。</div>
      <div class="dict-actions" style="justify-content:center">
        <button class="primary" data-action="summarize">${icon("summary")}生成结构化摘要</button>
      </div>`;
    return;
  }
  const summary = S.summary;
  const list = (items) => (Array.isArray(items) && items.length)
    ? `<div class="pill-list">${items.map((item) => `<div class="pill">${escapeHtml(item)}</div>`).join("")}</div>`
    : '<div class="muted">—</div>';
  const terms = (Array.isArray(summary.key_terms) ? summary.key_terms : []).map((item) => {
    const term = typeof item === "string" ? { term: item, meaning: "" } : (item || {});
    return `<div class="term-row"><b>${escapeHtml(term.term || "")}</b><span>${escapeHtml(term.meaning || "")}</span><span class="spacer"></span><button class="icon" data-action="add-vocab" data-word="${escapeAttr(term.term || "")}" title="加入生词本">＋</button></div>`;
  }).join("");
  body.innerHTML = `
    <div class="sum-card"><div class="sum-label">TL;DR</div><div class="sum-value">${escapeHtml(summary.tldr || "—")}</div></div>
    <div class="sum-grid">
      <div class="sum-card"><div class="sum-label">研究问题</div><div class="sum-value">${escapeHtml(summary.problem || "—")}</div></div>
      <div class="sum-card"><div class="sum-label">方法</div><div class="sum-value">${escapeHtml(summary.method || "—")}</div></div>
      <div class="sum-card"><div class="sum-label">数据 / 实验</div><div class="sum-value">${escapeHtml(summary.data || "—")}</div></div>
      <div class="sum-card"><div class="sum-label">主要结果</div><div class="sum-value">${escapeHtml(summary.results || "—")}</div></div>
    </div>
    <div class="sum-card"><div class="sum-label">贡献</div>${list(summary.contributions)}</div>
    <div class="sum-card"><div class="sum-label">核心 idea</div>${list(summary.ideas)}</div>
    <div class="sum-card"><div class="sum-label">局限</div>${list(summary.limitations)}</div>
    <div class="sum-card"><div class="sum-label">关键术语</div>${terms || '<div class="muted">—</div>'}</div>
    <div class="dict-actions">
      <button class="primary" data-action="keypoints">${icon("highlight")}本页自动划重点</button>
      <button class="ghost" data-action="summarize">重新生成</button>
    </div>`;
}

function renderMarksPanel() {
  const body = $("#panelBody");
  const highlights = S.highlights.filter((item) => !S.markFilter || item.color === S.markFilter);
  body.innerHTML = `
    <div class="panel-section-title">第 ${S.page} 页新笔记</div>
    <input id="noteTitleInput" placeholder="标题（可选）" style="width:100%;margin-bottom:7px">
    <textarea id="noteContentInput" placeholder="写下这一页的想法…" style="width:100%;min-height:80px"></textarea>
    <div class="dict-actions" style="margin-top:8px"><button class="primary" data-action="add-note">保存笔记</button></div>
    <div class="panel-section-title" style="margin-top:18px">全部笔记<span>${S.notes.length}</span></div>
    ${S.notes.length ? S.notes.map((note) => `
      <div class="note-card">
        <div class="note-title"><span>${escapeHtml(note.title || `第 ${note.page} 页`)}</span><span class="faint" style="font-size:9.5px">P${note.page}</span></div>
        <div class="note-body">${escapeHtml(note.content)}</div>
        <div class="note-actions">
          <button data-action="goto-page" data-page="${note.page}">跳转</button>
          <button data-action="edit-note" data-id="${note.id}">编辑</button>
          <button data-action="delete-note" data-id="${note.id}">删除</button>
        </div>
      </div>`).join("") : '<div class="panel-empty">还没有笔记。</div>'}
    <div class="panel-section-title" style="margin-top:18px">高亮<span>${highlights.length}</span></div>
    <div class="color-filter">
      ${["yellow", "green", "blue", "pink", "purple"].map((color) => `<button class="color-dot ${color} ${S.markFilter === color ? "active" : ""}" data-action="filter-marks" data-color="${color}" title="筛选"></button>`).join("")}
      ${S.markFilter ? '<button class="chip" data-action="filter-marks" data-color="">清除筛选</button>' : ""}
    </div>
    ${highlights.length ? highlights.map((item) => `
      <div class="mark-row" data-action="goto-page" data-page="${item.page}">
        <span class="mark-dot" style="background:${markColor(item.color)}"></span>
        <span class="mark-text">${escapeHtml(item.text || item.note || "")}${item.note ? `<br><span class="faint">${escapeHtml(item.note)}</span>` : ""}</span>
        <span class="mark-page">P${item.page}</span>
        <button class="icon" data-action="mark-note" data-id="${item.id}" title="备注">${icon("pen")}</button>
        <button class="icon" data-action="delete-highlight" data-id="${item.id}" title="删除">×</button>
      </div>`).join("") : '<div class="panel-empty">选中文字后点高亮颜色，标注会出现在这里。</div>'}
  `;
}

function openMarkNoteModal(id) {
  const item = S.highlights.find((entry) => entry.id === id);
  if (!item) return;
  openModal(`
    <div class="modal-head"><h2>标注备注</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <div class="sum-card"><div class="sum-label">原文</div><div class="sum-value">${escapeHtml(item.text || "")}</div></div>
    <label>备注<textarea id="markNoteInput" style="min-height:120px">${escapeHtml(item.note || "")}</textarea></label>
    <div class="modal-actions"><button class="ghost" data-close-modal>取消</button><button class="primary" data-action="save-mark-note" data-id="${id}">保存</button></div>`);
}

async function saveMarkNote(id) {
  const note = $("#markNoteInput")?.value.trim() || "";
  try {
    const updated = await api(`/api/highlights/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note }),
    });
    const index = S.highlights.findIndex((item) => item.id === id);
    if (index >= 0) S.highlights[index] = updated;
    closeModal();
    renderMarksPanel();
    toast("备注已保存");
  } catch (error) { toast(error.message, "error"); }
}
function markColor(color) { return { yellow: "#ffd60a", green: "#34c759", blue: "#64d2ff", pink: "#ff9fce", purple: "#bf9cff" }[color] || "#ffd60a"; }

/* ------------------------------------------------------------- selection */
function hidePopup() {
  const popup = $("#selectionPopup");
  popup.classList.add("hidden");
  popup.classList.remove("lookup");
  S.selectionToken = (S.selectionToken || 0) + 1;
}

function selectionRects() {
  const wrap = $("#pageWrap");
  const box = wrap.getBoundingClientRect();
  if (!box.width || !box.height) return [];
  const selection = window.getSelection();
  if (!selection || !selection.rangeCount) return [];
  const rects = [];
  for (const rect of selection.getRangeAt(0).getClientRects()) {
    if (rect.width < 1 || rect.height < 1) continue;
    const x = (rect.left - box.left) / box.width;
    const y = (rect.top - box.top) / box.height;
    const w = rect.width / box.width;
    const h = rect.height / box.height;
    if (x + w < 0 || y + h < 0 || x > 1 || y > 1) continue;
    rects.push({ x: Math.max(0, x), y: Math.max(0, y), w: Math.min(1 - Math.max(0, x), w), h: Math.min(1 - Math.max(0, y), h) });
  }
  return rects;
}

function getContext(text) {
  const pageText = S.pageText || "";
  const index = pageText.indexOf(text);
  if (index >= 0) return pageText.slice(Math.max(0, index - 500), index + text.length + 500).replace(/\s+/g, " ").trim();
  return pageText.slice(0, 1200).replace(/\s+/g, " ").trim();
}

function looksLikeQuestion(text) {
  if (!text || text.length > 2500) return false;
  if (/\?/.test(text)) return true;
  const options = (text.match(/(?:^|\s)[A-D][.、)]/g) || []).length;
  if (options >= 2) return true;
  if (/(^|\s)\d+[.、)]/.test(text) && /[A-D][.、)]/.test(text)) return true;
  if (/[（(][A-D][）)]/.test(text)) return true;
  return false;
}

function captureSelection() {
  if (S.view !== "reader" || !S.doc || S.mode !== "page") return;
  const selection = window.getSelection();
  if (!selection || !selection.rangeCount || selection.isCollapsed) { hidePopup(); return; }
  const text = selection.toString().replace(/\s+/g, " ").trim();
  if (!text) { hidePopup(); return; }
  const rects = selectionRects();
  if (!rects.length) { hidePopup(); return; }
  const core = text.replace(/^[^A-Za-z]+|[^A-Za-z'’-]+$/g, "");
  const isWord = /^[A-Za-z][A-Za-z'’-]*$/.test(core) && core.length <= 40;
  const words = text.split(/\s+/).filter(Boolean);
  const isPhrase = !isWord && words.length >= 2 && words.length <= 5 && text.length <= 60
    && /^[A-Za-z][A-Za-z'’\-\s]*$/.test(text);
  const lookup = isWord ? core : (isPhrase ? text.replace(/[^A-Za-z'’\-\s]/g, " ").replace(/\s+/g, " ").trim() : "");
  const rangeRect = selection.getRangeAt(0).getBoundingClientRect();
  const token = (S.selectionToken || 0) + 1;
  S.selectionToken = token;
  S.selection = {
    text, rects, isWord, isPhrase, canLookup: Boolean(lookup), lookup,
    isQuestion: looksLikeQuestion(text), word: core,
    context: getContext(text), x: rangeRect.left, y: rangeRect.bottom, token,
  };
  showPopup();
}

function positionPopup() {
  const popup = $("#selectionPopup");
  const selection = S.selection;
  if (!popup || !selection) return;
  const width = popup.offsetWidth;
  const height = popup.offsetHeight;
  popup.style.left = `${Math.max(8, Math.min(selection.x, window.innerWidth - width - 12))}px`;
  popup.style.top = `${Math.max(8, Math.min(selection.y + 8, window.innerHeight - height - 12))}px`;
}

function lookupColorsHtml() {
  return ["yellow", "green", "blue", "pink", "purple"].map((color) => `<button class="dot ${color}" data-action="hl" data-color="${color}" title="高亮"></button>`).join("");
}

function lookupCardHtml(entry, selection) {
  const colors = lookupColorsHtml();
  if (!entry.found) {
    return `<div class="lookup-card">
      <div class="lookup-head"><span class="lookup-word">${escapeHtml(selection.lookup)}</span>
        <button class="icon" data-action="speak" data-text="${escapeAttr(selection.lookup)}" title="朗读">${icon("volume")}</button></div>
      <div class="lookup-missing">词典没有收录这个词条，可以让 AI 解释。</div>
      <div class="lookup-actions">
        <button class="soft small" data-action="ai-selection-word">AI 详解</button>
        <button class="soft small" data-action="explain-selection">英文解释</button>
        <button class="ghost small" data-action="translate-selection">翻译</button>
      </div>
      <div class="lookup-colors">${colors}</div>
    </div>`;
  }
  const translation = String(entry.translation || "").split("\n").slice(0, 3).join("\n");
  return `<div class="lookup-card">
    <div class="lookup-head"><span class="lookup-word">${escapeHtml(entry.word || selection.lookup)}</span>
      <button class="icon" data-action="speak" data-text="${escapeAttr(entry.word || selection.lookup)}" title="朗读">${icon("volume")}</button></div>
    ${entry.phonetic ? `<div class="lookup-phonetic">/${escapeHtml(entry.phonetic)}/</div>` : ""}
    <div class="lookup-meaning">${escapeHtml(translation || "（没有中文释义）")}</div>
    <div class="lookup-actions">
      <button class="soft small" data-action="ai-selection-word">AI 详解</button>
      <button class="soft small" data-action="add-selection-vocab">＋生词本</button>
      <button class="ghost small" data-action="lookup-selection">完整词典</button>
    </div>
    <div class="lookup-colors">${colors}</div>
  </div>`;
}

async function renderLookupPopup(selection) {
  const popup = $("#selectionPopup");
  popup.classList.remove("hidden");
  popup.classList.add("lookup");
  popup.innerHTML = `<div class="lookup-card">${loadingHtml("查词典…")}</div>`;
  positionPopup();
  try {
    const entry = await api(`/api/dict/${encodeURIComponent(selection.lookup)}`);
    if (selection.token !== S.selectionToken || S.selection !== selection) return;
    popup.innerHTML = lookupCardHtml(entry, selection);
    positionPopup();
  } catch (error) {
    if (selection.token !== S.selectionToken || S.selection !== selection) return;
    popup.innerHTML = `<div class="lookup-card"><div class="lookup-missing">${escapeHtml(error.message)}</div></div>`;
    positionPopup();
  }
}

function showPopup() {
  const selection = S.selection;
  if (!selection) return;
  const popup = $("#selectionPopup");
  if (selection.canLookup && S.settings?.auto_lookup !== false) {
    renderLookupPopup(selection);
    return;
  }
  popup.classList.remove("lookup");
  const colors = lookupColorsHtml();
  const solve = selection.isQuestion ? `<button data-action="solve-question">解题</button>` : "";
  if (selection.isWord || selection.isPhrase) {
    popup.innerHTML = `
      <button data-action="lookup-selection">查词</button>
      <button data-action="ai-selection-word">AI 详解</button>
      <button data-action="add-selection-vocab">＋生词本</button>
      <button data-action="speak" data-text="${escapeAttr(selection.lookup || selection.text)}">${icon("volume")}</button>
      ${solve}
      <span class="pop-sep"></span>${colors}`;
  } else {
    popup.innerHTML = `
      <button data-action="translate-selection">翻译</button>
      <button data-action="explain-selection">英文解释</button>
      <button data-action="simplify-selection">简化</button>
      <button data-action="grammar-selection">语法</button>
      ${solve}
      <button data-action="ask-selection">问 AI</button>
      <button data-action="speak" data-text="${escapeAttr(selection.text)}">${icon("volume")}</button>
      <span class="pop-sep"></span>${colors}`;
  }
  popup.classList.remove("hidden");
  positionPopup();
}

/* --------------------------------------------------------------- word modal */
function modalHtml(content, options = {}) {
  return `
    <div class="modal-backdrop" data-modal-backdrop>
      <div class="modal-card ${options.wide ? "wide" : ""}" role="dialog" aria-modal="true">
        ${content}
      </div>
    </div>`;
}

function openModal(content, options = {}) {
  const root = $("#modalRoot");
  root.innerHTML = modalHtml(content, options);
  root.querySelector("[data-modal-backdrop]").addEventListener("mousedown", (event) => {
    if (!options.sticky && event.target === event.currentTarget) closeModal();
  });
  root.querySelectorAll("[data-close-modal]").forEach((button) => button.addEventListener("click", closeModal));
  return root.firstElementChild;
}

function closeModal() { $("#modalRoot").innerHTML = ""; }

async function openWordModal(word, context = "", autoAI = false) {
  if (!word) return;
  const root = openModal(`
    <div class="modal-head"><h2>词典</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <div id="wordModalBody">${loadingHtml("查词典…")}</div>`);
  try {
    const entry = await api(`/api/dict/${encodeURIComponent(word)}`);
    S.currentWord = { word: entry.word || word, context, entry, ai: null, loading: false };
    renderWordModalBody(entry, word, context, autoAI);
  } catch (error) {
    $("#wordModalBody").innerHTML = errorHtml(error.message);
  }
}

function renderWordModalBody(entry, word, context, autoAI) {
  const body = $("#wordModalBody");
  const head = `
    <div class="word-modal-word">${escapeHtml(entry.word || word)}</div>
    <div class="word-modal-phonetic">/${escapeHtml(entry.phonetic || "")}/</div>
    <div class="tag-row">${(entry.tag || []).map((tag) => `<span class="tag ${tag}">${TAG_LABELS[tag] || tag}</span>`).join("")}</div>
    <div class="word-modal-actions">
      <button class="primary" data-action="add-vocab" data-word="${escapeAttr(entry.word || word)}">＋ 生词本</button>
      <button class="ghost" data-action="speak" data-text="${escapeAttr(entry.word || word)}">${icon("volume")}朗读</button>
      <button class="ghost" data-action="ai-word" data-word="${escapeAttr(entry.word || word)}">AI 搭配 / 词根</button>
    </div>
    ${context ? `<div class="sum-card" style="margin-top:12px"><div class="sum-label">上下文</div><div class="sum-value muted">${escapeHtml(context.slice(0, 500))}</div></div>` : ""}`;
  if (!entry.found) {
    body.innerHTML = `${head}<div class="panel-empty">ECDICT 没有收录这个词。可以让 AI 结合上下文解释。</div><div id="wordModalAI"></div>`;
  } else {
    const translations = (entry.translation || "").split("\n").filter(Boolean).map((line) => `<li>${escapeHtml(line)}</li>`).join("");
    const definitions = (entry.definition || "").split("\n").filter(Boolean).slice(0, 8).map((line) => `<li>${escapeHtml(line)}</li>`).join("");
    const forms = (entry.exchange || []).map((item) => `<span>${escapeHtml(item.label)} <b>${escapeHtml(item.word)}</b></span>`).join("");
    body.innerHTML = `${head}
      ${translations ? `<div class="dict-section"><h4>中文释义</h4><ul class="trans-list">${translations}</ul></div>` : ""}
      ${definitions ? `<div class="dict-section"><h4>English definition</h4><ul class="def-list">${definitions}</ul></div>` : ""}
      ${forms ? `<div class="dict-section"><h4>词形变化</h4><div class="exchange">${forms}</div></div>` : ""}
      <div id="wordModalAI"></div>`;
  }
  if (autoAI) aiWord(word, context, true);
}

async function aiWord(word, context = "", modal = false) {
  if (!word) return;
  const target = modal ? $("#wordModalAI") : null;
  if (target) target.innerHTML = loadingHtml("AI 正在解释搭配和词根…");
  else { setPanel(true, "dict"); if (S.currentWord) S.currentWord.ai = null; }
  try {
    const data = await api("/api/ai/word", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ word, context: context || S.currentWord?.context || "" }),
    });
    if (target) target.innerHTML = `<div class="dict-section"><h4>AI 扩展</h4><div class="md">${mdToHtml(data.markdown)}</div></div>`;
    else {
      if (!S.currentWord) S.currentWord = { word, context, entry: null, loading: false };
      S.currentWord.ai = data.markdown;
      renderDictPanel();
    }
  } catch (error) {
    if (target) target.innerHTML = errorHtml(error.message);
    else toast(error.message, "error");
  }
}

async function openSelectionModal(text, mode) {
  const labels = { translate: "翻译", explain_en: "英文解释", simplify: "简化改写", grammar: "语法拆解" };
  openModal(`
    <div class="modal-head"><h2>${labels[mode] || "AI 解释"}</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <div class="sum-card"><div class="sum-label">原文</div><div class="sum-value" style="font-family:var(--serif)">${escapeHtml(text)}</div></div>
    <div id="selectionModalBody">${loadingHtml("AI 正在分析…")}</div>`);
  try {
    const data = await api("/api/ai/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, context: S.pageText.slice(0, 1200), mode }),
    });
    $("#selectionModalBody").innerHTML = `<div class="md">${mdToHtml(data.markdown)}</div>
      <div class="modal-actions"><button class="ghost" data-action="copy-text" data-text="${escapeAttr(data.markdown)}">${icon("copy")}复制</button><button class="ghost" data-action="save-selection-note" data-text="${escapeAttr(data.markdown)}">加入笔记</button></div>`;
  } catch (error) {
    $("#selectionModalBody").innerHTML = errorHtml(error.message);
  }
}

async function openSolveQuestionModal(text, context = "") {
  const question = String(text || "").trim();
  if (question.length < 8) { toast("先选中题干和选项", "error"); return; }
  const readerDoc = S.view === "reader" && S.doc ? S.doc : null;
  S.lastSolve = "";
  openModal(`
    <div class="modal-head"><h2>题目解析</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <div class="sum-card"><div class="sum-label">题目</div><div class="sum-value" style="max-height:180px;overflow:auto;white-space:pre-wrap">${escapeHtml(question.slice(0, 3000))}</div></div>
    <div id="solveModalBody">${loadingHtml("AI 正在解题…")}</div>`, { wide: true });
  try {
    const data = await api("/api/ai/solve-question", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: question,
        context: (context || S.pageText || "").slice(0, 2200),
        doc_id: readerDoc?.id || null,
        page: readerDoc ? S.page : null,
      }),
    });
    S.lastSolve = data.markdown;
    S.lastSolveQuestion = question;
    $("#solveModalBody").innerHTML = `<div class="md">${mdToHtml(data.markdown)}</div>
      <div class="modal-actions">
        <button class="ghost" data-action="copy-text" data-text="${escapeAttr(data.markdown)}">${icon("copy")}复制</button>
        <button class="ghost" data-action="mistake-from-solve">${icon("target")}加入错题本</button>
        ${readerDoc ? `<button class="ghost" data-action="save-selection-note" data-text="${escapeAttr(data.markdown)}" data-title="题目解析">${icon("note")}保存为笔记</button>` : ""}
        <button class="primary" data-action="close-modal">关闭</button>
      </div>`;
  } catch (error) {
    $("#solveModalBody").innerHTML = errorHtml(error.message);
  }
}

function openQuestionSolverModal() {
  openModal(`
    <div class="modal-head"><h2>题目解析</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">把题干和 A–D 选项贴进来。有答案键可以一起贴；没有的话 AI 会尝试作答，并标出不确定的地方。</p>
    <label>题目<textarea id="solveQuestionText" style="min-height:160px" placeholder="例：
1. What is the main idea of the passage?
A. ...
B. ...
C. ...
D. ..."></textarea></label>
    <div class="modal-actions"><button class="ghost" data-close-modal>取消</button><button class="primary" data-action="solve-question-text">${icon("play")}开始解析</button></div>`);
}

/* -------------------------------------------------------------- highlights */
async function addHighlight(color = "yellow") {
  if (!S.doc || !S.selection) return;
  try {
    const item = await api("/api/highlights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        doc_id: S.doc.id,
        page: S.page,
        color,
        text: S.selection.text.slice(0, 2000),
        rects: S.selection.rects,
      }),
    });
    S.highlights.push(item);
    renderHighlights();
    if (S.panelOpen && S.panelTab === "marks") renderMarksPanel();
    toast("已高亮");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function addVocab(word, context = "") {
  const clean = (word || "").trim();
  if (!clean) return;
  try {
    const item = await api("/api/vocab", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        word: clean,
        context: context || S.selection?.context || "",
        doc_id: S.view === "reader" && S.doc ? S.doc.id : null,
        page: S.view === "reader" && S.doc ? S.page : null,
      }),
    });
    S.vocab.set(item.word.toLowerCase(), item);
    if (!S.vocabList.some((entry) => entry.id === item.id)) S.vocabList.push(item);
    updateBadges();
    if (S.layout) buildTextLayer(S.layout.words);
    toast(`已加入生词本：${item.word}`);
  } catch (error) {
    toast(error.message, "error");
  }
}

function speak(text) {
  if (!text || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = 0.92;
  window.speechSynthesis.speak(utterance);
}

/* --------------------------------------------------------- summary & keypoints */
async function summarizeDoc() {
  if (!S.doc) return;
  setPanel(true, "summary");
  $("#panelBody").innerHTML = loadingHtml("AI 正在通读全文并提取核心内容…");
  try {
    const data = await api("/api/ai/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_id: S.doc.id, scope: "doc" }),
    });
    S.summary = data.summary;
    S.doc.summary = data.summary;
    renderSummaryPanel();
  } catch (error) {
    $("#panelBody").innerHTML = errorHtml(error.message);
  }
}

async function autoKeypoints() {
  if (!S.doc) return;
  try {
    const data = await api("/api/ai/keypoints", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_id: S.doc.id, page: S.page, count: 5 }),
    });
    let added = 0;
    for (const point of data.points || []) {
      const rects = findQuoteRects(point.quote);
      if (!rects.length) continue;
      const item = await api("/api/highlights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          doc_id: S.doc.id,
          page: S.page,
          color: "blue",
          text: point.quote,
          rects,
          note: point.reason || "",
          type: "ai-keypoint",
        }),
      });
      S.highlights.push(item);
      added += 1;
    }
    renderHighlights();
    if (S.panelOpen) renderMarksPanel();
    toast(added ? `已在第 ${S.page} 页标出 ${added} 处重点` : "AI 返回的句子没有在页面中匹配到", added ? "" : "error");
  } catch (error) {
    toast(error.message, "error");
  }
}

function findQuoteRects(quote) {
  if (!quote) return [];
  const spans = $$("#textLayer .tw");
  const items = spans.map((span) => ({ el: span, text: span.dataset.word || span.textContent.trim() }));
  const normalize = (value) => value.toLowerCase().replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
  const target = normalize(quote);
  const box = $("#pageWrap").getBoundingClientRect();
  for (let start = 0; start < items.length; start += 1) {
    let text = "";
    let used = [];
    for (let index = start; index < items.length; index += 1) {
      text += `${items[index].text} `;
      used.push(items[index].el);
      const normalized = normalize(text);
      if (normalized.length >= target.length) {
        if (normalized.startsWith(target) || normalized === target) {
          const rects = [];
          for (const element of used) {
            const rect = element.getBoundingClientRect();
            if (!rect.width || !rect.height) continue;
            rects.push({
              x: (rect.left - box.left) / box.width,
              y: (rect.top - box.top) / box.height,
              w: rect.width / box.width,
              h: rect.height / box.height,
            });
          }
          return rects;
        }
        break;
      }
    }
  }
  return [];
}

/* ----------------------------------------------------------------- notes */
async function addNote() {
  if (!S.doc) return;
  const title = $("#noteTitleInput")?.value.trim() || "";
  const content = $("#noteContentInput")?.value.trim() || "";
  if (!content) { toast("笔记不能为空", "error"); return; }
  try {
    await api("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_id: S.doc.id, page: S.page, content, title }),
    });
    S.notes = await api(`/api/notes/${S.doc.id}`);
    renderMarksPanel();
    toast("笔记已保存");
  } catch (error) {
    toast(error.message, "error");
  }
}

function editNoteModal(id) {
  const note = S.notes.find((item) => item.id === id);
  if (!note) return;
  openModal(`
    <div class="modal-head"><h2>编辑笔记</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <label>标题<input id="editNoteTitle" value="${escapeAttr(note.title || "")}"></label>
    <label>内容<textarea id="editNoteContent" style="min-height:160px">${escapeHtml(note.content)}</textarea></label>
    <div class="modal-actions"><button class="ghost" data-close-modal>取消</button><button class="primary" data-action="save-note-edit" data-id="${id}">保存</button></div>`);
}

async function saveNoteEdit(id) {
  const title = $("#editNoteTitle")?.value.trim() || "";
  const content = $("#editNoteContent")?.value.trim() || "";
  if (!content) return;
  try {
    await api(`/api/notes/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, content }),
    });
    S.notes = await api(`/api/notes/${S.doc.id}`);
    closeModal();
    renderMarksPanel();
    toast("已更新");
  } catch (error) {
    toast(error.message, "error");
  }
}

/* ---------------------------------------------------------------- library actions */
async function toggleFavorite(id) {
  const doc = S.docs.find((item) => item.id === id) || (S.doc && S.doc.id === id ? S.doc : null);
  if (!doc) return;
  try {
    const updated = await api(`/api/documents/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ favorite: doc.favorite ? 0 : 1 }),
    });
    doc.favorite = updated.favorite;
    if (S.doc && S.doc.id === id) S.doc.favorite = updated.favorite;
    if (S.view === "library") await refreshLibrary();
    if (S.view === "home") await renderHome();
    toast(updated.favorite ? "已收藏" : "已取消收藏");
  } catch (error) { toast(error.message, "error"); }
}

function openDocMenu() {
  if (!S.doc) return;
  const isEpub = S.doc.kind === "epub" || /\.epub$/i.test(S.doc.path || "");
  openModal(`
    <div class="modal-head"><h2>文献操作</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <div class="sum-card"><div class="sum-label">当前文献</div><div class="sum-value">${escapeHtml(S.doc.title)}</div><div class="faint" style="font-size:11px;margin-top:4px">${escapeHtml(S.doc.authors || "未填写作者")}${S.doc.year ? ` · ${S.doc.year}` : ""}</div></div>
    <div class="dict-actions" style="margin-top:8px">
      <button class="primary" data-action="edit-doc">${icon("pen")}编辑信息</button>
      ${isEpub ? `<button class="ghost" data-action="epub-layout">${icon("book")}EPUB 排版</button>` : ""}
      <button class="ghost" data-action="enrich-doc">${icon("refresh")}补全元数据</button>
      <button class="ghost" data-action="research-tools">${icon("compass")}研究工具</button>
      <button class="ghost" data-action="doc-export-menu">${icon("download")}导出 / 引用</button>
      <button class="danger" data-action="delete-doc">${icon("trash")}删除文献</button>
    </div>
    <div class="hint" style="margin-top:14px">${isEpub ? "EPUB 已重排为适合屏幕的 PDF；调整字号会重新分页。" : "补全元数据会先尝试 arXiv，再尝试 Crossref；需要联网。"}</div>`);
}

function openResearchTools() {
  const tools = [
    ["reading_card", "速读卡", "研究问题、方法、结果、新意、局限"],
    ["method", "方法拆解", "输入、模块、训练、指标、失败模式"],
    ["reviewer", "审稿人视角", "优点、问题、需要补的实验"],
    ["related_work", "相关工作段落", "可直接放进论文的英文段落"],
    ["gaps", "研究空白", "开放问题与下一步"],
    ["notes", "精读笔记", "概念、引文、疑问清单"],
  ];
  openModal(`
    <div class="modal-head"><h2>研究工具</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">基于当前文献的摘要、正文和已有总结生成。AI 不确定的地方会明确标出，不会编造实验或引用。</p>
    <div class="research-grid">
      ${tools.map(([mode, label, desc]) => `<button class="research-tool" data-action="research-run" data-mode="${mode}" data-label="${label}">
        <b>${label}</b><span>${desc}</span>
      </button>`).join("")}
    </div>
    <div id="researchBody"></div>`, { wide: true });
}

async function runResearch(mode, label) {
  if (!S.doc) return;
  const body = $("#researchBody");
  if (!body) return;
  body.innerHTML = `<div class="research-loading">${loadingHtml(`正在生成「${label}」…`)}</div>`;
  try {
    const data = await api("/api/ai/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_id: S.doc.id, mode }),
    });
    body.innerHTML = `<div class="research-result"><div class="panel-section-title">${escapeHtml(data.label || label)}</div>
      <div class="md">${mdToHtml(data.markdown)}</div>
      <div class="modal-actions">
        <button class="ghost" data-action="copy-text" data-text="${escapeAttr(data.markdown)}">${icon("copy")}复制</button>
        <button class="ghost" data-action="save-selection-note" data-text="${escapeAttr(data.markdown)}" data-title="研究工具 · ${escapeAttr(data.label || label)}">${icon("note")}保存为笔记</button>
      </div></div>`;
  } catch (error) {
    body.innerHTML = errorHtml(error.message);
  }
}

function openEpubLayoutModal() {
  if (!S.doc) return;
  const current = String(S.settings?.epub_font_size || "15");
  openModal(`
    <div class="modal-head"><h2>EPUB 排版</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">调大字号会重新分页，页数增加、页码变化。已有高亮和笔记仍按旧页码保存，建议读完当前这篇再调整。</p>
    <label>正文字号<select id="epubLayoutSize">
      ${[13, 15, 17, 19].map((size) => `<option value="${size}" ${current === String(size) ? "selected" : ""}>${size} pt${size === 15 ? "（标准）" : ""}</option>`).join("")}
    </select></label>
    <div class="modal-actions"><button class="ghost" data-close-modal>取消</button><button class="primary" data-action="apply-epub-layout">${icon("refresh")}重新排版</button></div>`);
}

async function applyEpubLayout() {
  if (!S.doc) return;
  const font_size = Number($("#epubLayoutSize")?.value || 15);
  try {
    const updated = await api(`/api/documents/${S.doc.id}/epub/relayout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ font_size }),
    });
    S.doc = updated;
    S.outline = await api(`/api/documents/${updated.id}/outline`).catch(() => []);
    if (S.settings) S.settings.epub_font_size = String(font_size);
    S.page = Math.min(S.page, updated.pages || 1);
    S.fitPending = true;
    S.scale = defaultScale();
    closeModal();
    renderReaderShell();
    await renderPage();
    toast(`已重新排版：${updated.pages} 页`);
  } catch (error) { toast(error.message, "error"); }
}

function openDocExportMenu() {
  openModal(`
    <div class="modal-head"><h2>导出 / 引用</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">Markdown 包含元数据、摘要、高亮和笔记。Obsidian 用 callout，Notion 用引用块和分隔线，Logseq 用大纲层级。双语 PDF 左侧保留原页面，右侧是中文译文。</p>
    <div class="dict-actions" style="margin-top:0">
      <button class="primary" data-action="export-md-obsidian">${icon("download")}Obsidian 笔记</button>
      <button class="ghost" data-action="export-md-notion">${icon("download")}Notion 页面</button>
      <button class="ghost" data-action="export-md-logseq">${icon("download")}Logseq 大纲</button>
      <button class="ghost" data-action="export-md-highlights">${icon("highlight")}高亮清单</button>
      <button class="ghost" data-action="export-md">${icon("download")}完整 Markdown</button>
      <button class="ghost" data-action="bilingual-export">${icon("translate")}双语 PDF</button>
      <button class="ghost" data-action="cite-bibtex">${icon("copy")}BibTeX</button>
      <button class="ghost" data-action="cite-ris">${icon("copy")}RIS</button>
    </div>`);
}

function openHighlightsExportMenu() {
  openModal(`
    <div class="modal-head"><h2>导出全部高亮</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">按文献分组导出所有高亮，保留页码和备注。选择你正在使用的笔记工具。</p>
    <div class="dict-actions" style="margin-top:0">
      <button class="primary" data-action="export-all-highlights">${icon("download")}Obsidian</button>
      <button class="ghost" data-action="export-all-highlights-notion">${icon("download")}Notion</button>
      <button class="ghost" data-action="export-all-highlights-logseq">${icon("download")}Logseq</button>
    </div>`);
}

function openLibraryMoreMenu() {
  openModal(`
    <div class="modal-head"><h2>更多工具</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">不常用的导入和整理工具收在这里，主界面只保留最常用的「导入 PDF」。</p>
    <div class="dict-actions" style="margin-top:0">
      <button class="ghost" data-action="upload-folder">${icon("upload")}导入文件夹</button>
      <button class="ghost" data-action="web-import-modal">${icon("compass")}从网页导入</button>
      <button class="ghost" data-action="zotero-modal">${icon("book")}从 Zotero 导入</button>
      <button class="ghost" data-action="compare-modal">${icon("summary")}多篇对比</button>
      <button class="ghost" data-action="export-highlights-menu">${icon("highlight")}导出全部高亮</button>
      <button class="ghost" data-action="add-collection">${icon("plus")}新建分类</button>
    </div>`);
}

function openVocabExportMenu() {
  openModal(`
    <div class="modal-head"><h2>导出 ${S.vocab.size} 个生词</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">CSV 适合 Excel / 欧路；Anki 包会带上单词、音标、释义、词形和上下文。</p>
    <div class="dict-actions" style="margin-top:0">
      <button class="primary" data-action="vocab-export">${icon("download")}导出 CSV</button>
      <button class="ghost" data-action="vocab-export-anki">${icon("download")}导出 Anki</button>
    </div>`);
}

function openDocEditModal() {
  const doc = S.doc;
  if (!doc) return;
  openModal(`
    <div class="modal-head"><h2>编辑文献信息</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <div class="form-grid">
      <label class="full">标题<input id="editDocTitle" value="${escapeAttr(doc.title)}"></label>
      <label class="full">作者<input id="editDocAuthors" value="${escapeAttr(doc.authors || "")}" placeholder="多位作者用逗号分隔"></label>
      <label>年份<input id="editDocYear" value="${escapeAttr(doc.year || "")}"></label>
      <label>期刊 / 会议<input id="editDocVenue" value="${escapeAttr(doc.venue || "")}"></label>
      <label class="full">DOI<input id="editDocDoi" value="${escapeAttr(doc.doi || "")}"></label>
      <label class="full">标签<input id="editDocTags" value="${escapeAttr(doc.tags || "")}" placeholder="用逗号或空格分隔"></label>
      <label class="full">分类<select id="editDocCollection"><option value="">未分类</option>${S.collections.map((collection) => `<option value="${collection.id}" ${doc.collection_id === collection.id ? "selected" : ""}>${escapeHtml(collection.name)}</option>`).join("")}</select></label>
      <label class="full">摘要<textarea id="editDocAbstract" style="min-height:100px">${escapeHtml(doc.abstract || "")}</textarea></label>
    </div>
    <div class="modal-actions"><button class="ghost" data-action="enrich-doc">从网络补全</button><button class="ghost" data-close-modal>取消</button><button class="primary" data-action="save-doc-edit">保存</button></div>`, { wide: true });
}

async function saveDocEdit() {
  if (!S.doc) return;
  const payload = {
    title: $("#editDocTitle").value.trim(),
    authors: $("#editDocAuthors").value.trim(),
    year: $("#editDocYear").value.trim(),
    venue: $("#editDocVenue").value.trim(),
    doi: $("#editDocDoi").value.trim(),
    tags: $("#editDocTags").value.trim(),
    abstract: $("#editDocAbstract").value.trim(),
    collection_id: $("#editDocCollection").value ? Number($("#editDocCollection").value) : null,
  };
  try {
    S.doc = await api(`/api/documents/${S.doc.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    closeModal();
    renderReaderShell();
    await loadCollections();
    toast("已保存");
  } catch (error) { toast(error.message, "error"); }
}

async function enrichDoc() {
  if (!S.doc) return;
  toast("正在从 arXiv / Crossref 补全元数据…");
  try {
    S.doc = await api(`/api/documents/${S.doc.id}/enrich`, { method: "POST" });
    closeModal();
    renderReaderShell();
    toast("元数据已补全");
  } catch (error) { toast(error.message, "error"); }
}

async function copyCitation(format) {
  if (!S.doc) return;
  try {
    const data = await api(`/api/documents/${S.doc.id}/cite?fmt=${format}`);
    try {
      await navigator.clipboard.writeText(data.text);
      closeModal();
      toast("引用已复制到剪贴板");
    } catch {
      openModal(`<div class="modal-head"><h2>引用</h2><button class="icon" data-close-modal>${icon("x")}</button></div><textarea style="width:100%;min-height:200px">${escapeHtml(data.text)}</textarea><div class="modal-actions"><button class="ghost" data-close-modal>关闭</button></div>`);
    }
  } catch (error) { toast(error.message, "error"); }
}

async function deleteCurrentDoc() {
  if (!S.doc) return;
  if (!confirm(`删除《${S.doc.title}》？批注、笔记和阅读进度会一起删除。`)) return;
  try {
    await api(`/api/documents/${S.doc.id}`, { method: "DELETE" });
    S.doc = null;
    closeModal();
    await Promise.all([loadCollections(), loadVocabCache(), loadDue()]);
    go("library");
  } catch (error) { toast(error.message, "error"); }
}

/* ------------------------------------------------------------------ vocab */
async function renderVocab() {
  topbar({ crumb: "生词本" });
  const view = $("#vocabView");
  view.innerHTML = `<div class="page">${loadingHtml("加载生词本…")}</div>`;
  try {
    const [stats, items] = await Promise.all([api("/api/vocab/stats"), api("/api/vocab")]);
    S.vocabStats = stats;
    S.vocabList = items;
    S.vocab = new Map(items.map((item) => [item.word.toLowerCase(), item]));
    updateBadges();
    view.innerHTML = `
      <div class="page">
        <div class="page-head"><div><h1>生词本</h1><p>阅读中收藏的词，按 FSRS 间隔重复复习。</p></div><div class="page-head-actions"><button class="ghost" data-action="vocab-export-menu">${icon("download")}导出</button><button class="primary" data-action="review-start">${icon("refresh")}开始复习</button></div></div>
        <div class="vocab-stats">
          <div class="mini-stat"><div class="v">${stats.total}</div><div class="l">全部生词</div></div>
          <div class="mini-stat"><div class="v" style="color:var(--orange)">${stats.due}</div><div class="l">待复习</div></div>
          <div class="mini-stat"><div class="v" style="color:var(--green)">${stats.mastered}</div><div class="l">已掌握</div></div>
          <div class="mini-stat"><div class="v">${stats.reviews}</div><div class="l">累计复习次数</div></div>
        </div>
        <div class="vocab-toolbar">
          <div class="search-box" style="max-width:280px">${icon("search")}<input id="vocabSearch" placeholder="搜索单词或释义…"></div>
          <div class="filter-row" id="vocabFilters">
            <button class="chip active" data-action="vocab-filter" data-filter="all">全部</button>
            <button class="chip" data-action="vocab-filter" data-filter="due">待复习</button>
            <button class="chip" data-action="vocab-filter" data-filter="mastered">已掌握</button>
            <button class="chip" data-action="vocab-filter" data-filter="cet4">四级</button>
            <button class="chip" data-action="vocab-filter" data-filter="cet6">六级</button>
            <button class="chip" data-action="vocab-filter" data-filter="ky">考研</button>
          </div>
          <span class="spacer"></span>
          <span class="faint" style="font-size:11px">${items.length} 个词</span>
        </div>
        <div id="vocabRows" class="vocab-list">${items.map((item) => vocabRow(item)).join("") || '<div class="panel-empty">生词本还是空的。去读一篇 PDF，划词收藏。</div>'}</div>
      </div>`;
    $("#vocabSearch").addEventListener("input", debounce((event) => filterVocab(event.target.value.trim()), 250));
  } catch (error) {
    view.innerHTML = `<div class="page">${errorHtml(error.message)}</div>`;
  }
}

function vocabRow(item) {
  return `
    <div class="vocab-row" data-action="open-word" data-word="${escapeAttr(item.word)}">
      <div><div class="word">${escapeHtml(item.word)}</div><div class="phonetic">/${escapeHtml(item.phonetic || "")}/</div></div>
      <div class="meaning">${escapeHtml(firstLine(item.translation) || firstLine(item.definition) || "—")}</div>
      <div class="tags-cell">${tagChips(item.tag)}</div>
      <div class="due ${isDue(item) ? "now" : ""}">${item.mastered ? "已掌握" : isDue(item) ? "待复习" : formatDue(item.due)}</div>
      <div class="actions">
        <button data-action="speak" data-text="${escapeAttr(item.word)}" title="朗读">${icon("volume")}</button>
        <button data-action="review-word" data-id="${item.id}" title="复习">${icon("refresh")}</button>
        <button class="del" data-action="delete-vocab" data-id="${item.id}" title="删除">${icon("trash")}</button>
      </div>
    </div>`;
}

function filterVocab(query) {
  const rows = S.vocabList.filter((item) => !query || item.word.toLowerCase().includes(query.toLowerCase()) || (item.translation || "").toLowerCase().includes(query.toLowerCase()));
  $("#vocabRows").innerHTML = rows.map((item) => vocabRow(item)).join("") || '<div class="panel-empty">没有匹配的生词。</div>';
}

async function deleteVocab(id) {
  try {
    await api(`/api/vocab/${id}`, { method: "DELETE" });
    S.vocabList = S.vocabList.filter((item) => item.id !== id);
    const item = [...S.vocab.values()].find((entry) => entry.id === id);
    if (item) S.vocab.delete(item.word.toLowerCase());
    updateBadges();
    if (S.view === "vocab") renderVocab();
    else if (S.panelOpen) renderPanel();
    toast("已删除");
  } catch (error) { toast(error.message, "error"); }
}

/* ----------------------------------------------------------------- review */
function reviewTabsHtml() {
  return `<div class="review-mode">
    <button class="${S.review.mode === "vocab" ? "active" : ""}" data-action="review-mode" data-mode="vocab">生词 <em>${S.due.length}</em></button>
    <button class="${S.review.mode === "highlight" ? "active" : ""}" data-action="review-mode" data-mode="highlight">高亮 <em>${S.highlightDue.length}</em></button>
  </div>`;
}

/* -------------------------------------------------------------- mistakes */
const MISTAKE_TYPES = ["细节题", "主旨题", "推断题", "词义题", "写作", "翻译", "其他"];

function extractAnswer(markdown = "") {
  const match = String(markdown).match(/##\s*答案\s*\n+([\s\S]*?)(?=\n##|$)/);
  return match ? match[1].trim().slice(0, 500) : "";
}

async function renderMistakes() {
  topbar({ crumb: "错题本" });
  const view = $("#mistakesView");
  view.innerHTML = `
    <div class="page">
      <div class="page-head">
        <div><h1>错题本</h1><p>只有你主动加入的题才会出现在这里；不会自动收录。</p></div>
        <div class="page-head-actions"><button class="primary" data-action="mistake-new">${icon("plus")}新建错题</button></div>
      </div>
      <div class="vocab-toolbar">
        <div class="search-box" style="max-width:320px">${icon("search")}<input id="mistakeSearch" placeholder="搜索题目、解析、来源…" value="${escapeAttr(S.mistakeQuery)}"></div>
        <div class="filter-row" id="mistakeFilters">
          <button class="chip ${!S.mistakeType ? "active" : ""}" data-action="mistake-filter" data-type="">全部</button>
          ${MISTAKE_TYPES.map((type) => `<button class="chip ${S.mistakeType === type ? "active" : ""}" data-action="mistake-filter" data-type="${type}">${type}</button>`).join("")}
        </div>
        <span class="spacer"></span>
        <span class="faint" id="mistakeSummary">加载中…</span>
      </div>
      <div id="mistakeList" class="mistake-list">${loadingHtml("加载错题…")}</div>
    </div>`;
  $("#mistakeSearch").addEventListener("input", debounce((event) => {
    S.mistakeQuery = event.target.value.trim();
    refreshMistakes();
  }, 250));
  await refreshMistakes();
}

function mistakeCardHtml(item) {
  const type = item.question_type || "未分类";
  return `<article class="mistake-card">
    <div class="mistake-top">
      <span class="mistake-type">${escapeHtml(type)}</span>
      ${item.source ? `<span class="mistake-source">${escapeHtml(item.source)}</span>` : ""}
      <span class="spacer"></span>
      <button class="icon subtle" data-action="mistake-edit" data-id="${item.id}" title="编辑">${icon("pen")}</button>
      <button class="icon subtle" data-action="mistake-delete" data-id="${item.id}" title="删除">${icon("trash")}</button>
    </div>
    <div class="mistake-question">${escapeHtml(item.question)}</div>
    ${item.options ? `<pre class="mistake-options">${escapeHtml(item.options)}</pre>` : ""}
    ${item.answer ? `<div class="mistake-answer"><b>答案</b><span>${escapeHtml(item.answer)}</span></div>` : ""}
    ${item.explanation ? `<details class="mistake-explain"><summary>解析</summary><div class="md">${mdToHtml(item.explanation)}</div></details>` : ""}
  </article>`;
}

async function refreshMistakes() {
  const params = new URLSearchParams();
  if (S.mistakeQuery) params.set("q", S.mistakeQuery);
  if (S.mistakeType) params.set("question_type", S.mistakeType);
  try {
    S.mistakes = await api(`/api/wrong-questions?${params.toString()}`);
    const summary = $("#mistakeSummary");
    if (summary) summary.textContent = `${S.mistakes.length} 道`;
    const list = $("#mistakeList");
    if (list) list.innerHTML = S.mistakes.length
      ? S.mistakes.map(mistakeCardHtml).join("")
      : `<div class="empty-state" style="padding:52px 20px"><div class="mark">${icon("target")}</div><h2>还没有错题</h2><p>做题时点「加入错题本」，或者在这里手动新建；Folio 不会自动收录。</p><button class="primary" data-action="mistake-new">新建错题</button></div>`;
    await loadMistakeCount();
  } catch (error) {
    const list = $("#mistakeList");
    if (list) list.innerHTML = errorHtml(error.message);
  }
}

function openMistakeForm(prefill = {}) {
  const item = prefill || {};
  S.mistakeEditId = item.id || null;
  const types = MISTAKE_TYPES.map((type) => `<option value="${type}" ${item.question_type === type ? "selected" : ""}>${type}</option>`).join("");
  openModal(`
    <div class="modal-head"><h2>${item.id ? "编辑错题" : "加入错题本"}</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">只有你点保存后才会加入；错题本不会自动收集。</p>
    <label>题目<textarea id="mistakeQuestion" style="min-height:100px" placeholder="题干">${escapeHtml(item.question || "")}</textarea></label>
    <label>选项<textarea id="mistakeOptions" style="min-height:80px" placeholder="A. …&#10;B. …&#10;C. …&#10;D. …">${escapeHtml(item.options || "")}</textarea></label>
    <div class="form-grid">
      <label>答案<input id="mistakeAnswer" value="${escapeAttr(item.answer || "")}" placeholder="例如 B"></label>
      <label>题型<select id="mistakeType"><option value="">未分类</option>${types}</select></label>
      <label class="full">来源<input id="mistakeSource" value="${escapeAttr(item.source || "")}" placeholder="例如 2024 年 6 月四级阅读 · 第 3 题"></label>
      <label class="full">解析<textarea id="mistakeExplanation" style="min-height:120px" placeholder="可以粘贴 AI 解析，也可以自己写">${escapeHtml(item.explanation || "")}</textarea></label>
    </div>
    <div class="modal-actions"><button class="ghost" data-close-modal>取消</button><button class="primary" data-action="mistake-save">保存到错题本</button></div>`, { wide: true });
}

async function saveMistake() {
  const payload = {
    question: $("#mistakeQuestion")?.value.trim() || "",
    options: $("#mistakeOptions")?.value || "",
    answer: $("#mistakeAnswer")?.value.trim() || "",
    question_type: $("#mistakeType")?.value || "",
    source: $("#mistakeSource")?.value.trim() || "",
    explanation: $("#mistakeExplanation")?.value || "",
  };
  if (!payload.question) { toast("先填题目", "error"); return; }
  try {
    if (S.mistakeEditId) {
      await api(`/api/wrong-questions/${S.mistakeEditId}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
    } else {
      await api("/api/wrong-questions", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, doc_id: S.doc?.id || null, page: S.page || null }),
      });
    }
    closeModal();
    toast("已加入错题本");
    if (S.view === "mistakes") await refreshMistakes();
    else await loadMistakeCount();
  } catch (error) { toast(error.message, "error"); }
}

async function deleteMistake(id) {
  if (!confirm("从错题本删除这道题？")) return;
  try {
    await api(`/api/wrong-questions/${id}`, { method: "DELETE" });
    toast("已删除");
    await refreshMistakes();
  } catch (error) { toast(error.message, "error"); }
}

function mistakeFromSolve() {
  const readerDoc = S.view === "reader" && S.doc ? S.doc : null;
  openMistakeForm({
    question: S.lastSolveQuestion || S.selection?.text || "",
    answer: extractAnswer(S.lastSolve || ""),
    explanation: S.lastSolve || "",
    source: readerDoc ? `${readerDoc.title} · 第 ${S.page} 页` : "",
  });
}

/* --------------------------------------------------------------- review */
async function renderReview() {
  topbar({ crumb: "今日复习", right: `<button class="ghost" data-action="go-vocab">${icon("book")}生词本</button>` });
  const view = $("#reviewView");
  view.innerHTML = `<div class="review-page">${loadingHtml("准备复习队列…")}</div>`;
  try {
    [S.due, S.highlightDue] = await Promise.all([
      api("/api/review/due"),
      api("/api/review/highlights/due"),
    ]);
    const mode = S.review.mode || "vocab";
    S.review = {
      mode,
      queue: S.due,
      index: 0,
      revealed: false,
      highlightQueue: S.highlightDue,
      highlightIndex: 0,
      session: { again: 0, hard: 0, good: 0, easy: 0 },
    };
    renderReviewCard();
  } catch (error) {
    view.innerHTML = `<div class="review-page">${errorHtml(error.message)}</div>`;
  }
}

function renderReviewCard() {
  const view = $("#reviewView");
  if (S.review.mode === "highlight") { renderHighlightReviewCard(); return; }
  const tabs = reviewTabsHtml();
  const queue = S.review.queue;
  if (!queue.length) {
    view.innerHTML = `<div class="review-page">${tabs}<div class="review-done"><div class="empty-state"><div class="mark">✓</div><h2>今天没有到期生词</h2><p>${S.highlightDue.length ? `还有 ${S.highlightDue.length} 条高亮可以复习。` : "去读一篇 PDF，把生词收进来，或明天再来。"}</p><button class="primary" data-action="go-vocab">打开生词本</button>${S.highlightDue.length ? '<button class="ghost" data-action="review-mode" data-mode="highlight">复习高亮</button>' : ""}</div></div></div>`;
    return;
  }
  if (S.review.index >= queue.length) {
    const session = S.review.session;
    view.innerHTML = `<div class="review-page">${tabs}<div class="review-done">
      <div class="stat-icon green" style="margin:0 auto 8px;width:52px;height:52px">${icon("award")}</div>
      <h2>本轮完成</h2><p>复习了 ${queue.length} 个词。${session.again ? `有 ${session.again} 个需要再看。` : "全部记得，很棒。"}</p>
      <div class="vocab-stats" style="max-width:520px;margin:0 auto 18px">
        <div class="mini-stat"><div class="v" style="color:var(--red)">${session.again}</div><div class="l">忘记</div></div>
        <div class="mini-stat"><div class="v" style="color:var(--orange)">${session.hard}</div><div class="l">模糊</div></div>
        <div class="mini-stat"><div class="v" style="color:var(--accent)">${session.good}</div><div class="l">记得</div></div>
        <div class="mini-stat"><div class="v" style="color:var(--green)">${session.easy}</div><div class="l">简单</div></div>
      </div>
      <div class="hero-actions" style="justify-content:center"><button class="primary" data-action="review-start">再来一轮</button><button class="ghost" data-action="go-vocab">打开生词本</button></div>
    </div></div>`;
    return;
  }
  const item = queue[S.review.index];
  const safeWord = escapeRegExp(escapeHtml(item.word));
  const context = item.context ? escapeHtml(item.context).replace(new RegExp(`(${safeWord})`, "ig"), "<b>$1</b>") : "";
  const progress = Math.round((S.review.index / queue.length) * 100);
  view.innerHTML = `
    <div class="review-page">
      ${tabs}
      <div class="review-top"><span>今日复习 · 生词</span><span>${S.review.index + 1} / ${queue.length}</span></div>
      <div class="review-progress"><div style="width:${progress}%"></div></div>
      <div class="flashcard">
        <div class="flash-word">${escapeHtml(item.word)}</div>
        <div class="flash-phonetic">/${escapeHtml(item.phonetic || "")}/ <button class="icon" data-action="speak" data-text="${escapeAttr(item.word)}" style="vertical-align:middle">${icon("volume")}</button></div>
        ${context ? `<div class="flash-context">${context}</div>` : ""}
        <div class="flash-answer ${S.review.revealed ? "" : "hidden"}">
          <div class="trans">${escapeHtml(item.translation || "（没有释义）")}</div>
          <div class="defs">${escapeHtml((item.definition || "").split("\n").slice(0, 3).join("\n"))}</div>
          <div class="tag-row">${tagChips(item.tag)}</div>
        </div>
        <div class="flash-actions">
          ${S.review.revealed
            ? `<div class="rate-grid">
                <button data-action="rate" data-rating="1">忘记</button>
                <button data-action="rate" data-rating="2">模糊</button>
                <button data-action="rate" data-rating="3">记得</button>
                <button data-action="rate" data-rating="4">简单</button>
              </div><div class="review-kbd">按 <kbd>1</kbd>–<kbd>4</kbd> 评分</div>`
            : `<button class="primary" data-action="reveal">显示答案</button><div class="review-kbd">按 <kbd>空格</kbd> 显示答案</div>`}
        </div>
      </div>
    </div>`;
}

function renderHighlightReviewCard() {
  const view = $("#reviewView");
  const tabs = reviewTabsHtml();
  const queue = S.review.highlightQueue;
  if (!queue.length) {
    view.innerHTML = `<div class="review-page">${tabs}<div class="review-done"><div class="empty-state"><div class="mark">✓</div><h2>今天没有到期高亮</h2><p>${S.due.length ? `还有 ${S.due.length} 个生词可以复习。` : "选中文字时存几个高亮，这里会按 FSRS 复习。"}</p><button class="primary" data-action="review-mode" data-mode="vocab">复习生词</button></div></div></div>`;
    return;
  }
  if (S.review.highlightIndex >= queue.length) {
    const session = S.review.session;
    view.innerHTML = `<div class="review-page">${tabs}<div class="review-done"><div class="stat-icon green" style="margin:0 auto 8px;width:52px;height:52px">${icon("award")}</div><h2>高亮复习完成</h2><p>复习了 ${queue.length} 条高亮。</p><div class="hero-actions" style="justify-content:center"><button class="primary" data-action="review-mode" data-mode="vocab">复习生词</button><button class="ghost" data-action="go-vocab">生词本</button></div></div></div>`;
    return;
  }
  const item = queue[S.review.highlightIndex];
  const progress = Math.round((S.review.highlightIndex / queue.length) * 100);
  view.innerHTML = `
    <div class="review-page">
      ${tabs}
      <div class="review-top"><span>今日复习 · 高亮</span><span>${S.review.highlightIndex + 1} / ${queue.length}</span></div>
      <div class="review-progress"><div style="width:${progress}%"></div></div>
      <div class="flashcard">
        <div class="eyebrow">${escapeHtml(item.doc_title || "")} · 第 ${item.page} 页</div>
        <div class="flash-quote">${escapeHtml(item.text || "（没有文字）")}</div>
        ${item.note ? `<div class="flash-context">${escapeHtml(item.note)}</div>` : ""}
        <div class="flash-actions">
          <div class="rate-grid">
            <button data-action="rate-highlight" data-rating="1">忘记</button>
            <button data-action="rate-highlight" data-rating="2">模糊</button>
            <button data-action="rate-highlight" data-rating="3">记得</button>
            <button data-action="rate-highlight" data-rating="4">简单</button>
          </div>
          <div class="review-kbd">按 <kbd>1</kbd>–<kbd>4</kbd> 评分 · <button class="ghost small" data-action="open-doc" data-id="${item.doc_id}" data-page="${item.page}">打开原文</button></div>
        </div>
      </div>
    </div>`;
}

async function rateWord(rating) {
  const item = S.review.queue[S.review.index];
  if (!item) return;
  try {
    const result = await api(`/api/vocab/${item.id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating }),
    });
    const local = S.vocab.get(item.word.toLowerCase());
    if (local) local.due = result.due;
    if (rating > 1) S.due = S.due.filter((entry) => entry.id !== item.id);
    const key = ["", "again", "hard", "good", "easy"][rating];
    if (S.review.session[key] !== undefined) S.review.session[key] += 1;
    if (rating === 1) S.review.queue.push(item);
    S.review.index += 1;
    S.review.revealed = false;
    updateBadges();
    renderReviewCard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function rateHighlight(rating) {
  const item = S.review.highlightQueue[S.review.highlightIndex];
  if (!item) return;
  try {
    await api(`/api/highlights/${item.id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating }),
    });
    if (rating > 1) S.highlightDue = S.highlightDue.filter((entry) => entry.id !== item.id);
    const key = ["", "again", "hard", "good", "easy"][rating];
    if (S.review.session[key] !== undefined) S.review.session[key] += 1;
    if (rating === 1) S.review.highlightQueue.push(item);
    S.review.highlightIndex += 1;
    updateBadges();
    renderHighlightReviewCard();
  } catch (error) {
    toast(error.message, "error");
  }
}

function startReviewForWord(id) {
  const item = S.vocabList.find((entry) => entry.id === id) || [...S.vocab.values()].find((entry) => entry.id === id);
  if (!item) return;
  S.review = { mode: "vocab", queue: [item], index: 0, revealed: false, highlightQueue: [], highlightIndex: 0, session: { again: 0, hard: 0, good: 0, easy: 0 } };
  go("review").then(() => { S.review.queue = [item]; renderReviewCard(); });
}

/* ------------------------------------------------------------------ stats */
async function renderStats() {
  topbar({ crumb: "学习统计", right: `<button class="ghost" data-action="annual-report">${icon("award")}年度报告</button>` });
  const view = $("#statsView");
  view.innerHTML = `<div class="page">${loadingHtml("统计中…")}</div>`;
  try {
    const [data, annotations, notes] = await Promise.all([
      api("/api/stats/overview"),
      api("/api/annotations").catch(() => []),
      api("/api/notes").catch(() => []),
    ]);
    S.stats = data;
    const tags = Object.entries(data.vocab.tags || {}).sort((a, b) => b[1] - a[1]).slice(0, 6);
    const maxTag = Math.max(1, ...tags.map(([, count]) => count));
    view.innerHTML = `
      <div class="page">
        <div class="page-head"><div><h1>学习统计</h1><p>阅读、生词和复习的累计数据。</p></div></div>
        <div class="stats-grid">
          <div class="mini-stat"><div class="v">${fmtDuration(data.reading_seconds)}</div><div class="l">累计阅读</div></div>
          <div class="mini-stat"><div class="v">${data.documents}</div><div class="l">文献</div></div>
          <div class="mini-stat"><div class="v">${data.vocab.total}</div><div class="l">生词</div></div>
          <div class="mini-stat"><div class="v" style="color:var(--orange)">${data.streak}</div><div class="l">连续学习天数</div></div>
        </div>
        <div class="stats-columns">
          <section class="card"><div class="card-head"><h3>学习热力图</h3><span class="eyebrow">最近 180 天</span></div><div class="card-body">${heatmapHtml(data.heatmap, 180)}</div></section>
          <section class="card"><div class="card-head"><h3>生词构成</h3></div><div class="card-body">
            ${tags.length ? tags.map(([tag, count]) => `<div class="bar-row"><span>${TAG_LABELS[tag] || tag}</span><div class="bar-track"><div class="bar-fill" style="width:${(count / maxTag) * 100}%"></div></div><span class="bar-value">${count}</span></div>`).join("") : '<div class="panel-empty">还没有标签数据。</div>'}
            <div class="bar-row"><span>已掌握</span><div class="bar-track"><div class="bar-fill" style="width:${data.vocab.total ? (data.vocab.mastered / data.vocab.total) * 100 : 0}%;background:var(--green)"></div></div><span class="bar-value">${data.vocab.mastered}</span></div>
          </div></section>
        </div>
        <div class="stats-columns">
          <section class="card"><div class="card-head"><h3>最近标注</h3><span class="eyebrow">${annotations.length}</span></div><div class="card-body">
            ${annotations.slice(0, 6).map((item) => `<div class="mark-row"><span class="mark-dot" style="background:${markColor(item.color)}"></span><span class="mark-text">${escapeHtml((item.text || "").slice(0, 80))}<br><span class="faint">${escapeHtml(item.doc_title || "")}</span></span><span class="mark-page">P${item.page}</span></div>`).join("") || '<div class="panel-empty">还没有标注。</div>'}
          </div></section>
          <section class="card"><div class="card-head"><h3>最近笔记</h3><span class="eyebrow">${notes.length}</span></div><div class="card-body">
            ${notes.slice(0, 6).map((note) => `<div class="note-card"><div class="note-title"><span>${escapeHtml(note.title || `第 ${note.page} 页`)}</span><span class="faint" style="font-size:9px">${escapeHtml(note.doc_title || "")}</span></div><div class="note-body">${escapeHtml(note.content.slice(0, 120))}</div></div>`).join("") || '<div class="panel-empty">还没有笔记。</div>'}
          </div></section>
        </div>
      </div>`;
  } catch (error) {
    view.innerHTML = `<div class="page">${errorHtml(error.message)}</div>`;
  }
}

function heatmapHtml(data = [], days = 120) {
  const map = new Map((data || []).map((item) => [item.day, item.count]));
  const end = new Date();
  end.setHours(0, 0, 0, 0);
  const start = new Date(end);
  start.setDate(end.getDate() - days + 1);
  start.setDate(start.getDate() - start.getDay());
  const cells = [];
  for (let cursor = new Date(start); cursor <= end; cursor.setDate(cursor.getDate() + 1)) {
    const key = cursor.toISOString().slice(0, 10);
    const count = map.get(key) || 0;
    const level = count === 0 ? 0 : count < 3 ? 1 : count < 8 ? 2 : count < 15 ? 3 : 4;
    cells.push(`<div class="heat-cell l${level}" title="${key} · ${count} 次"></div>`);
  }
  return `<div class="heatmap-wrap"><div class="heatmap">${cells.join("")}</div></div>
    <div class="heat-legend">少 <span class="heat-cell"></span><span class="heat-cell l1"></span><span class="heat-cell l2"></span><span class="heat-cell l3"></span><span class="heat-cell l4"></span> 多</div>`;
}

/* -------------------------------------------------------------------- CET */
async function renderCET() {
  topbar({ crumb: "四六级精读" });
  const view = $("#cetView");
  view.innerHTML = `<div class="cet-page"><div class="cet-side">${loadingHtml("加载文章…")}</div><div class="cet-main"></div></div>`;
  try {
    const articles = await api("/api/articles");
    view.innerHTML = `
      <div class="cet-page">
        <aside class="cet-side">
          <h2>四六级精读</h2>
          <p>粘贴真题阅读或外刊文章，自动标出 CET-4 / CET-6 核心词，点词即查。</p>
          <input id="cetTitle" placeholder="标题（可选）">
          <textarea id="cetText" placeholder="Paste an English article here…">${escapeHtml(S.cet.text || "")}</textarea>
          <div class="row"><button class="primary" data-action="cet-analyze">${icon("play")}开始精读</button><button class="ghost" data-action="cet-save">保存文章</button></div>
          <div class="cet-saved-title">已保存文章 · ${articles.length}</div>
          ${articles.map((article) => `<div class="cet-saved-item" data-action="open-article" data-id="${article.id}"><b>${escapeHtml(article.title)}</b><span>${article.chars} 字符 · ${fmtDate(article.created_at)}</span><button class="cet-del" data-action="delete-article" data-id="${article.id}" title="删除">×</button></div>`).join("") || '<div class="panel-empty" style="padding:14px 0">还没有保存的文章。</div>'}
          <div class="cet-saved-title">训练</div>
          <div class="filter-row">
            <button class="chip" data-action="writing-modal">写作批改</button>
            <button class="chip" data-action="question-solver-modal">题目解析</button>
          </div>
        </aside>
        <main class="cet-main">
          <div class="cet-main-inner" id="cetMain">
            ${S.cet.analysis ? "" : `<div class="empty-state" style="padding-top:80px"><div class="mark">Aa</div><h2>粘贴一篇英文文章</h2><p>左边输入文章，点「开始精读」；也可以用 AI 生成阅读理解题。</p></div>`}
          </div>
        </main>
      </div>`;
    if (S.cet.analysis) renderCETAnalysis();
  } catch (error) {
    view.innerHTML = `<div class="page">${errorHtml(error.message)}</div>`;
  }
}

async function analyzeCET() {
  const text = $("#cetText")?.value.trim() || "";
  if (text.length < 20) { toast("先粘贴一段英文文章", "error"); return; }
  try {
    const analysis = await api("/api/cet/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    S.cet.analysis = analysis;
    S.cet.text = text;
    S.cet.quiz = null;
    S.cet.answers = {};
    S.cet.submitted = false;
    renderCETAnalysis();
  } catch (error) { toast(error.message, "error"); }
}

function renderCETAnalysis() {
  const analysis = S.cet.analysis;
  if (!analysis) return;
  $("#cetMain").innerHTML = `
    <div class="cet-stats">
      <span><b>${analysis.total}</b>词</span><span><b>${analysis.unique}</b>不同词</span>
      <span><b>${analysis.cet4}</b>四级词</span><span><b>${analysis.cet6}</b>六级词</span>
      <span class="spacer"></span><button class="ghost small" data-action="quiz-generate">${icon("pen")}生成练习</button>
    </div>
    <article class="cet-article" id="cetArticle">${cetArticleHtml(S.cet.text, analysis)}</article>
    <div id="quizArea">${S.cet.quiz ? quizHtml() : ""}</div>`;
}

function cetArticleHtml(text, analysis) {
  const tags = analysis.tags || {};
  return text.split(/\n+/).filter((paragraph) => paragraph.trim()).map((paragraph) => {
    const sentences = paragraph.match(/[^.!?]+[.!?]+["')\]]?|[^.!?]+$/g) || [paragraph];
    return `<p>${sentences.map((sentence) => {
      const sentenceAttr = escapeAttr(sentence.trim());
      return sentence.split(/([A-Za-z][A-Za-z'’-]*)/g).map((part) => {
        if (/^[A-Za-z][A-Za-z'’-]*$/.test(part)) {
          const marks = (tags[part.toLowerCase()] || "").split(/\s+/);
          let classes = "cw";
          if (marks.includes("cet4")) classes += " cet4";
          if (marks.includes("cet6")) classes += " cet6";
          return `<span class="${classes}" data-action="open-word" data-word="${escapeAttr(part)}" data-context="${sentenceAttr}">${escapeHtml(part)}</span>`;
        }
        return escapeHtml(part);
      }).join("");
    }).join("")}</p>`;
  }).join("");
}

async function saveCETArticle() {
  const text = $("#cetText")?.value.trim() || "";
  if (!text) return;
  try {
    await api("/api/articles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: $("#cetTitle")?.value.trim() || "", text }),
    });
    toast("文章已保存");
    await renderCET();
  } catch (error) { toast(error.message, "error"); }
}

async function openArticle(id) {
  try {
    const article = await api(`/api/articles/${id}`);
    S.cet.text = article.text;
    S.cet.article = article;
    await renderCET();
    $("#cetTitle").value = article.title;
    $("#cetText").value = article.text;
    await analyzeCET();
  } catch (error) { toast(error.message, "error"); }
}

async function generateQuiz() {
  const text = S.cet.text || $("#cetText")?.value || "";
  if (!text) return;
  $("#quizArea").innerHTML = loadingHtml("AI 正在出题…");
  try {
    const data = await api("/api/ai/quiz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, count: 5 }),
    });
    S.cet.quiz = data.questions || [];
    S.cet.answers = {};
    S.cet.submitted = false;
    $("#quizArea").innerHTML = quizHtml();
  } catch (error) { $("#quizArea").innerHTML = errorHtml(error.message); }
}

function quizHtml() {
  if (!S.cet.quiz?.length) return "";
  return `<div class="quiz-card">
    <div class="panel-section-title">阅读理解练习<span>${S.cet.quiz.length} 题</span></div>
    ${S.cet.quiz.map((question, index) => `
      <div style="margin-bottom:18px">
        <div class="quiz-q">${index + 1}. ${escapeHtml(question.question)}</div>
        ${(question.options || []).map((option, optionIndex) => {
          const selected = S.cet.answers[index] === optionIndex;
          let cls = "quiz-option";
          if (selected) cls += " selected";
          if (S.cet.submitted) {
            if (optionIndex === question.answer) cls += " correct";
            else if (selected) cls += " wrong";
          }
          return `<div class="${cls}" data-action="quiz-option" data-index="${index}" data-option="${optionIndex}"><span class="letter">${String.fromCharCode(65 + optionIndex)}</span><span>${escapeHtml(option)}</span></div>`;
        }).join("")}
        ${S.cet.submitted ? `<div class="quiz-explanation">${escapeHtml(question.explanation || "")}</div>` : ""}
      </div>`).join("")}
    <div class="dict-actions">
      ${S.cet.submitted ? `<button class="primary" data-action="quiz-generate">再出一套</button>` : `<button class="primary" data-action="quiz-submit">提交答案</button>`}
    </div>
  </div>`;
}

function submitQuiz() {
  S.cet.submitted = true;
  $("#quizArea").innerHTML = quizHtml();
  const correct = S.cet.quiz.reduce((sum, question, index) => sum + (S.cet.answers[index] === question.answer ? 1 : 0), 0);
  toast(`答对 ${correct} / ${S.cet.quiz.length}`);
}

/* ------------------------------------------------------------ CET training */
function openWritingModal() {
  openModal(`
    <div class="modal-head"><h2>写作批改</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">按四六级 15 分制批改：内容、结构、语言、逐句修改，再给一篇升级版范文。</p>
    <label>题目<input id="writingPrompt" value="${escapeAttr(S.cet.article?.title || "")}" placeholder="例如：On the Importance of Reading"></label>
    <label>作文<textarea id="writingEssay" style="min-height:180px" placeholder="Paste or write your essay here…"></textarea></label>
    <div class="modal-actions"><button class="ghost" data-close-modal>取消</button><button class="primary" data-action="run-writing">开始批改</button></div>
    <div id="writingResult"></div>`, { wide: true });
}

async function runWritingReview() {
  const essay = $("#writingEssay")?.value.trim() || "";
  if (essay.length < 80) { toast("至少写 80 词", "error"); return; }
  $("#writingResult").innerHTML = loadingHtml("AI 正在批改作文…");
  try {
    const data = await api("/api/ai/write-review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: $("#writingPrompt")?.value.trim() || "", essay }),
    });
    $("#writingResult").innerHTML = `<div class="md" style="margin-top:16px">${mdToHtml(data.markdown)}</div>`;
  } catch (error) {
    $("#writingResult").innerHTML = errorHtml(error.message);
  }
}

/* ------------------------------------------------------------------ modal: settings */
const PRESETS = {
  deepseek: { base: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  openai: { base: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  ollama: { base: "http://127.0.0.1:11434/v1", model: "qwen2.5:7b" },
  custom: {},
};

async function showStorageSetup(status = S.storage, required = false) {
  S.storage = status || S.storage;
  S.storageRequired = required;
  const current = S.storage?.data_dir || S.storage?.default_dir || "";
  const defaultDir = S.storage?.default_dir || "";
  openModal(`
    <div class="modal-head"><h2>${required ? "选择资料库位置" : "更改资料库位置"}</h2>${required ? "" : `<button class="icon" data-close-modal>${icon("x")}</button>`}</div>
    <p class="modal-note">Folio 会把数据库、导入的 PDF / EPUB、导出文件、词典都放在这个文件夹。建议放在非系统盘，之后换电脑时复制这个文件夹即可。</p>
    <label>资料库文件夹<input id="storagePath" value="${escapeAttr(current)}" placeholder="例如 D:/FolioData"></label>
    <div class="storage-hint">
      <b>会放在这里</b>
      <span>readmate.db · pdfs/ · cache/ · exports/ · ecdict.db</span>
    </div>
    <div class="modal-actions">
      ${required && defaultDir ? `<button class="ghost" data-action="storage-default">使用当前位置</button>` : ""}
      <button class="ghost" data-action="storage-pick">浏览…</button>
      <button class="primary" data-action="storage-save">使用这个文件夹</button>
    </div>
    ${required ? '<div class="hint" style="margin-top:12px">第一次使用必须先选择资料库位置；以后可以在设置里更改。</div>' : '<div class="hint" style="margin-top:12px">更改位置会把现有数据库、PDF 和导出复制到新文件夹；旧文件夹不会自动删除。</div>'}`, { sticky: required });
}

async function saveStorageLocation(path) {
  const target = String(path || $("#storagePath")?.value || "").trim();
  if (!target) { toast("请先选择文件夹", "error"); return; }
  const button = $('[data-action="storage-save"]');
  if (button) { button.disabled = true; button.textContent = "正在迁移…"; }
  try {
    const data = await api("/api/storage/set", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: target }),
    });
    toast(data.existing ? "资料库已设置，检测到已有数据" : "资料库已设置");
    setTimeout(() => location.reload(), 350);
  } catch (error) {
    toast(error.message, "error");
    if (button) { button.disabled = false; button.textContent = "使用这个文件夹"; }
  }
}

async function pickStorageFolder() {
  try {
    const data = await api("/api/storage/pick", { method: "POST" });
    if (data.path) $("#storagePath").value = data.path;
  } catch (error) { toast(error.message, "error"); }
}

function openSettings() {
  const settings = S.settings || { provider: "deepseek", base_url: "https://api.deepseek.com/v1", model: "deepseek-chat", has_key: false };
  openModal(`
    <div class="modal-head"><h2>设置</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">AI 解释、翻译、总结需要一个 OpenAI 兼容接口。推荐 DeepSeek，费用很低；也可以接本地 Ollama，完全离线。</p>
    <label>服务商<select id="providerSelect">
      <option value="deepseek" ${settings.provider === "deepseek" ? "selected" : ""}>DeepSeek</option>
      <option value="openai" ${settings.provider === "openai" ? "selected" : ""}>OpenAI</option>
      <option value="ollama" ${settings.provider === "ollama" ? "selected" : ""}>本地 Ollama</option>
      <option value="custom" ${settings.provider === "custom" ? "selected" : ""}>自定义</option>
    </select></label>
    <label>Base URL<input id="baseUrl" value="${escapeAttr(settings.base_url || "")}"></label>
    <label>模型名<input id="modelName" value="${escapeAttr(settings.model || "")}"></label>
    <label>API Key<input id="apiKey" type="password" placeholder="${settings.has_key ? "已保存，留空则不修改" : "sk-..."}"></label>
    <div class="hint">Key 只写入本机 data/readmate.db，不会上传。词典和 PDF 完全离线。</div>
    <label style="margin-top:14px">Zotero 本地 API<input id="zoteroUrl" value="${escapeAttr(settings.zotero_url || "http://127.0.0.1:23119")}"></label>
    <div class="panel-section-title" style="margin-top:18px">阅读</div>
    <label>EPUB 字号<select id="epubFontSize">
      ${[13, 15, 17, 19].map((size) => `<option value="${size}" ${String(settings.epub_font_size || 15) === String(size) ? "selected" : ""}>${size} pt${size === 15 ? "（标准）" : ""}</option>`).join("")}
    </select></label>
    <label style="display:flex;align-items:center;gap:7px;font-size:12px"><input id="autoLookup" type="checkbox" ${settings.auto_lookup !== false ? "checked" : ""} style="width:auto">划词自动查词（单词 / 短语，带发音）</label>
    <div class="hint">影响之后导入的 EPUB；已经导入的 EPUB 可以在「文献 → 更多 → EPUB 排版」里重新生成页面。</div>
    <div class="panel-section-title" style="margin-top:18px">跨设备同步（WebDAV）</div>
    <label>WebDAV 地址<input id="syncUrl" value="${escapeAttr(settings.sync_url || "")}" placeholder="https://dav.jianguoyun.com/dav/Folio"></label>
    <div class="form-grid">
      <label>账号<input id="syncUser" value="${escapeAttr(settings.sync_user || "")}" placeholder="WebDAV 账号"></label>
      <label>密码<input id="syncPassword" type="password" placeholder="${settings.has_sync_password ? "已保存，留空不改" : "应用密码"}"></label>
    </div>
    <label style="display:flex;align-items:center;gap:7px;font-size:12px"><input id="syncPdfs" type="checkbox" ${settings.sync_pdfs ? "checked" : ""} style="width:auto">同步 PDF 文件（关闭则只同步元数据/生词/笔记）</label>
    <div class="row" style="margin-top:0">
      <button class="ghost" data-action="sync-test">测试 WebDAV</button>
      <button class="primary" data-action="sync-now">${icon("refresh")}立即同步</button>
      <button class="ghost" data-action="sync-conflicts">冲突 <em id="syncConflictCount"></em></button>
      <span class="faint" style="font-size:10.5px">${settings.last_sync ? `上次：${fmtDate(settings.last_sync)}` : "尚未同步"}</span>
    </div>
    <div class="panel-section-title" style="margin-top:18px">数据</div>
    <div class="storage-current"><div><b>资料库位置</b><span>${escapeHtml(S.storage?.data_dir || "尚未设置")}</span></div><button class="ghost small" data-action="storage-change">更改…</button></div>
    <div class="dict-actions" style="margin-top:0">
      <button class="ghost" data-action="backup">${icon("download")}备份数据库</button>
      <button class="ghost" data-action="shortcuts">查看快捷键</button>
    </div>
    <div class="modal-actions"><button class="ghost" data-action="test-ai">测试连接</button><button class="primary" data-action="save-settings">保存</button></div>
    <details style="margin-top:14px;font-size:11px;color:var(--faint)">
      <summary>数据与设计来源</summary>
      <p>词典 ECDICT（MIT）· 间隔重复 FSRS（MIT）· PDF 解析 PyMuPDF · 界面参考 Zotero / Readwise Reader / PaperLens / Gloss / Koodo / Readest，未复制其代码。</p>
    </details>`);
  $("#providerSelect").addEventListener("change", (event) => {
    const preset = PRESETS[event.target.value];
    if (preset?.base) { $("#baseUrl").value = preset.base; $("#modelName").value = preset.model; }
  });
  loadSyncConflicts();
}

async function saveSettings(close = true) {
  const payload = {
    provider: $("#providerSelect")?.value || "deepseek",
    base_url: $("#baseUrl")?.value.trim() || "",
    model: $("#modelName")?.value.trim() || "",
    api_key: $("#apiKey")?.value.trim() || "",
    zotero_url: $("#zoteroUrl")?.value.trim() || "",
    sync_url: $("#syncUrl")?.value.trim() || "",
    sync_user: $("#syncUser")?.value.trim() || "",
    sync_password: $("#syncPassword")?.value.trim() || "",
    sync_pdfs: $("#syncPdfs")?.checked ? "1" : "0",
    epub_font_size: $("#epubFontSize")?.value || "15",
    auto_lookup: $("#autoLookup")?.checked ? "1" : "0",
  };
  S.settings = await api("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (close) { closeModal(); toast("设置已保存"); }
}

async function testAI() {
  try {
    await saveSettings(false);
    const result = await api("/api/settings/test", { method: "POST" });
    toast(`连接正常：${result.answer}`);
  } catch (error) { toast(error.message, "error"); }
}

async function loadSyncConflicts() {
  try {
    S.syncConflicts = await api("/api/sync/conflicts");
    const badge = $("#syncConflictCount");
    if (badge) badge.textContent = S.syncConflicts.length ? String(S.syncConflicts.length) : "";
  } catch { /* optional */ }
}

const CONFLICT_FIELDS = {
  document: [["title", "标题"], ["authors", "作者"], ["year", "年份"], ["venue", "期刊 / 会议"], ["doi", "DOI"], ["abstract", "摘要"]],
  vocab: [["translation", "翻译"], ["definition", "释义"], ["tag", "标签"], ["context", "语境"], ["deck", "词库"]],
  highlight: [["text", "高亮文字"], ["note", "备注"], ["color", "颜色"], ["page", "页码"]],
  note: [["title", "标题"], ["content", "正文"], ["page", "页码"]],
};
const CONFLICT_LABELS = { document: "文献", vocab: "生词", highlight: "高亮", note: "笔记" };
const COLOR_LABELS = { yellow: "黄", green: "绿", blue: "蓝", pink: "粉", purple: "紫" };
const sameConflictValue = (a, b) => JSON.stringify(a ?? "") === JSON.stringify(b ?? "");

function conflictValue(field, value) {
  if (value === undefined || value === null || value === "") return "—";
  if (field === "page") return `第 ${value} 页`;
  if (field === "color") return COLOR_LABELS[value] || value;
  return String(value);
}

function conflictTitle(item) {
  const local = item.local || {};
  const remote = item.remote || {};
  return local.title || local.word || local.text || local.content
    || remote.title || remote.word || remote.text || remote.content
    || item.entity_key;
}

function conflictBody(item) {
  const local = item.local || {};
  const remote = item.remote || {};
  const fields = CONFLICT_FIELDS[item.entity_type] || [];
  const localDeleted = !!local.deleted;
  const remoteDeleted = !!remote.deleted;
  if (localDeleted || remoteDeleted) {
    const alive = localDeleted ? remote : local;
    const who = localDeleted ? "本机已删除，云端仍有这条记录" : "云端已删除，本机仍有这条记录";
    const details = fields
      .filter(([key]) => alive[key])
      .slice(0, 2)
      .map(([key, label]) => `<div class="conflict-line"><span>${label}</span><b>${escapeHtml(conflictValue(key, alive[key]).slice(0, 120))}</b></div>`)
      .join("");
    return `<div class="conflict-deleted">${escapeHtml(who)}</div>${details}`;
  }
  const changed = fields.filter(([key]) => !sameConflictValue(local[key], remote[key]));
  if (!changed.length) return `<div class="conflict-line"><span>两边内容一致</span><b>只需确认保留哪一侧</b></div>`;
  return `<div class="conflict-diff">
    <div class="conflict-diff-head"><span>字段</span><span>本机</span><span>云端</span></div>
    ${changed.slice(0, 6).map(([key, label]) => `
      <div class="conflict-diff-row">
        <span class="conflict-field">${label}</span>
        <span class="conflict-value">${escapeHtml(conflictValue(key, local[key]).slice(0, 160))}</span>
        <span class="conflict-value cloud">${escapeHtml(conflictValue(key, remote[key]).slice(0, 160))}</span>
      </div>`).join("")}
  </div>`;
}

async function openSyncConflicts() {
  await loadSyncConflicts();
  const total = S.syncConflicts.length;
  openModal(`
    <div class="modal-head"><h2>同步冲突</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">${total ? `有 ${total} 处两边不一致。逐条选择保留本机或采用云端；处理完再同步一次即可。` : "两台设备的内容已经一致，没有待处理的冲突。"}</p>
    <div class="conflict-list">
      ${total ? S.syncConflicts.map((item) => {
        const label = CONFLICT_LABELS[item.entity_type] || item.entity_type;
        const localDeleted = !!(item.local || {}).deleted;
        const remoteDeleted = !!(item.remote || {}).deleted;
        return `<article class="conflict-card">
          <div class="conflict-head">
            <span class="conflict-kind">${label}</span>
            <strong>${escapeHtml(String(conflictTitle(item)).slice(0, 100))}</strong>
            ${localDeleted || remoteDeleted ? '<span class="conflict-flag">删除冲突</span>' : '<span class="conflict-flag content">内容冲突</span>'}
          </div>
          ${conflictBody(item)}
          <div class="conflict-actions">
            <button class="ghost small" data-action="resolve-sync-conflict" data-id="${item.id}" data-choice="local">保留本机</button>
            <button class="primary small" data-action="resolve-sync-conflict" data-id="${item.id}" data-choice="cloud">采用云端</button>
          </div>
        </article>`;
      }).join("") : '<div class="panel-empty">没有未处理的冲突。</div>'}
    </div>`, { wide: true });
}

async function resolveSyncConflict(id, choice) {
  try {
    await api(`/api/sync/conflicts/${id}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ choice }),
    });
    await loadSyncConflicts();
    if (S.syncConflicts.length) await openSyncConflicts();
    else closeModal();
    await Promise.all([loadCollections(), loadVocabCache(), loadDue(), loadTopics()]);
    if (S.view === "reader" && S.doc) {
      const [highlights, notes] = await Promise.all([
        api(`/api/highlights/${S.doc.id}`),
        api(`/api/notes/${S.doc.id}`),
      ]);
      S.highlights = highlights;
      S.notes = notes;
      await renderPage();
      renderMarksPanel();
    }
    if (S.view === "home") await renderHome();
    else if (S.view === "library") await refreshLibrary();
    toast("冲突已处理");
  } catch (error) { toast(error.message, "error"); }
}

async function testSync() {
  try {
    await saveSettings(false);
    await api("/api/sync/test", { method: "POST" });
    toast("WebDAV 可用");
  } catch (error) { toast(error.message, "error"); }
}

async function runSync() {
  try {
    await saveSettings(false);
    toast("正在与 WebDAV 同步…");
    const data = await api("/api/sync/now", { method: "POST" });
    const counts = data.counts || {};
    S.settings.last_sync = data.last_sync;
    await Promise.all([loadCollections(), loadVocabCache(), loadDue(), loadTopics(), loadNotifications(), loadSyncConflicts()]);
    if (S.view === "home") await renderHome();
    else if (S.view === "library") await refreshLibrary();
    openSettings();
    toast(`同步完成：文献 +${counts.documents || 0}，生词 +${counts.vocab || 0}，删除 ${counts.deleted || 0}，冲突 ${counts.conflicts || 0}`);
    if (counts.conflicts) await openSyncConflicts();
  } catch (error) { toast(error.message, "error"); }
}

/* ------------------------------------------------------------ doc actions */
function openShortcuts() {
  openModal(`
    <div class="modal-head"><h2>快捷键</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <div class="term-row"><b>← / →</b><span>上一页 / 下一页</span></div>
    <div class="term-row"><b>B</b><span>切换双语对照</span></div>
    <div class="term-row"><b>S</b><span>AI 总结</span></div>
    <div class="term-row"><b>C</b><span>打开 AI 对话</span></div>
    <div class="term-row"><b>D</b><span>打开词典</span></div>
    <div class="term-row"><b>F</b><span>专注阅读</span></div>
    <div class="term-row"><b>Space</b><span>复习时显示答案</span></div>
    <div class="term-row"><b>1 – 4</b><span>复习评分</span></div>
    <div class="term-row"><b>Esc</b><span>关闭弹窗 / 收起选择菜单</span></div>
    <div class="term-row"><b>?</b><span>打开这个面板</span></div>`);
}

function showOnboarding() {
  openModal(`
    <div class="modal-head"><h2>欢迎使用 Folio</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">一个本地优先的英文阅读工作台：读论文、查词、问 AI、背生词，全在一个窗口里。</p>
    <div class="sum-card"><div class="sum-label">1 · 导入 PDF</div><div class="sum-value">把英文论文拖进窗口，自动建立文献库、提取标题/年份/DOI。</div></div>
    <div class="sum-card"><div class="sum-label">2 · 连接 AI</div><div class="sum-value">设置里填 DeepSeek API Key，或用本地 Ollama；词典和 PDF 不需要联网。</div></div>
    <div class="sum-card"><div class="sum-label">3 · 开始读</div><div class="sum-value">划词查词典、划句问 AI、整页翻译、自动总结、加入生词本，按 FSRS 复习。</div></div>
    <div class="modal-actions"><button class="ghost" data-action="onboard-skip">先看看</button><button class="primary" data-action="upload">导入第一篇 PDF</button></div>`);
}

/* --------------------------------------------------------------- actions */
async function handleAction(action, element, event) {
  if (event) event.preventDefault();
  switch (action) {
    case "upload": closeModal(); $("#fileInput").click(); break;
    case "upload-folder": closeModal(); $("#folderInput").click(); break;
    case "web-import-modal": openWebImportModal(); break;
    case "web-import": await importWebArticle(); break;
    case "compare-modal": await openCompareModal(); break;
    case "run-compare": await runCompare(); break;
    case "zotero-modal": openZoteroModal(); break;
    case "zotero-load": await loadZoteroItems(); break;
    case "zotero-import": await importZoteroItems(); break;
    case "zotero-metadata-import": await importZoteroMetadata(); break;
    case "add-topic": openTopicModal(); break;
    case "save-topic": await createTopic(); break;
    case "view-topic": await viewTopic(Number(element.dataset.id)); break;
    case "refresh-topic": await refreshTopic(Number(element.dataset.id)); break;
    case "delete-topic": await deleteTopic(Number(element.dataset.id)); break;
    case "refresh-due-topics": await refreshDueTopics(); break;
    case "notifications-read-all": await api("/api/notifications/read-all", { method: "POST" }); await loadNotifications(); openNotificationsModal(); break;
    case "notification-open": await openNotification(Number(element.dataset.id), element.dataset.link || ""); break;
    case "annual-report": await openAnnualReport(); break;
    case "download-report": downloadAnnualReport(); break;
    case "compare-download": downloadCompareMarkdown(); break;
    case "compare-print": printCompareMarkdown(); break;
    case "writing-modal": openWritingModal(); break;
    case "run-writing": await runWritingReview(); break;
    case "doc-export-menu": openDocExportMenu(); break;
    case "vocab-export-menu": openVocabExportMenu(); break;
    case "discover-search": await runDiscoverSearch(); break;
    case "agent-run": await runAgent(); break;
    case "discover-topic": {
      const input = $("#discoverQuery");
      if (input) { input.value = element.dataset.text; S.discover.query = element.dataset.text; input.focus(); }
      break;
    }
    case "import-paper": await importPaper(Number(element.dataset.index)); break;
    case "cite-paper": await copyPaperCitation(Number(element.dataset.index)); break;
    case "go-discover": await go("discover"); break;
    case "shortcuts": openShortcuts(); break;
    case "open-settings": openSettings(); break;
    case "backup": window.location.href = "/api/backup"; break;
    case "save-settings": await saveSettings(); break;
    case "test-ai": await testAI(); break;
    case "sync-test": await testSync(); break;
    case "sync-now": await runSync(); break;
    case "sync-conflicts": await openSyncConflicts(); break;
    case "resolve-sync-conflict": await resolveSyncConflict(Number(element.dataset.id), element.dataset.choice); break;
    case "go-library": await go("library"); break;
    case "library-more": openLibraryMoreMenu(); break;
    case "go-vocab": await go("vocab"); break;
    case "review-start": await go("review"); break;
    case "cet-open": await go("cet"); break;
    case "open-doc": await openDoc(Number(element.dataset.id), Number(element.dataset.page) || undefined); break;
    case "fav-doc": await toggleFavorite(Number(element.dataset.id)); break;
    case "delete-doc": await deleteCurrentDoc(); break;
    case "edit-doc": openDocEditModal(); break;
    case "research-tools": openResearchTools(); break;
    case "research-run": await runResearch(element.dataset.mode, element.dataset.label); break;
    case "epub-layout": openEpubLayoutModal(); break;
    case "apply-epub-layout": await applyEpubLayout(); break;
    case "save-doc-edit": await saveDocEdit(); break;
    case "enrich-doc": await enrichDoc(); break;
    case "cite-bibtex": await copyCitation("bibtex"); break;
    case "cite-ris": await copyCitation("ris"); break;
    case "export-md": if (S.doc) { closeModal(); window.location.href = `/api/documents/${S.doc.id}/export.md`; } break;
    case "export-md-obsidian": if (S.doc) { closeModal(); window.location.href = `/api/documents/${S.doc.id}/export.md?template=obsidian`; } break;
    case "export-md-notion": if (S.doc) { closeModal(); window.location.href = `/api/documents/${S.doc.id}/export.md?template=notion`; } break;
    case "export-md-logseq": if (S.doc) { closeModal(); window.location.href = `/api/documents/${S.doc.id}/export.md?template=logseq`; } break;
    case "export-md-highlights": if (S.doc) { closeModal(); window.location.href = `/api/documents/${S.doc.id}/export.md?template=highlights`; } break;
    case "export-highlights-menu": openHighlightsExportMenu(); break;
    case "export-all-highlights": closeModal(); window.location.href = "/api/export/highlights.md?template=obsidian"; break;
    case "export-all-highlights-notion": closeModal(); window.location.href = "/api/export/highlights.md?template=notion"; break;
    case "export-all-highlights-logseq": closeModal(); window.location.href = "/api/export/highlights.md?template=logseq"; break;
    case "summary-open": closeModal(); setPanel(true, "summary"); break;
    case "panel-chat": closeModal(); setPanel(true, "chat"); break;
    case "panel-dict": closeModal(); setPanel(true, "dict"); break;
    case "ocr-start": closeModal(); await startOCR(); break;
    case "bilingual-export": closeModal(); await startBilingualExport(); break;
    case "rail-search":
      closeModal();
      S.railTab = "search";
      S.railCollapsed = false;
      $("#readerView").classList.remove("rail-hidden");
      renderRail();
      $("#railSearchInput")?.focus();
      break;
    case "add-collection": openCollectionModal(); break;
    case "lib-filter": setLibraryFilter(element.dataset.filter); break;
    case "lib-reset":
      S.library.author = ""; S.library.venue = ""; S.library.yearFrom = ""; S.library.yearTo = "";
      await renderLibrary();
      break;
    case "filter-collection": S.library.collection = Number(element.dataset.id) || null; S.library.favorite = false; S.library.status = ""; renderCollections(); await refreshLibrary(); break;
    case "lookup-selection": lookupWord(S.selection?.lookup || S.selection?.word || S.selection?.text, S.selection?.context, { modal: true }); break;
    case "ai-selection-word": openWordModal(S.selection?.lookup || S.selection?.word, S.selection?.context, true); break;
    case "add-selection-vocab": await addVocab(S.selection?.lookup || S.selection?.word || S.selection?.text, S.selection?.context); break;
    case "translate-selection": openSelectionModal(S.selection?.text, "translate"); break;
    case "explain-selection": openSelectionModal(S.selection?.text, "explain_en"); break;
    case "simplify-selection": openSelectionModal(S.selection?.text, "simplify"); break;
    case "grammar-selection": openSelectionModal(S.selection?.text, "grammar"); break;
    case "ask-selection": setPanel(true, "chat"); sendChat(`请解释这段内容：\n\n${S.selection?.text}`); break;
    case "hl": await addHighlight(element.dataset.color); break;
    case "speak": speak(element.dataset.text); break;
    case "open-word": openWordModal(element.dataset.word, element.dataset.context || ""); break;
    case "add-vocab": await addVocab(element.dataset.word, S.currentWord?.context || ""); break;
    case "ai-word": await aiWord(element.dataset.word, S.currentWord?.context || "", Boolean($("#wordModalBody"))); break;
    case "retranslate-page": S.bilingual = null; await translatePage(true); break;
    case "translate-page": await translatePage(false); break;
    case "translate-all": await translateFullDoc(); break;
    case "summarize": await summarizeDoc(); break;
    case "keypoints": await autoKeypoints(); break;
    case "chat-suggest": setPanel(true, "chat"); sendChat(element.dataset.text); break;
    case "clear-chat": if (S.doc) { await api(`/api/chat/${S.doc.id}`, { method: "DELETE" }); S.chat = []; renderChatPanel(); } break;
    case "add-note": await addNote(); break;
    case "edit-note": editNoteModal(Number(element.dataset.id)); break;
    case "save-note-edit": await saveNoteEdit(Number(element.dataset.id)); break;
    case "delete-note": await api(`/api/notes/${element.dataset.id}`, { method: "DELETE" }); S.notes = await api(`/api/notes/${S.doc.id}`); renderMarksPanel(); break;
    case "delete-highlight": await api(`/api/highlights/${element.dataset.id}`, { method: "DELETE" }); S.highlights = S.highlights.filter((item) => item.id !== Number(element.dataset.id)); renderHighlights(); renderMarksPanel(); break;
    case "goto-page": goPage(Number(element.dataset.page)); break;
    case "filter-marks": S.markFilter = element.dataset.color || null; renderMarksPanel(); break;
    case "mark-note": openMarkNoteModal(Number(element.dataset.id)); break;
    case "save-mark-note": await saveMarkNote(Number(element.dataset.id)); break;
    case "vocab-export": window.location.href = "/api/vocab/export.csv"; break;
    case "vocab-export-anki": window.location.href = "/api/vocab/export.apkg"; break;
    case "vocab-filter": filterVocabBy(element.dataset.filter); break;
    case "delete-vocab": await deleteVocab(Number(element.dataset.id)); break;
    case "review-word": startReviewForWord(Number(element.dataset.id)); break;
    case "review-mode":
      S.review.mode = element.dataset.mode;
      S.review.index = 0;
      S.review.highlightIndex = 0;
      S.review.revealed = false;
      renderReviewCard();
      break;
    case "reveal": S.review.revealed = true; renderReviewCard(); break;
    case "rate": await rateWord(Number(element.dataset.rating)); break;
    case "rate-highlight": await rateHighlight(Number(element.dataset.rating)); break;
    case "cet-analyze": await analyzeCET(); break;
    case "cet-save": await saveCETArticle(); break;
    case "open-article": await openArticle(Number(element.dataset.id)); break;
    case "delete-article":
      if (confirm("删除这篇保存的文章？")) {
        await api(`/api/articles/${element.dataset.id}`, { method: "DELETE" });
        toast("文章已删除");
        await renderCET();
      }
      break;
    case "quiz-generate": await generateQuiz(); break;
    case "quiz-option": {
      const index = Number(element.dataset.index); const option = Number(element.dataset.option);
      if (!S.cet.submitted) { S.cet.answers[index] = option; $("#quizArea").innerHTML = quizHtml(); }
      break;
    }
    case "quiz-submit": submitQuiz(); break;
    case "onboard-skip": localStorage.setItem("folio-onboarded", "1"); S.onboarded = true; closeModal(); break;
    case "close-modal": closeModal(); break;
    case "storage-pick": await pickStorageFolder(); break;
    case "storage-save": await saveStorageLocation(); break;
    case "storage-default": await saveStorageLocation(S.storage?.default_dir); break;
    case "storage-change": showStorageSetup(S.storage, false); break;
    case "mistake-new": openMistakeForm(); break;
    case "mistake-edit": {
      const mistake = (S.mistakes || []).find((entry) => entry.id === Number(element.dataset.id));
      if (mistake) openMistakeForm(mistake);
      break;
    }
    case "mistake-delete": await deleteMistake(Number(element.dataset.id)); break;
    case "mistake-save": await saveMistake(); break;
    case "mistake-filter":
      S.mistakeType = element.dataset.type || "";
      $$("#mistakeFilters .chip").forEach((chip) => chip.classList.toggle("active", chip.dataset.type === S.mistakeType));
      await refreshMistakes();
      break;
    case "mistake-from-solve": mistakeFromSolve(); break;
    case "solve-question": await openSolveQuestionModal(S.selection?.text || "", S.selection?.context || ""); break;
    case "question-solver-modal": openQuestionSolverModal(); break;
    case "solve-question-text": await openSolveQuestionModal($("#solveQuestionText")?.value || "", S.pageText || ""); break;
    case "copy-text": await navigator.clipboard.writeText(element.dataset.text || ""); toast("已复制"); break;
    case "save-selection-note": {
      if (!S.doc || S.view !== "reader") break;
      await api("/api/notes", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ doc_id: S.doc.id, page: S.page, content: element.dataset.text || "", title: element.dataset.title || "AI 解释" }) });
      S.notes = await api(`/api/notes/${S.doc.id}`);
      closeModal(); toast("已加入笔记"); break;
    }
    default: break;
  }
}

function setLibraryFilter(filter) {
  S.library.favorite = filter === "favorite";
  S.library.status = ["unread", "reading", "finished"].includes(filter) ? filter : "";
  S.library.collection = null;
  renderCollections();
  refreshLibrary();
  $$("#libFilters .chip").forEach((chip) => chip.classList.toggle("active", chip.dataset.filter === filter));
}

function filterVocabBy(filter) {
  $$("#vocabFilters .chip").forEach((chip) => chip.classList.toggle("active", chip.dataset.filter === filter));
  const rows = S.vocabList.filter((item) => {
    if (filter === "all") return true;
    if (filter === "due") return isDue(item) && !item.mastered;
    if (filter === "mastered") return item.mastered;
    return (item.tag || "").split(/\s+/).includes(filter);
  });
  $("#vocabRows").innerHTML = rows.map((item) => vocabRow(item)).join("") || '<div class="panel-empty">没有匹配的生词。</div>';
}

/* --------------------------------------------------------------- collection modal */
async function openCompareModal() {
  let docs = S.docs;
  try { docs = await api("/api/documents?sort=title"); } catch { /* use current */ }
  if (docs.length < 2) {
    openModal(`<div class="modal-head"><h2>文献对比</h2><button class="icon" data-close-modal>${icon("x")}</button></div><div class="panel-empty">至少需要 2 篇文献。</div>`);
    return;
  }
  openModal(`
    <div class="modal-head"><h2>文献对比</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">选 2–6 篇，AI 会按研究问题、方法、数据、结果、创新、局限做一张对比表，并给阅读顺序。</p>
    <div style="max-height:320px;overflow:auto">
      ${docs.map((doc) => `<label class="zotero-item"><input type="checkbox" data-compare-key="${doc.id}"><span style="flex:1;min-width:0"><b>${escapeHtml(doc.title)}</b><span class="faint" style="font-size:10.5px">${escapeHtml(doc.authors || "未填写作者")}${doc.year ? ` · ${doc.year}` : ""}</span></span></label>`).join("")}
    </div>
    <div class="modal-actions"><button class="ghost" data-close-modal>取消</button><button class="primary" data-action="run-compare">生成对比</button></div>
    <div id="compareResult"></div>`, { wide: true });
}

async function runCompare() {
  const ids = $$("[data-compare-key]:checked").map((input) => Number(input.dataset.compareKey));
  if (ids.length < 2) { toast("至少选 2 篇文献", "error"); return; }
  if (ids.length > 6) { toast("最多选 6 篇文献", "error"); return; }
  $("#compareResult").innerHTML = loadingHtml("AI 正在读这几篇文献并做对比…");
  try {
    const data = await api("/api/ai/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_ids: ids }),
    });
    S.compareMarkdown = data.markdown;
    $("#compareResult").innerHTML = `<div class="md" style="margin-top:16px">${mdToHtml(data.markdown)}</div>
      <div class="modal-actions">
        <button class="ghost" data-action="compare-download">${icon("download")}下载 Markdown</button>
        <button class="ghost" data-action="compare-print">${icon("summary")}打印 / 存为 PDF</button>
        <button class="ghost" data-action="copy-text" data-text="${escapeAttr(data.markdown)}">${icon("copy")}复制</button>
      </div>`;
  } catch (error) {
    $("#compareResult").innerHTML = errorHtml(error.message);
  }
}

function downloadCompareMarkdown() {
  if (!S.compareMarkdown) return;
  const blob = new Blob([S.compareMarkdown], { type: "text/markdown;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "folio-compare.md";
  link.click();
  URL.revokeObjectURL(link.href);
}

function printCompareMarkdown() {
  if (!S.compareMarkdown) return;
  const win = window.open("", "_blank");
  if (!win) { toast("浏览器拦截了新窗口，请允许弹窗", "error"); return; }
  win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>文献对比</title>
    <style>
      body{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;color:#1d1d1f;max-width:900px;margin:32px auto;padding:0 24px;line-height:1.7;}
      h1{font-size:24px;} h3{font-size:15px;margin-top:22px;}
      table{border-collapse:collapse;width:100%;font-size:12px;margin:12px 0;}
      th,td{border:1px solid #d5d5da;padding:7px 9px;text-align:left;vertical-align:top;}
      th{background:#f2f2f7;}
      @media print{body{margin:0;padding:0;} .no-print{display:none;}}
    </style></head><body><h1>文献对比</h1>${mdToHtml(S.compareMarkdown)}</body></html>`);
  win.document.close();
  win.focus();
  setTimeout(() => win.print(), 400);
}

async function openZoteroModal() {
  openModal(`
    <div class="modal-head"><h2>导入 Zotero</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">可以从 Zotero 7 本地 API 读取条目和 PDF，也可以粘贴 Zotero 导出的 CSL JSON / BibTeX。</p>
    <div class="sum-card" id="zoteroStatus">${loadingHtml("检查 Zotero 本地 API…")}</div>
    <div class="dict-actions" style="margin-top:0">
      <button class="primary" data-action="zotero-load">${icon("refresh")}读取 Zotero 条目</button>
    </div>
    <div id="zoteroList"></div>
    <div class="panel-section-title" style="margin-top:18px">从文件 / 剪贴板导入元数据</div>
    <div class="row" style="margin-top:0">
      <select id="zoteroMetaFormat" class="sort-select"><option value="csl">CSL JSON</option><option value="bibtex">BibTeX</option></select>
      <button class="ghost" data-action="zotero-metadata-import">${icon("download")}导入元数据</button>
    </div>
    <textarea id="zoteroMetaText" placeholder="把 Zotero 导出的 CSL JSON 或 BibTeX 粘贴到这里…" style="width:100%;min-height:100px;margin-top:8px"></textarea>
    <div class="hint" style="margin-top:10px">Zotero 本地 API：设置 → 高级 → 勾选「允许其他应用程序与本机 Zotero 通信」。没有 PDF 的条目会生成一页摘要占位文献。</div>`, { wide: true });
  try {
    const status = await api("/api/zotero/status");
    $("#zoteroStatus").innerHTML = `<div class="sum-label">Zotero 本地 API</div><div class="sum-value">${status.available ? "已连接" : "未连接"} · ${escapeHtml(status.message)}</div><div class="faint" style="font-size:10.5px;margin-top:4px">${escapeHtml(status.url)}</div>`;
  } catch (error) {
    $("#zoteroStatus").innerHTML = errorHtml(error.message);
  }
}

async function loadZoteroItems() {
  const box = $("#zoteroList");
  box.innerHTML = loadingHtml("读取 Zotero 条目…");
  try {
    const data = await api("/api/zotero/items?limit=60");
    const items = data.items || [];
    if (!items.length) {
      box.innerHTML = '<div class="panel-empty">Zotero 里没有可导入的条目。</div>';
      return;
    }
    box.innerHTML = `<div class="panel-section-title">${items.length} 个条目</div>
      ${items.map((item) => `
        <label class="zotero-item">
          <input type="checkbox" data-zotero-key="${escapeAttr(item.key)}" ${item.has_pdf ? "checked" : ""}>
          <span style="flex:1;min-width:0">
            <b>${escapeHtml(item.title)}</b>
            <span class="faint" style="font-size:10.5px">${escapeHtml(item.authors || "未填写作者")}${item.year ? ` · ${item.year}` : ""}${item.venue ? ` · ${escapeHtml(item.venue)}` : ""}</span>
          </span>
          <span class="tag ${item.has_pdf ? "cet6" : ""}">${item.has_pdf ? "PDF" : "无 PDF"}</span>
        </label>`).join("")}
      <div class="dict-actions"><button class="primary" data-action="zotero-import">${icon("download")}导入选中条目</button></div>`;
  } catch (error) {
    box.innerHTML = errorHtml(error.message);
  }
}

async function importZoteroItems() {
  const keys = $$("[data-zotero-key]:checked").map((input) => input.dataset.zoteroKey);
  if (!keys.length) { toast("先选几个条目", "error"); return; }
  const box = $("#zoteroList");
  box.innerHTML = loadingHtml(`正在导入 ${keys.length} 个条目…`);
  try {
    const data = await api("/api/zotero/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keys }),
    });
    const imported = data.imported || [];
    if (!imported.length) {
      box.innerHTML = errorHtml((data.errors?.[0]?.message) || "没有导入任何条目。");
      return;
    }
    await Promise.all([loadCollections(), loadVocabCache()]);
    closeModal();
    toast(`已导入 ${imported.length} 个条目`);
    await openDoc(imported[0].id);
  } catch (error) {
    box.innerHTML = errorHtml(error.message);
  }
}

async function importZoteroMetadata() {
  const text = $("#zoteroMetaText")?.value.trim() || "";
  const format = $("#zoteroMetaFormat")?.value || "csl";
  if (!text) { toast("先粘贴 CSL JSON 或 BibTeX", "error"); return; }
  const box = $("#zoteroList");
  box.innerHTML = loadingHtml("正在解析并生成条目…");
  try {
    const data = await api("/api/zotero/import-metadata", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format, text }),
    });
    const imported = (data.imported || []).filter((item) => item.id);
    if (!imported.length) {
      box.innerHTML = errorHtml("没有解析到可导入的条目。");
      return;
    }
    closeModal();
    toast(`已导入 ${imported.length} 个条目`);
    await openDoc(imported[0].id);
  } catch (error) {
    box.innerHTML = errorHtml(error.message);
  }
}

function openWebImportModal() {
  openModal(`
    <div class="modal-head"><h2>导入网页文章</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">抓取网页正文，生成可划词、可翻译、可总结的 PDF。适合外刊、博客、新闻和四六级阅读材料。</p>
    <label>网址<input id="webUrl" placeholder="https://..." autofocus></label>
    <label>标题（可选）<input id="webTitle" placeholder="留空则自动识别"></label>
    <div id="webImportStatus"></div>
    <div class="modal-actions"><button class="ghost" data-close-modal>取消</button><button class="primary" data-action="web-import">导入</button></div>`);
  $("#webUrl").focus();
}

async function importWebArticle() {
  const url = $("#webUrl")?.value.trim() || "";
  if (!url) { toast("请输入网址", "error"); return; }
  $("#webImportStatus").innerHTML = loadingHtml("正在抓取并提取正文…");
  try {
    const result = await api("/api/web/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, title: $("#webTitle")?.value.trim() || "" }),
    });
    await Promise.all([loadCollections(), loadVocabCache()]);
    closeModal();
    toast("网页已导入");
    await openDoc(result.id);
  } catch (error) {
    $("#webImportStatus").innerHTML = errorHtml(error.message);
  }
}

function openCollectionModal() {
  const colors = ["#0071e3", "#34c759", "#ff9500", "#ff2d55", "#af52de", "#00c7be"];
  openModal(`
    <div class="modal-head"><h2>新建分类</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <label>分类名<input id="collectionName" placeholder="例如：遥感论文 / 四六级真题"></label>
    <label>颜色<div class="color-choices" id="collectionColors">${colors.map((color, index) => `<button class="color-choice ${index === 0 ? "active" : ""}" data-color="${color}" style="background:${color}"></button>`).join("")}</div></label>
    <div class="modal-actions"><button class="ghost" data-close-modal>取消</button><button class="primary" data-action="save-collection">创建</button></div>`);
  $$("#collectionColors .color-choice").forEach((button) => button.addEventListener("click", () => {
    $$("#collectionColors .color-choice").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
  }));
  $("#collectionName").focus();
}

async function saveCollection() {
  const name = $("#collectionName")?.value.trim();
  const color = $("#collectionColors .color-choice.active")?.dataset.color || "#0071e3";
  if (!name) { toast("分类名不能为空", "error"); return; }
  try {
    await api("/api/collections", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, color }) });
    closeModal();
    await loadCollections();
    toast("分类已创建");
  } catch (error) { toast(error.message, "error"); }
}

/* ------------------------------------------------------------- translate all */
async function startBilingualExport() {
  if (!S.doc) return;
  openModal(`
    <div class="modal-head"><h2>导出双语 PDF</h2><button class="icon" data-close-modal>${icon("x")}</button></div>
    <p class="modal-note">左侧保留原页面，右侧是逐页中文译文。未翻译的页面会自动调用 AI 翻译；页数多时需要几分钟。</p>
    <div id="bilingualExportBody">${loadingHtml("正在准备导出…")}</div>`);
  try {
    const job = await api(`/api/documents/${S.doc.id}/bilingual/start`, { method: "POST" });
    renderBilingualExport(job);
    pollBilingualExport();
  } catch (error) {
    $("#bilingualExportBody").innerHTML = errorHtml(error.message);
  }
}

function renderBilingualExport(job) {
  const body = $("#bilingualExportBody");
  if (!body) return;
  if (job.status === "done") {
    body.innerHTML = `<div class="sum-card"><div class="sum-label">导出完成</div><div class="sum-value">共 ${job.total} 页，左侧原页 + 右侧译文。</div></div>
      <a class="primary" style="display:inline-flex" href="/api/documents/${S.doc.id}/bilingual.pdf" download>${icon("download")}下载双语 PDF</a>`;
    return;
  }
  if (job.status === "error") {
    body.innerHTML = errorHtml(job.message || "导出失败");
    return;
  }
  const percent = job.total ? Math.round((job.done / job.total) * 100) : 0;
  body.innerHTML = `${loadingHtml(job.status === "queued" ? "排队中…" : "正在逐页翻译并排版…")}
    <div class="progress-track" style="margin:8px 0"><div class="progress-fill" style="width:${percent}%"></div></div>
    <div class="faint" style="font-size:11px">${job.done} / ${job.total} 页</div>`;
}

function pollBilingualExport() {
  if (!S.doc) return;
  setTimeout(async () => {
    try {
      const job = await api(`/api/documents/${S.doc.id}/bilingual/status`);
      renderBilingualExport(job);
      if (job.status === "queued" || job.status === "running") pollBilingualExport();
    } catch (error) {
      const body = $("#bilingualExportBody");
      if (body) body.innerHTML = errorHtml(error.message);
    }
  }, 1500);
}

async function translateFullDoc() {
  if (!S.doc) return;
  setPanel(true, "translate");
  $("#panelBody").innerHTML = loadingHtml("AI 正在翻译全文，长文献可能需要 1–2 分钟…");
  try {
    const data = await api("/api/ai/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_id: S.doc.id }),
    });
    S.fullTranslation = data.markdown;
    renderTranslatePanel();
  } catch (error) { $("#panelBody").innerHTML = errorHtml(error.message); }
}

/* ------------------------------------------------------------------ events */
function wireEvents() {
  document.addEventListener("click", async (event) => {
    if (!(event.target instanceof Element)) return;
    const nav = event.target.closest(".nav-link[data-view]");
    if (nav) { await go(nav.dataset.view); return; }
    const panelTab = event.target.closest(".panel-tab[data-tab]");
    if (panelTab) { S.panelTab = panelTab.dataset.tab; renderPanel(); return; }
    const railTab = event.target.closest(".rail-tab[data-rail]");
    if (railTab) { S.railTab = railTab.dataset.rail; renderRail(); return; }
    const delCollection = event.target.closest("[data-del-collection]");
    if (delCollection) {
      event.stopPropagation();
      if (confirm("删除这个分类？文献不会被删除，只会回到未分类。")) {
        try {
          await api(`/api/collections/${delCollection.dataset.delCollection}`, { method: "DELETE" });
          if (S.library.collection === Number(delCollection.dataset.delCollection)) S.library.collection = null;
          await loadCollections();
          renderCollections();
          if (S.view === "library") await refreshLibrary();
        } catch (error) { toast(error.message, "error"); }
      }
      return;
    }
    const collection = event.target.closest("[data-collection]");
    if (collection) { S.library.collection = Number(collection.dataset.collection); S.library.favorite = false; S.library.status = ""; S.library.q = ""; renderCollections(); if (S.view !== "library") await go("library"); else await refreshLibrary(); return; }
    const quickTag = event.target.closest(".chip[data-tag]");
    if (quickTag) { await go("vocab"); filterVocabBy(quickTag.dataset.tag); return; }
    const actionEl = event.target.closest("[data-action]");
    if (actionEl) { await handleAction(actionEl.dataset.action, actionEl, event); return; }
    const pageEl = event.target.closest("[data-page]");
    if (pageEl) { goPage(Number(pageEl.dataset.page)); }
  });

  document.addEventListener("mouseup", (event) => {
    if (!(event.target instanceof Element)) return;
    if (S.view !== "reader" || !S.doc || S.mode !== "page") return;
    if (event.target.closest("#selectionPopup") || event.target.closest("#panel") || event.target.closest("#sidebar") || event.target.closest("#topbar")) return;
    setTimeout(captureSelection, 10);
  });

  document.addEventListener("mousedown", (event) => {
    if (!(event.target instanceof Element)) return;
    if (!event.target.closest("#selectionPopup")) hidePopup();
  });

  $("#fileInput").addEventListener("change", (event) => { uploadFiles(event.target.files); event.target.value = ""; });
  $("#folderInput").addEventListener("change", (event) => { uploadFiles(event.target.files); event.target.value = ""; });
  $("#collapseSidebar").addEventListener("click", () => $("#app").classList.toggle("sidebar-collapsed"));
  $("#themeBtn").addEventListener("click", cycleTheme);
  $("#settingsBtn").addEventListener("click", openSettings);
  $("#notifyBtn").addEventListener("click", openNotificationsModal);
  $("#closePanel").addEventListener("click", () => setPanel(false));
  $("#addCollection").addEventListener("click", openCollectionModal);
  $("#modalRoot").addEventListener("click", (event) => {
    const saveCollectionButton = event.target.closest('[data-action="save-collection"]');
    if (saveCollectionButton) { event.preventDefault(); saveCollection(); }
  });

  const reader = $("#readerStage");
  ["dragenter", "dragover"].forEach((name) => reader.addEventListener(name, (event) => event.preventDefault()));
  reader.addEventListener("drop", (event) => { event.preventDefault(); uploadFiles(event.dataTransfer.files); });

  document.addEventListener("keydown", (event) => {
    if (event.target.matches("input, textarea, select")) return;
    if (event.key === "Escape") { if (S.storageRequired) return; hidePopup(); closeModal(); return; }
    if (event.key === "?" && !event.metaKey && !event.ctrlKey) { openShortcuts(); return; }
    if (S.view === "review") {
      if (S.review.mode === "highlight") {
        if (["1", "2", "3", "4"].includes(event.key)) { event.preventDefault(); rateHighlight(Number(event.key)); return; }
      } else {
        if (event.key === " " && !S.review.revealed) { event.preventDefault(); S.review.revealed = true; renderReviewCard(); return; }
        if (["1", "2", "3", "4"].includes(event.key) && S.review.revealed) { event.preventDefault(); rateWord(Number(event.key)); return; }
      }
    }
    if (S.view === "reader" && S.doc) {
      const selection = window.getSelection();
      if (selection && !selection.isCollapsed) return;
      if (event.key === "ArrowLeft") { event.preventDefault(); goPage(S.page - 1); }
      else if (event.key === "ArrowRight") { event.preventDefault(); goPage(S.page + 1); }
      else if (event.key.toLowerCase() === "b") { $("#modeBtn")?.click(); }
      else if (event.key.toLowerCase() === "s") { summarizeDoc(); }
      else if (event.key.toLowerCase() === "c") { setPanel(true, "chat"); }
      else if (event.key.toLowerCase() === "d") { setPanel(true, "dict"); }
      else if (event.key.toLowerCase() === "f") { toggleFocusMode(); }
    }
  });

  window.addEventListener("beforeunload", () => {
    if (S.view === "reader" && S.doc) {
      const seconds = Math.max(0, Math.round((Date.now() - S.readingStarted) / 1000));
      navigator.sendBeacon(`/api/documents/${S.doc.id}/progress?page=${S.page}&seconds=${seconds}`);
    }
  });

  setInterval(() => { if (S.view === "reader" && S.doc) flushProgress(); }, 45000);
  setInterval(() => loadNotifications(), 60000);

  window.addEventListener("hashchange", async () => {
    const hash = location.hash.replace("#", "");
    if (hash.startsWith("reader/")) {
      const id = Number(hash.split("/")[1]);
      if (id && (!S.doc || S.doc.id !== id)) await openDoc(id);
    } else if (VIEW_IDS[hash] && S.view !== hash) {
      await go(hash);
    }
  });
}

/* -------------------------------------------------------------------- init */
(async function init() {
  applyTheme(S.theme, false);
  hydrateIcons();
  wireEvents();
  try {
    const storage = await api("/api/storage/status");
    S.storage = storage;
    if (!storage.configured) {
      showStorageSetup(storage, true);
      return;
    }
  } catch (error) {
    toast(`资料库状态读取失败：${error.message}`, "error");
  }
  await Promise.all([loadCollections(), loadVocabCache(), loadDue(), loadSettings(), loadNotifications(), loadMistakeCount()]);
  const hash = location.hash.replace("#", "");
  if (hash.startsWith("reader/")) {
    const id = Number(hash.split("/")[1]);
    if (id) { await openDoc(id); return; }
  }
  if (["home", "library", "discover", "cet", "vocab", "mistakes", "review", "stats"].includes(hash)) await go(hash);
  else await go("home");
  if (!S.onboarded) setTimeout(showOnboarding, 700);
})();

window.Folio = { S, api, go, openDoc };
