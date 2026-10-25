#!/usr/bin/env python3
"""Add (or replace) one week on the Drift landing page (index.html).

A week = Brief A (AI learning plan, from a plan markdown file) + Brief B
(Reddit deep-dive, from RedditAPIs, curated by an agent). Three steps:

  1. collect   python3 add_week.py collect 2026-10-19
       Fetches the posts for each subreddit (1 call per subreddit) into
       data-cache/<start>/ (gitignored) and writes data-cache/<start>/candidates.md:
       every in-window post, ranked, with a text snippet. If weeks-data/<start>.json
       does not exist yet, it writes a skeleton to fill in.
  2. curate    (agent step) Edit weeks-data/<start>.json: per subreddit pick the
       threads with real signal (workflows, setups, measured results, cost or
       memory lessons; not just score), write summary + key points, plus the
       Brief B headline, executive read and "For our setup" list.
       Then run:  python3 add_week.py comments 2026-10-19
       (fetches top comments only for kept threads, 1 call per thread, cached)
       and pick 1-2 quote ids per thread from data-cache/<start>/comments.md.
  3. build     python3 add_week.py build PLAN.md 2026-10-19
       Renders the week block, inserts it newest-first (or replaces the same
       week), updates the jump list and writes weeks/<start>.html redirect.
       Other weeks are left byte-for-byte untouched.

Key: read from /home/box/.config/redditapis.env (REDDITAPIS_API_KEY=...).
Never printed. Read-only GET requests only.
"""
import argparse, datetime as dt, html, json, pathlib, re, sys, time

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / "data-cache"
WDATA = ROOT / "weeks-data"
INDEX = ROOT / "index.html"
KEYFILE = pathlib.Path("/home/box/.config/redditapis.env")
API = "https://api.redditapis.com/api/reddit"
COST = 0.002

# order, display name, api name, hue, tier  (same as Week 42)
SUBS = [
    ("hermesagent", "hermesagent", "hermes", "Core"),
    ("Hermes", "Hermes", "xnetwork", "Core"),
    ("OpenClaw", "OpenClaw", "mlreddit", "Core"),
    ("AI_Agents", "AI_Agents", "singularity", "Core"),
    ("ClaudeAI", "ClaudeAI", "claudeai", "Secondary"),
    ("ClaudeCode", "ClaudeCode", "claudeai", "Secondary"),
    ("cursor", "cursor", "xnetwork", "Secondary"),
    ("LocalLLaMA", "LocalLLaMA", "localllama", "Secondary"),
    ("ChatGPT", "ChatGPT", "mlreddit", "Secondary"),
    ("OpenAI", "OpenAI", "hermes", "Secondary"),
]

esc = lambda s: html.escape(s or "", quote=True)

# ---------------------------------------------------------------- dates
def window(start):
    s = dt.date.fromisoformat(start)
    if s.weekday() != 0:
        sys.exit(f"{start} is not a Monday")
    e = s + dt.timedelta(days=6)
    return s, e

def iso_week(start):
    return dt.date.fromisoformat(start).isocalendar()[1]

def md(d):  # "Oct 19"
    return d.strftime("%b %-d")

def in_window(p, s, e):
    c = dt.datetime.fromisoformat(p["created"].replace("Z", "+00:00")).date()
    return s <= c <= e

# ---------------------------------------------------------------- api
def key():
    m = re.search(r"REDDITAPIS_API_KEY=[\"']?([^\"'\s]+)", KEYFILE.read_text())
    if not m:
        sys.exit("no key in " + str(KEYFILE))
    return m.group(1)

class Api:
    def __init__(self, d):
        import requests
        self.rq, self.h = requests, {"Authorization": f"Bearer {key()}"}
        self.log = d / "calls.json"
        self.state = json.loads(self.log.read_text()) if self.log.exists() else {"calls": 0, "credits_remaining": None}

    def get(self, path, params):
        r = self.rq.get(f"{API}/{path}", params=params, headers=self.h, timeout=90)
        self.state["calls"] += 1
        self.state["credits_remaining"] = r.headers.get("X-Credits-Remaining", self.state["credits_remaining"])
        self.log.write_text(json.dumps(self.state))
        if r.status_code != 200:
            raise RuntimeError(f"{path} -> HTTP {r.status_code}")
        return r.json()

