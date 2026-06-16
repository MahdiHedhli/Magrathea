"use strict";
// Read-only dashboard client: fetch /api/* and render. No writes, no model.

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function relTime(iso) {
  if (!iso) return "";
  const t = Date.parse(iso);
  if (isNaN(t)) return "";
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 60) return Math.floor(s) + "s";
  if (s < 3600) return Math.floor(s / 60) + "m";
  if (s < 86400) return Math.floor(s / 3600) + "h";
  return Math.floor(s / 86400) + "d";
}
const modelBadge = (m) => m
  ? `<span class="model-badge">${esc(m)}</span>`
  : `<span class="model-badge none">no model</span>`;

async function fetchJSON(path) {
  const r = await fetch(path, { headers: { "Accept": "application/json" } });
  if (!r.ok) throw new Error(path + " → " + r.status);
  return r.json();
}

const RENDER = {
  topology(d) {
    const arrow = `<div class="arrow">↓</div>`;
    const roles = d.roles.map((r) => `
      <div class="role">
        <span class="rk">${esc(r.role)}</span>
        <span class="rmodel">${modelBadge(r.model)}</span>
      </div>
      <div class="sub">${esc([r.provider, r.scope ? "writes " + r.scope : null, r.note].filter(Boolean).join(" · "))}</div>
    `).join(arrow);
    const provs = (d.providers || []).map((p) => `
      <span class="prov"><b>${esc(p.provider)}</b>${p.default_model ? " · " + esc(p.default_model) : ""}${p.floor ? " · floor " + esc(p.floor) : ""}</span>
    `).join("");
    return `<div class="flow">${roles}</div>
      ${provs ? `<div class="providers">${provs}</div>` : ""}`;
  },

  sprint(d) {
    const pct = d.total ? Math.round((d.done / d.total) * 100) : 0;
    const phases = (d.phases || []).map((ph) => `
      <div class="phase">
        <h3>${esc(ph.name)}</h3>
        ${ph.tasks.map((t) => `
          <div class="task ${t.done ? "done" : "todo"}">
            <span class="box">${t.done ? "✓" : "○"}</span>
            <span>${esc(t.text)}</span>
          </div>`).join("")}
      </div>`).join("");
    return `<div class="muted" style="font-size:.82rem">${d.done}/${d.total} tasks · ${esc(d.sprint)}</div>
      <div class="bar"><i style="width:${pct}%"></i></div>${phases}`;
  },

  governance(d) {
    const ah = (d.always_human || []).map((x) => `<span class="gchip">${esc(x)}</span>`).join("");
    const esc_ = (d.escalate_always || []).map((x) => `<span class="gchip soft">${esc(x)}</span>`).join("");
    const fl = (d.model_floors || []).map((f) => `<span class="floor">${esc(f.provider)} · <b>${esc(f.floor || "—")}</b></span>`).join("");
    return `
      <div class="glabel">Always human · never autonomous</div><div class="chips">${ah || "<span class='muted'>—</span>"}</div>
      <div class="glabel">Always escalate</div><div class="chips">${esc_ || "<span class='muted'>—</span>"}</div>
      <div class="glabel">Model floors</div><div class="floors">${fl || "<span class='muted'>—</span>"}</div>
      ${d.stop_threshold_pct != null ? `<div class="thr">Stop new work at <b>${d.stop_threshold_pct}%</b> remaining headroom</div>` : ""}`;
  },

  timeline(d) {
    let note = "";
    if (d.events_source === "ntfy") note = `reporting: <b>${esc(d.topic)}</b> · ${(d.events || []).length} events`;
    else if (d.events_source === "git-only") note = `reporting topic <b>${esc(d.topic || "?")}</b> unreachable · git-only`;
    else note = "no reporting topic configured · git-only";
    const events = (d.events || []).slice().reverse().map((e) => `
      <li class="evt"><span class="h">◆</span><span class="s">${esc(e.title || "")}<br><span class="when">${esc(e.message || "")}</span></span></li>`).join("");
    const commits = (d.commits || []).map((c) => `
      <li><span class="h">${esc(c.hash)}</span><span class="s">${esc(c.subject)}<br>
        <span class="when">${esc(c.author)} · ${esc(relTime(c.date))} ago</span></span></li>`).join("");
    return `<div class="events-note">${note}</div><ul class="tl">${events}${commits || "<li class='muted'>no commits</li>"}</ul>`;
  },

  runstate(d) {
    if (d.status === "pending") return pendingCard("Live tasks", d, "⏳");
    const inf = d.in_flight
      ? `<div class="role"><span class="rk">in flight</span><span class="rmodel">${modelBadge(d.in_flight.model)}</span></div>
         <div class="sub">${esc(d.in_flight.id)} · ${esc(d.in_flight.provider || "")} · thread ${esc((d.in_flight.thread_id || "").slice(0, 8))}</div>`
      : `<div class="muted">idle</div>`;
    const q = (d.task_queue || []).map((t) => `<div class="task ${t.status === "passed" ? "done" : "todo"}">
        <span class="box">${t.status === "passed" ? "✓" : "○"}</span><span>${esc(t.id)} · ${esc(t.status)}</span></div>`).join("");
    return `<div class="muted" style="font-size:.82rem">run ${esc(d.run_id || "")} · <b>${esc(d.status)}</b></div>${inf}${q}`;
  },

  budget(d) {
    if (d.status === "pending") return pendingCard("Budget &amp; limits", d, "▱");
    const provs = (d.providers || []).map((p) => `
      <div class="phase"><h3>${esc(p.provider)} · ${esc(p.adapter)}</h3>
        ${(p.windows || []).map((w) => `<div class="task"><span>${esc(w.window)}</span>
          <span class="rmodel">${w.remaining_pct == null ? "—" : w.remaining_pct + "%"}</span></div>`).join("")}</div>`).join("");
    return `<div class="thr">stop at <b>${esc(d.stop_threshold_pct)}%</b></div>${provs}`;
  },
};

function pendingCard(title, d, glyph) {
  return `<div class="pending">
    <div class="big">${glyph}</div>
    <div class="what">pending</div>
    <div class="lands">${esc(d.reason || "")}<br>lands in: ${esc(d.lands_in || "a later sprint")}<br>
    reads <code>${esc(d.reads || "")}</code></div></div>`;
}

async function loadPanel(section) {
  const name = section.dataset.panel;
  const body = $("[data-body]", section);
  const srcEl = $("[data-src]", section);
  try {
    const data = await fetchJSON("/api/" + name);
    body.innerHTML = RENDER[name](data);
    if (srcEl) {
      const s = data.sources || (data.source ? [data.source] : null);
      srcEl.textContent = s ? (Array.isArray(s) ? s.join(" · ") : s) : "";
    }
    return true;
  } catch (e) {
    body.innerHTML = `<div class="err">unavailable — ${esc(e.message)}</div>`;
    return false;
  }
}

async function refreshAll() {
  const btn = $("#refresh"); btn.classList.add("spin");
  try {
    const health = await fetchJSON("/api/health").catch(() => null);
    if (health) $("#sprint-chip").textContent = "sprint " + (health.sprint || "—");
  } catch (_) {}
  const results = await Promise.all(
    [...document.querySelectorAll(".panel")].map(loadPanel));
  const dot = $("#status-dot");
  const ok = results.every(Boolean);
  dot.className = "dot " + (ok ? "ok" : "bad");
  dot.title = "last refresh " + new Date().toLocaleTimeString();
  btn.classList.remove("spin");
}

document.getElementById("refresh").addEventListener("click", refreshAll);
refreshAll();
