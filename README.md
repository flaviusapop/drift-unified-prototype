# Drift Unified — Prototype (3rd site)

**Prototype only.** A third, separate site to iterate on Zander's unified
2-brief-per-week idea in the Drift design. It does **not** replace or modify
the live sites:

- Live Drift: https://flaviusapop.github.io/ai-digest/drift.html (repo `flaviusapop/ai-digest`)
- Live learning plan: https://flaviusapop.github.io/weekly-ai-learning-plan/ (repo `flaviusapop/weekly-ai-learning-plan`)

Live prototype: https://flaviusapop.github.io/drift-unified-prototype/

## Idea

One Drift-design site, 2 briefs per week, synced in timing/format:

1. **Brief A — AI Learning** (working title, TODO: rename — naming exploration
   runs separately): exactly 3 Must Watch + agents/workflows,
   investing/trading, product/building; ~10h; no short-form, no vendor content.
2. **Brief B — Reddit Deep-Dive** (working title, TODO: rename): priority
   threads, comments worth quoting, what changes for a real setup.
   Planned sources: r/hermesagent, r/Hermes, r/OpenClaw, r/AI_Agents,
   r/ClaudeAI, r/ClaudeCode, r/cursor, r/LocalLLaMA, r/ChatGPT, r/OpenAI.

Names are placeholders (`Brief A / Brief B`) until Zander picks final names.
Implementation of the collector/scheduler is intentionally **not** started —
this repo only proves the unified layout. The unified spec (how the two
digests combine) is still to be decided by Zander.

## Layout

- `index.html` — THE single landing page: weeks stacked newest-first on one page (Week 42 full Brief A + Brief B, Weeks 41/40 as not-collected blocks), with a minimal in-page anchor jump list at the top
- `weeks/2026-10-12.html` — redirect stub to `index.html#wk-42` (the week now lives on the landing page)
  Drift style: `Brief/Week header · date range · strip · Fold all`,
  foldable sections (Brief A and Brief B sticky tabs sit directly together), and inside Brief B ten full-size subreddit section headers (big hue display heading, Core/Secondary pill, rule, scanned/kept/shown stat) starting under Brief B's own header; r/hermesagent carries the Brief 35 sample, the other 9 subreddits are 'not yet collected' placeholders, priority-thread cards, top-comments folds
- `style.css` — Drift design DNA copied read-only from `flaviusapop/ai-digest`
  (`src/drift.html`: cream/dark editorial, Chivo + Sometype Mono, 660px
  measure, mobile-first) + small prototype additions (banner, cards)
- `app.js` — fold/unfold, Fold all, Compact (key-points) toggle; no backend

Visual system: `style.css` is the original Drift stylesheet verbatim plus a small additions block that reuses only original Drift tokens/patterns (type scale, `--h-*` hues, `.brk-band` divider, `.srch/.srtoggle` subreddit headers, original fold motion). No invented sizes, colours or transitions.

Sample content is clearly labelled PROTOTYPE: Brief A reuses the Oct 18
learning-plan structure; Brief B reuses Drift Brief 35 (Aug 21–26, 2026)
structure/headline. Neither is a new collected edition.

## How to iterate

1. Edit HTML/CSS/JS directly (plain static, no build step).
2. Add a week: copy `weeks/2026-10-12.html`, change the Week header/date,
   replace sample cards, and add a matching week section + anchor row in `index.html`.
3. Rename briefs: search for `Brief A` / `Brief B` once final names land.
4. Publish: `git add -A && git commit -m "..." && git push` — GitHub Pages
   serves `main` / root, redeploys in ~1 min.
5. Verify: `curl -s -o /dev/null -w '%{http_code}\n' https://flaviusapop.github.io/drift-unified-prototype/`