# ---------------------------------------------------------------- collect
def cmd_collect(a):
    s, e = window(a.start)
    d = CACHE / a.start; d.mkdir(parents=True, exist_ok=True)
    api = None
    age = (dt.datetime.now(dt.timezone.utc).date() - s).days
    mode = a.mode or ("top-week" if age <= 7 else "new")
    lines = [f"# Candidates {md(s)}–{md(e)}, {s.year} (mode: {mode})", ""]
    for name, sub, hue, tier in SUBS:
        f = d / f"posts-{name}.json"
        if not f.exists():
            api = api or Api(d)
            posts, after, pages = [], None, 0
            while True:
                prm = {"subreddit": sub, "limit": 100}
                prm.update({"sort": "top", "t": "week"} if mode == "top-week" else {"sort": "new"})
                if after: prm["after"] = after
                j = api.get("posts", prm); pages += 1
                posts += j.get("posts", []); after = j.get("after")
                oldest = min((p["created"] for p in j.get("posts", [])), default="")
                if mode == "top-week" or not after or oldest[:10] < s.isoformat() or pages >= a.max_pages:
                    break
            f.write_text(json.dumps({"posts": posts, "mode": mode, "pages": pages}))
        posts = json.loads(f.read_text())["posts"]
        win = [p for p in posts if in_window(p, s, e) and not p.get("stickied")]
        win.sort(key=lambda p: (p.get("comments", 0) + p.get("upvotes", 0)), reverse=True)
        lines.append(f"## r/{name} — {len(posts)} fetched, {len(win)} in window ({tier})")
        for p in win[: a.top]:
            t = (p.get("text") or "").replace("\n", " ")[:320]
            lines.append(f"- `{p['id']}` {p.get('upvotes')} pts · {p.get('comments')} c · {p['created'][:10]} · "
                         f"[{p.get('link_flair_text') or '-'}] **{p['title']}**\n  {t}")
        lines.append("")
    (d / "candidates.md").write_text("\n".join(lines))
    sk = WDATA / f"{a.start}.json"
    if not sk.exists():
        WDATA.mkdir(exist_ok=True)
        sk.write_text(json.dumps({
            "headline": "", "executive_read": [""], "for_our_setup": [""],
            "subs": {n: {"note": "", "threads": [{"id": "", "summary": "", "kp": [], "quotes": []}][:0]} for n, *_ in SUBS},
        }, indent=2))
        print("skeleton:", sk)
    st = json.loads((d / "calls.json").read_text()) if (d / "calls.json").exists() else {"calls": 0}
    print(f"candidates: {d/'candidates.md'}  calls so far: {st['calls']}  credits remaining: {st.get('credits_remaining')}")

# ---------------------------------------------------------------- comments
def walk(children, out, depth=0):
    for n in children or []:
        if n.get("kind") != "t1": continue
        x = n["data"]
        out.append((depth, x))
        r = x.get("replies")
        if isinstance(r, dict) and depth < 1:
            walk(r["data"]["children"], out, depth + 1)

def cmd_comments(a):
    d = CACHE / a.start; sel = json.loads((WDATA / f"{a.start}.json").read_text())
    api = None; lines = [f"# Comment candidates {a.start}", ""]
    for name, *_ in SUBS:
        for t in sel["subs"].get(name, {}).get("threads", []):
            f = d / f"comments-{t['id']}.json"
            if not f.exists():
                api = api or Api(d)
                f.write_text(json.dumps(api.get(f"post/{t['id']}/comments", {"limit": 40, "depth": 2, "sort": "top"})))
            j = json.loads(f.read_text()); out = []; walk(j.get("comments"), out)
            lines.append(f"## r/{name} `{t['id']}` {j['post']['title']}")
            for depth, x in sorted(out, key=lambda z: -(z[1].get("score") or 0))[:12]:
                b = (x.get("body") or "").replace("\n", " ")[:300]
                lines.append(f"- `{x['id']}` {x.get('author')} {x.get('score')} pts{' (reply)' if depth else ''}: {b}")
            lines.append("")
    (d / "comments.md").write_text("\n".join(lines))
    st = json.loads((d / "calls.json").read_text())
    print(f"comments: {d/'comments.md'}  calls so far: {st['calls']}  credits remaining: {st.get('credits_remaining')}")

# ---------------------------------------------------------------- Brief A (plan markdown)
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")

def inl(s):
    s = esc(s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return LINK.sub(lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)}</a>', s)

