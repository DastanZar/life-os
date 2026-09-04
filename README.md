# Body OS — a Life OS chart

Personal transformation tracker PWA: body, exercise, nutrition. Part of a larger
"Life OS" with separate charts for career/studies/finances (not in this repo yet).

**Live:** served from a VPS via Cloudflare tunnel (URL rotates) · **Install:**
open on Android Chrome → Add to Home Screen (full PWA, offline-first).

## What's inside

```
app/
  index.html            — the whole PWA (no build step, single file)
  server.py             — tiny backend: static files + /api/ask (LLM coach) + /api/memory
  sw.js                 — service worker (offline cache, bump CACHE on every release)
  manifest.webmanifest  — PWA manifest
body/
  PLAN.md               — baseline 3-day plan (superseded)
  PLAN-MAX.md           — aggressive gym split (superseded)
  PLAN-HOME-MAX.md      — THE plan: 13-week home recomp (dumbbells + bands)
  APPS-ANALYSIS.md      — competitor research (Cronometer/MFP/MacroFactor/Hevy) → feature backlog
```

## Features (v2.1)

- 13-week periodized program: LEARN → MAX → deloads (wk 7, 12) → FINAL, auto-phased by date
- Session logger: prefill from last week, 90 s rest timer, per-set ✓ with haptics
- Food diary: veg+egg food library (kcal+protein), meal groups, favorites, recents,
  custom foods, auto-syncs kcal+protein totals
- Adherence-neutral design (MacroFactor school): no red rings, no shame copy
- Stats: weight trend (7-d MA), estimated TDEE, adherence heatmap
- Coach: rule-based offline engine + LLM backend (glm-5.3-flash / qwen3.8-flash via
  a local proxy that injects the plan + today's stats + today's *diary* into the prompt,
  with a rolling conversation memory on disk)

## Run it

```bash
cd app
BAI_API_KEY=sk-... python3 server.py     # :8790, key only needed for the LLM coach
# app works fully offline (rule-based coach) without the key
```

## Conventions

- `index.html` is deliberately one file — no framework, no build; edit + hard refresh
- Every release: bump `CACHE` in `sw.js` (v1, v2, …) or phones keep the stale bundle
- Tests: `/tmp/test-logic.js` + `/tmp/test-diary.js` run the JS under node with a DOM shim
