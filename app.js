"use strict";

const SEARCH_URL = "https://learning.oreilly.com/search/?type=live-course&rows=100&language=en&q=";
const $ = id => document.getElementById(id);
const state = { entries: [], domains: new Set(), tags: new Set(), q: "", sort: "received_desc" };

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

function fmtDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
  if (!m) return iso || "—";
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return isNaN(d) ? iso : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function highlight(text, q) {
  const safe = esc(text);
  if (!q) return safe;
  return safe.replace(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "ig"), "<mark>$1</mark>");
}

function counts(entries, key, where) {
  const c = {};
  for (const e of entries) {
    if (where && !where(e)) continue;
    for (const v of e[key] || []) c[v] = (c[v] || 0) + 1;
  }
  return Object.entries(c).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

function chip(name, n, cls, onClick, active) {
  const el = document.createElement("span");
  el.className = `chip ${cls}${active ? " active" : ""}`;
  el.innerHTML = `${esc(name)}<span class="count">${n}</span>`;
  el.addEventListener("click", onClick);
  return el;
}

function renderFilters() {
  const dBar = $("domainBar");
  dBar.replaceChildren();
  for (const [n, k] of counts(state.entries, "domains")) {
    dBar.append(chip(n, k, "domain", () => {
      state.domains.has(n) ? state.domains.delete(n) : state.domains.add(n);
      const valid = new Set(counts(state.entries, "tags", e => !state.domains.size || (e.domains || []).some(d => state.domains.has(d))).map(([t]) => t));
      for (const t of [...state.tags]) if (!valid.has(t)) state.tags.delete(t);
      renderFilters(); render();
    }, state.domains.has(n)));
  }
  const subRow = $("subTagRow");
  const tBar = $("tagBar");
  tBar.replaceChildren();
  if (!state.domains.size) { subRow.hidden = true; return; }
  subRow.hidden = false;
  for (const [n, k] of counts(state.entries, "tags", e => (e.domains || []).some(d => state.domains.has(d)))) {
    tBar.append(chip(n, k, "tag", () => {
      state.tags.has(n) ? state.tags.delete(n) : state.tags.add(n);
      renderFilters(); render();
    }, state.tags.has(n)));
  }
}

function applyFilters() {
  const q = state.q.trim().toLowerCase();
  const out = state.entries.filter(e => {
    if (state.domains.size && !(e.domains || []).some(d => state.domains.has(d))) return false;
    for (const t of state.tags) if (!(e.tags || []).includes(t)) return false;
    if (!q) return true;
    return [e.event, e.presenter, ...(e.tags || []), ...(e.domains || [])].join(" ").toLowerCase().includes(q);
  });
  const sorters = {
    received_asc:  (a, b) => (a.received || "").localeCompare(b.received || ""),
    received_desc: (a, b) => (b.received || "").localeCompare(a.received || ""),
    event_asc:     (a, b) => (a.event || "").localeCompare(b.event || ""),
    presenter_asc: (a, b) => (a.presenter || "").localeCompare(b.presenter || ""),
  };
  return out.sort(sorters[state.sort] || sorters.received_desc);
}

function render() {
  const items = applyFilters();
  const q = state.q.trim().toLowerCase();
  $("count").textContent = `${items.length} of ${state.entries.length}`;
  $("empty").classList.toggle("hidden", items.length > 0);

  const results = $("results");
  results.replaceChildren();
  const frag = document.createDocumentFragment();
  for (const e of items) {
    const card = document.createElement("article");
    card.className = "card";
    const url = SEARCH_URL + encodeURIComponent(e.event);
    const chips = [
      ...(e.domains || []).map(d => `<span class="tag-chip domain">${esc(d)}</span>`),
      ...(e.tags    || []).map(t => `<span class="tag-chip">${esc(t)}</span>`),
    ].join("");
    card.innerHTML = `
      <h2 class="event"><a href="${url}" target="_blank" rel="noopener" title="Search on O'Reilly Learning">${highlight(e.event, q)}</a></h2>
      <div class="presenter">👤 ${highlight(e.presenter || "Unknown presenter", q)}</div>
      <div class="date">📅 ${fmtDate(e.received)}</div>
      <div class="tags">${chips}</div>`;
    frag.append(card);
  }
  results.append(frag);
}

async function load() {
  let loadedFrom = "data/data.json";
  try {
    let r = await fetch(`data/data.json?t=${Date.now()}`, { cache: "no-store" });
    if (!r.ok) {
      // fall back to the bundled sample so the SPA works on a fresh clone
      r = await fetch(`data/data.sample.json?t=${Date.now()}`, { cache: "no-store" });
      loadedFrom = "data/data.sample.json";
    }
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    state.entries = await r.json();
  } catch (err) {
    $("meta").textContent = `failed to load data — ${err.message}`;
    return;
  }
  let meta = `${state.entries.length} unique recordings`;
  if (loadedFrom.endsWith("sample.json")) meta += " (sample data)";
  try {
    const sr = await fetch(`data/state.json?t=${Date.now()}`, { cache: "no-store" });
    if (sr.ok) {
      const s = await sr.json();
      const at = s.last_run_at ? new Date(s.last_run_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "—";
      meta += ` · last refresh: ${at} · latest email: ${fmtDate(s.last_run_iso)}`;
    }
  } catch {}
  $("meta").textContent = meta;
  renderFilters();
  render();
}

document.addEventListener("DOMContentLoaded", () => {
  $("search").addEventListener("input", debounce(e => { state.q = e.target.value; render(); }, 100));
  $("sort").addEventListener("change", e => { state.sort = e.target.value; render(); });
  $("clearTags").addEventListener("click", () => { state.domains.clear(); state.tags.clear(); renderFilters(); render(); });
  load();
});