ITEM = re.compile(r"^\[(?P<t>[^\]]+)\]\((?P<u>https?://[^)\s]+)\),\s*(?P<who>.+?),\s*(?P<dur>about [^,.]+?(?: read)?)"
                  r"(?:,\s*(?P<tag>new(?: \([^)]*\))?|from your (?:X )?saves))?\.\s*(?P<sum>.*)$")

def tcard(text, num=None):
    m = ITEM.match(text)
    if not m:
        return f'<div class="tcard"><p class="summary">{inl(text)}</p></div>'
    who = m["who"]
    i = who.rfind(" on ")
    if i > 0: who = who[:i] + " · " + who[i + 4:]
    who = re.sub(r"· the (.+?) channel$", r"· \1", who)
    tag = m["tag"] or ""
    tag = "from your X saves" if "saves" in tag else tag
    title = (f"{num}. " if num else "") + m["t"]
    badge = f"<b>{esc(m['dur'])}</b><i>/</i>{esc(who)}" + (f"<i>/</i>{esc(tag)}" if tag else "")
    return (f'<div class="tcard"><h3><a href="{m["u"]}" target="_blank" rel="noopener">{esc(title)}</a></h3>'
            f'<span class="badge">{badge}</span><p class="summary">{inl(m["sum"])}</p></div>')

def brief_a(plan, wk, plan_label):
    txt = pathlib.Path(plan).read_text()
    title = re.search(r"^# (.+)$", txt, re.M).group(1).strip()
    parts = re.split(r"^## (.+)$", txt, flags=re.M)
    intro = " ".join(l.strip() for l in parts[0].splitlines() if l.strip() and not l.startswith("#"))
    out = [f'<div class="sum hed"><h3 class="issuehed">{esc(title)}</h3><p>{inl(intro)}</p></div>']
    for i in range(1, len(parts), 2):
        head, body = parts[i].strip(), parts[i + 1]
        m = re.match(r"(.+?)\s*\((about [^)]*)\)\s*$", head)
        name, meta = (m.group(1), m.group(2)) if m else (head, plan_label)
        items, paras, order = [], [], head.lower().startswith("suggested order")
        for l in body.splitlines():
            l = l.strip()
            if not l: continue
            mm = re.match(r"^(\d+)\.\s+(.*)$", l)
            if mm: items.append((mm.group(1), mm.group(2)))
            elif l.startswith("- "): items.append((None, l[2:]))
            else: paras.append(l)
        if order:
            tot = next((p for p in paras if "total" in p.lower()), "")
            tm = re.search(r"about [\d.]+ hours", tot)
            meta = f"{tm.group(0)} total" if tm else meta
            lis = "".join(f"<li>{inl(re.sub(r'^\*\*(.+?):\*\*', r'\1:', t))}</li>" for _, t in items)
            tot = re.match(r"[^.]*total[^.]*\.", tot)
            g = f'<ol class="ed">{lis}</ol>' + (f'<p style="padding:0 20px">{inl(tot.group(0))}</p>' if tot else "")
        else:
            g = "".join(f'<p style="padding:0 20px">{inl(p)}</p>' for p in paras)
            g += "".join(tcard(t, n) for n, t in items)
        out.append(f'<div class="grp"><div class="grph"><span>{esc(name)}</span><span>{esc(meta)}</span></div>{g}</div>')
    return title, "\n        ".join(out)

