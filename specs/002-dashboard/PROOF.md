# Dashboard — proof of behavior

Recorded 2026-06-16. Server started on `127.0.0.1:8787` via the preview tool
(`.venv/bin/python -m dashboard.server`).

## Gate (deterministic)
`/.venv/bin/python -m pytest dashboard/tests -q` → **13 passed**. Covers:
- read-only (no mutating routes; no LLM/orchestrator-dispatch import; no disk writes),
- localhost (binds 127.0.0.1, never 0.0.0.0),
- graceful degradation (runstate/usage absent → 200, panels 5/6 pending).

## Endpoints (curl, localhost)
- `GET /` → 200; `/api/{health,topology,sprint,governance,timeline,runstate,budget}` → all 200.
- `POST /api/health` → **501** (no mutating method implemented). Read-only confirmed.

## Panels 1–4 render from the repo's real files
- **Topology** (from `governance/*.md`, data-driven): Operator (no model) → Orchestrator
  (**Claude Sonnet**, Anthropic/Claude) → Worker (**gpt-5.5**, OpenAI/Codex, writes `gate/`)
  → Independent verification (no model — role reserved). Providers: OpenAI/Codex (floor
  gpt-5.5), Gemini, Grok, Anthropic/Claude (floor Opus).
- **Sprint** (from `specs/002-dashboard/tasks.md`): "10/16 tasks · 002-dashboard", phases
  with done/pending ticks, progress bar.
- **Governance** (from `governance/`): always-human = Security-sensitive, Bulk deletes,
  Git/GitHub history or log-history modification; escalate list; model floors; stop at 15%.
- **Timeline** (`git log` + optional ntfy): commits plus **17 live events** from topic
  `Mahdi-Dev` (degrades to git-only if unreachable; topic read from config, not hardcoded).

## Panels 5–6 degrade gracefully (stub now)
From the running page (`preview_eval`, stores absent):
- runstate → `⏳ pending … lands in: the runtime sprint (runstate writer not built yet)
  reads .magrathea/runstate.json`
- budget → `▱ pending … lands in: the usage-adapter sprint … reads .magrathea/usage.json`

## Responsive (operator checks from a phone)
At **375 px** (mobile, dark): `document.documentElement.scrollWidth == window.innerWidth
== 375` → **no horizontal scroll**; panels reflow to a single column; header fits one line
(sprint chip collapses < 480 px). At ≥ 680 px: two-column grid, topology/timeline span full
width. Dark and light supported via `prefers-color-scheme`.
