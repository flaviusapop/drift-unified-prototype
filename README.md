# Drift Unified — the official weekly site

> As of Oct 25, 2026 this is the official Drift version we keep updating (Zander). The older notes below are kept for history.

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

## Add a week (repeatable)

One script, `add_week.py`, adds or replaces one Mon–Sun week on `index.html`
(newest first). It never touches other weeks. Inputs: the week's learning-plan
markdown (Brief A) and the Monday start date. Brief B (Reddit) has an agent
curation step in the middle.

Key: `/home/box/.config/redditapis.env` (`REDDITAPIS_API_KEY=...`). The script
reads it from that file only (the shell env var is not used). Read-only GETs;
never post, vote or DM. Raw responses go to `data-cache/<start>/` (gitignored),
and the call count plus the last `X-Credits-Remaining` value go to
`data-cache/<start>/calls.json`.

```bash
cd /workspace/drift-unified-prototype && git pull --rebase origin main
START=2026-10-26                      # Monday of the week
PLAN=/workspace/plan-2026-11-01.md    # that week's learning plan (Sunday edition)

# 1. Collect: 1 call per subreddit (10 calls). Top 100 of the past week if run
#    within 7 days of START, otherwise paginates sort=new (--mode new).
python3 add_week.py collect $START
#    -> data-cache/$START/candidates.md  (in-window posts, ranked, with snippets)
#    -> weeks-data/$START.json            (skeleton, created once)

# 2. Curate (agent): in weeks-data/$START.json pick threads with real signal per
#    subreddit (workflows, setups, measured results, cost/memory/security lessons;
#    not score alone; usually 0-3 per sub), set "id", "summary", "kp".
#    Set "note" for subs with nothing kept, plus "headline", "executive_read"
#    (HTML paragraphs), "for_our_setup", optional "method".
python3 add_week.py comments $START   # 1 call per kept thread, cached
#    -> data-cache/$START/comments.md ; put 1-2 comment ids in each thread's "quotes"

# 3. Build: insert/replace the week block, jump-list row, weeks/$START.html redirect
python3 add_week.py build $PLAN $START

# 4. Publish + verify (Pages redeploys in ~1 min)
git add -A && git commit -m "Add Week NN" && git push
sleep 75 && curl -s https://flaviusapop.github.io/drift-unified-prototype/ | grep -c 'id="wk-NN"'
```

Re-running `build` for the same week replaces that week in place. Week ids are
ISO week numbers (`wk-43` = Oct 19–25, 2026). The committed `weeks-data/<start>.json`
holds the curation, so a week can be rebuilt from cache without new API calls.
Cost: about (10 + kept threads) calls × $0.002.