# ---------------------------------------------------------------- Brief B
def short(s, n=250):
    s = (s or "").replace("\n", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"

def thread_card(p, t, cdata):
    cm = {}
    if cdata:
        out = []; walk(cdata.get("comments"), out)
        cm = {x["id"]: x for _, x in out}
    created = dt.datetime.fromisoformat(p["created"].replace("Z", "+00:00"))
    kp = "".join(f"<li>{esc(k)}</li>" for k in t.get("kp", []))
    qs = [cm[q] for q in t.get("quotes", []) if q in cm]
    url = p.get("url") or f"https://reddit.com{p['permalink']}"
    h = (f'<div class="tcard"><h3><a href="{esc(url)}" target="_blank" rel="noopener">{esc(p["title"])}</a></h3>'
         f'<span class="badge"><b>{p.get("upvotes")}</b> pts<i>/</i><b>{p.get("comments")}</b> comments<i>/</i>{md(created)}</span>'
         f'<p class="summary">{esc(t["summary"])}</p>' + (f'<ul class="kp">{kp}</ul>' if kp else ""))
    if qs:
        items = "".join(
            f'<div class="tc-item"><p class="tc-meta"><b>{esc(x.get("author"))}</b><span class="sc">{x.get("score")} pts</span></p>'
            f'<p class="tc-body">{esc(short(x.get("body")))}</p>'
            f'<a class="tc-pl" href="https://www.reddit.com{esc(x.get("permalink"))}" target="_blank" rel="noopener">permalink</a></div>'
            for x in qs)
        h += (f'<details class="tc"><summary class="tc-hd">Top comments <span>{len(qs)} quoted</span></summary>'
              f'<div class="tc-list">{items}</div></details>')
    return h + "</div>"

def brief_b(start, wk):
    s, e = window(start)
    d = CACHE / start
    sel = json.loads((WDATA / f"{start}.json").read_text())
    secs, kept_total, fetched_total = [], 0, 0
    for name, sub, hue, tier in SUBS:
        posts = {p["id"]: p for p in json.loads((d / f"posts-{name}.json").read_text())["posts"]}
        fetched_total += len(posts)
        ss = sel["subs"].get(name, {}); th = [t for t in ss.get("threads", []) if t.get("id") in posts]
        kept_total += len(th)
        stat = f"{len(posts)} fetched · {len(th)} kept · {len(th)} shown" + ("" if th else " — nothing kept this week")
        head = (f'    <section class="subsrc" id="sub-{name.lower().replace("_", "-")}-{wk}" style="color:var(--h-{hue})">\n'
                f'      <header class="subsrc-h">\n        <span class="subk">Brief B · Reddit Deep-Dive · {tier}</span>\n'
                f'        <h3>r/{name}</h3>\n        <span class="subline"><span class="subtier">{tier}</span><span class="substat">{stat}</span></span>\n      </header>')
        if th:
            cards = "".join(thread_card(posts[t["id"]], t, json.loads((d / f"comments-{t['id']}.json").read_text())
                                        if (d / f"comments-{t['id']}.json").exists() else None) for t in th)
            secs.append(head + "\n" + cards + "\n</section>\n")
        else:
            note = ss.get("note") or "no substantive workflow or use-case thread in the window under the Drift rule."
            secs.append(head + f'<div class="notyet"><b>Nothing kept this week</b> — r/{name} — {esc(note)}</div></section>\n')
    st = json.loads((d / "calls.json").read_text()) if (d / "calls.json").exists() else {}
    method = sel.get("method") or f"top {100} posts of the week fetched per subreddit ({fetched_total:,} total), filtered to the window and to substantive threads"
    ex = "\n".join(f'          <p style="padding:0 20px">{p}</p>' for p in sel["executive_read"])
    fo = "".join(f"<li>{esc(x)}</li>" for x in sel["for_our_setup"])
    rng = f"{md(s)}–{e.strftime('%-d') if s.month == e.month else md(e)}"
    synth = f'''    <section class="bbsynth" aria-label="Brief B executive read">
      <div class="sum hed"><h3 class="issuehed">{esc(sel["headline"])}</h3><p><b>Collected {rng}, {s.year} via RedditAPIs</b> — {esc(method)}; top comments fetched only for the {kept_total} kept threads. Raw responses are cached locally and not committed.</p></div>
<div class="grp"><div class="grph"><span>Executive read</span><span>{rng} collection</span></div>
{ex}
          <aside class="callout"><span class="boxlabel">Note</span><p>Every thread, score and quote above comes from the {rng} RedditAPIs responses; summaries and key points are editorial, quotes are excerpts of the fetched comment text.</p></aside>
        </div>
<div class="grp"><div class="grph"><span>For our setup</span><span>from this window</span></div>
          <ol class="ed">{fo}</ol></div>
    </section>'''
    return "\n".join(secs) + "\n" + synth, kept_total

# ---------------------------------------------------------------- page surgery
def find_week(src, wk):
    """Return (start, end) of <section class="wk" id="wk-NN"> ... matching </section>, or None."""
    m = re.search(rf'<section class="wk" id="wk-{wk}">', src)
    if not m: return None
    depth, i = 0, m.start()
    for t in re.finditer(r"<section\b|</section>", src[m.start():]):
        depth += 1 if t.group(0) == "<section" else -1
        if depth == 0:
            end = m.start() + t.end()
            return m.start(), end
    sys.exit(f"unbalanced sections in wk-{wk}")

def cmd_build(a):
    s, e = window(a.start)
    wk = iso_week(a.start)
    title_a, body_a = brief_a(a.plan, wk, a.plan_label or f"{md(s + dt.timedelta(days=6))} plan")
    body_b, kept = brief_b(a.start, wk)
    rng = f"{md(s)} — {md(e)}"
    block = f'''<section class="wk" id="wk-{wk}">
    <div class="wkhead"><div class="in">
      <span class="no">Week {wk}</span><span class="dt">{rng}</span>
      <span class="strip" aria-hidden="true"><i data-on="true"></i><i data-on="true"></i><i data-on="true"></i><i data-on="true"></i><i data-on="true"></i><i data-on="true"></i><i></i><i></i><i></i><i></i><i></i><i></i></span>
      <button class="fold" data-fold-all="{wk}">Fold all</button>
    </div></div>

    <!-- Brief A -->
    <section class="src" id="learning-{wk}" data-fold="false" style="color:var(--h-claudeai)">
      <div class="srch"><div class="in"><h2><button class="srtoggle" aria-expanded="true">Brief A — AI Learning</button></h2></div></div>
      <div class="fold-wrap"><div>

        {body_a}

      </div></div>
    </section>

  <!-- Brief B -->
  <section class="src" id="reddit-{wk}" data-fold="false" style="color:var(--h-hermes)">
    <div class="srch"><div class="in"><h2><button class="srtoggle" aria-expanded="true">Brief B — Reddit Deep-Dive</button></h2></div></div>
    <div class="fold-wrap"><div>
{body_b}
    </div></div>
  </section>
  </section>'''
    src = INDEX.read_text()
    loc = find_week(src, wk)
    if loc:
        src = src[:loc[0]] + block + src[loc[1]:]
    else:  # insert before the first older week (weeks are newest first)
        olds = [(int(m.group(1)), m.start()) for m in re.finditer(r'<section class="wk" id="wk-(\d+)">', src)]
        nxt = next((pos for n, pos in olds if n < wk), None)
        if nxt is None:
            nxt = src.index('<section class="brk-band">')
        src = src[:nxt] + block + "\n\n  " + src[nxt:]
    # jump list row
    row = (f'<li><a class="week-row" href="#wk-{wk}"><span class="week-name">Week {wk}</span>'
           f'<span class="week-meta">{md(s)} — {md(e)}, {e.year} · {kept} THREADS KEPT</span><span class="arr" aria-hidden="true">↓</span></a></li>')
    rx = re.compile(rf'<li><a class="week-row" href="#wk-{wk}">.*?</li>')
    if rx.search(src):
        src = rx.sub(lambda _: row, src, count=1)
    else:
        rows = [(int(m.group(1)), m.start()) for m in re.finditer(r'<li><a class="week-row" href="#wk-(\d+)">', src)]
        pos = next((p for n, p in rows if n < wk), None)
        if pos is None:
            pos = src.index("</ul>", src.index('class="week-list"'))
            src = src[:pos] + "  " + row + "\n    " + src[pos:]
        else:
            src = src[:pos] + row + "\n      " + src[pos:]
    INDEX.write_text(src)
    (ROOT / "weeks").mkdir(exist_ok=True)
    (ROOT / "weeks" / f"{a.start}.html").write_text(f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=../index.html#wk-{wk}">
<link rel="canonical" href="../index.html#wk-{wk}">
<title>Week {wk} — moved to the single landing page</title>
</head>
<body>
<p>This week now lives on the single landing page: <a href="../index.html#wk-{wk}">Week {wk}</a>.</p>
<script>location.replace("../index.html#wk-{wk}");</script>
</body>
</html>
''')
    print(f"Week {wk} built: Brief A '{title_a}', Brief B {kept} threads kept")

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("collect"); c.add_argument("start"); c.add_argument("--mode", choices=["top-week", "new"])
    c.add_argument("--top", type=int, default=25); c.add_argument("--max-pages", type=int, default=8)
    k = sp.add_parser("comments"); k.add_argument("start")
    b = sp.add_parser("build"); b.add_argument("plan"); b.add_argument("start"); b.add_argument("--plan-label")
    a = ap.parse_args()
    {"collect": cmd_collect, "comments": cmd_comments, "build": cmd_build}[a.cmd](a)

if __name__ == "__main__":
    main()
