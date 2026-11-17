import sqlite3, html, os, webbrowser
from collections import Counter

PACKAGE = "axios"
CI = {"GitHub Actions"}
WINDOW = 5

ACTIONS = {
    "clean": "No action needed.",
    "TIER 1": "Log only. No alert is sent.",
    "TIER 2": "ALERT a human: hold the update, pin to last known-good version, notify security team.",
    "TIER 3": "Proposed: block in CI/CD and open a rollback PR. A human must approve; nothing is merged automatically.",
}

def tier(s):
    return "TIER 3" if s >= 70 else "TIER 2" if s >= 40 else "TIER 1" if s > 0 else "clean"

def score(rows, i):
    v, t, pub, inst, prov, deps = rows[i]
    recent = rows[max(0, i - WINDOW):i]
    seen = {r[2] for r in rows[:i]}
    usual = Counter(r[2] for r in recent).most_common(1)[0][0]
    sig = []
    if pub not in seen:
        sig.append((25, "New publisher", f"'{pub}' has never published this package before."))
    elif pub != usual:
        sig.append((10, "Publisher differs from usual", f"Recent releases were by '{usual}', not '{pub}'."))
    if all(r[2] in CI for r in recent) and pub not in CI:
        sig.append((30, "CI/CD bypass", "Recent releases came from the pipeline; this one came from an account."))
    if all(r[4] for r in recent) and not prov:
        sig.append((25, "Provenance missing", "Earlier releases had build provenance; this one does not."))
    if inst and not any(r[3] for r in recent):
        sig.append((35, "Install script added", "Package never ran install-time scripts before."))
    if deps - rows[i - 1][5] >= 2:
        sig.append((10, "Dependency jump", f"{deps - rows[i-1][5]} new dependencies."))
    hours = {int(r[1][11:13]) for r in rows[max(0, i - 20):i]}
    if int(t[11:13]) not in hours:
        sig.append((10, "Unusual publish hour", f"{t[11:13]}:00 UTC is outside the usual hours."))
    return sum(s[0] for s in sig), sig

conn = sqlite3.connect("driftguard.db")
real = conn.execute(
    "SELECT version, publish_time, publisher, install_script, provenance, dep_count "
    "FROM releases WHERE package=? AND publish_time IS NOT NULL "
    "ORDER BY publish_time ASC", (PACKAGE,)).fetchall()

counts = Counter()
scored = []
for i in range(10, len(real)):
    s, sig = score(real, i)
    counts[tier(s)] += 1
    scored.append((s, i, sig))
scored.sort(reverse=True)
total = len(real) - 10

last = real[-1]
scenarios = [
    ("A: Normal CI release", ("9.9.1", "2026-11-01T18:00:00Z", "GitHub Actions", 0, last[4], last[5])),
    ("D: Two new dependencies only", ("9.9.4", "2026-11-01T18:00:00Z", "GitHub Actions", 0, last[4], last[5] + 2)),
    ("B: Unknown account publishes manually", ("9.9.2", "2026-11-01T18:00:00Z", "new-account", 0, last[4], last[5])),
    ("C: Full hijack pattern", ("9.9.3", "2026-11-01T03:12:00Z", "new-account", 1, 0, last[5] + 2)),
]

e = html.escape
CLS = {"clean": "c0", "TIER 1": "c1", "TIER 2": "c2", "TIER 3": "c3"}

def badge(tr):
    return f'<span class="badge {CLS[tr]}">{e(tr)}</span>'

def sig_list(sig):
    if not sig:
        return "<p class='muted'>No signals triggered. Matches this package's normal behavior.</p>"
    return "<ul>" + "".join(
        f"<li><b>+{w} {e(n)}</b>: {e(r)}</li>" for w, n, r in sig) + "</ul>"

cards = ""
for title, rel in scenarios:
    s, sig = score(real + [rel], len(real))
    tr = tier(s)
    cards += (f'<div class="card"><h3>{e(title)} <small>(simulated)</small></h3>'
              f'<p>Score <b>{s}</b> {badge(tr)}</p>{sig_list(sig)}'
              f'<p class="action"><b>Action:</b> {e(ACTIONS[tr])}</p></div>')

rows_html = ""
for s, i, sig in scored[:10]:
    v, t, pub = real[i][0], real[i][1], real[i][2]
    why = "; ".join(f"+{w} {n}" for w, n, r in sig) or "none"
    rows_html += (f"<tr><td>{e(v)}</td><td>{e(t[:10])}</td><td>{e(pub)}</td>"
                  f"<td>{s}</td><td>{badge(tier(s))}</td><td>{e(why)}</td></tr>")

bar = ""
for k in ("clean", "TIER 1", "TIER 2", "TIER 3"):
    pct = 100 * counts[k] / total
    if pct > 0:
        bar += f'<div class="seg {CLS[k]}" style="width:{pct:.1f}%">{k} {counts[k]}</div>'

CSS = """
:root{--bg:#f6f7f9;--fg:#1c2330;--card:#fff;--line:#dde1e7;--mut:#667085;
--c0:#2e7d5b;--c1:#2f6fb5;--c2:#b7791f;--c3:#c0392b}
@media(prefers-color-scheme:dark){:root{--bg:#10151c;--fg:#e6e9ef;--card:#1a212b;--line:#2b3441;--mut:#9aa4b2}}
body{font-family:Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--fg);margin:0;padding:24px;max-width:1100px;margin:auto}
h1{margin:0}h2{margin-top:32px}.muted,small{color:var(--mut)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.stat{font-size:28px;font-weight:700}
.badge{color:#fff;padding:2px 8px;border-radius:10px;font-size:12px}
.c0{background:var(--c0)}.c1{background:var(--c1)}.c2{background:var(--c2)}.c3{background:var(--c3)}
.bar{display:flex;border-radius:8px;overflow:hidden;color:#fff;font-size:13px}
.seg{padding:8px 4px;text-align:center;white-space:nowrap;overflow:hidden}
table{width:100%;border-collapse:collapse;background:var(--card);font-size:14px}
td,th{border:1px solid var(--line);padding:6px 8px;text-align:left}
.action{border-top:1px solid var(--line);padding-top:8px;font-size:14px}
.note{border-left:4px solid var(--c2);padding:8px 12px;background:var(--card)}
"""

page = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DriftGuard Dashboard</title><style>{CSS}</style></head><body>
<h1>DriftGuard</h1>
<p class="muted">Read-only report of release drift scoring. Package: {e(PACKAGE)}. Prototype, about 40% complete.</p>

<div class="grid">
<div class="card"><div class="muted">Releases in database</div><div class="stat">{len(real)}</div></div>
<div class="card"><div class="muted">Releases scored</div><div class="stat">{total}</div></div>
<div class="card"><div class="muted">Alerts to a human (Tier 2+)</div><div class="stat">{counts['TIER 2'] + counts['TIER 3']}</div></div>
<div class="card"><div class="muted">Single-signal baseline flags</div><div class="stat">43</div></div>
</div>

<h2>Tier distribution on real {e(PACKAGE)} history</h2>
<div class="bar">{bar}</div>

<h2>Controlled test scenarios</h2>
<p class="note">These releases are <b>simulated</b> and appended to real history to show the tier logic. They are not real attacks.</p>
<div class="grid">{cards}</div>

<h2>Highest-scoring real releases</h2>
<table><tr><th>Version</th><th>Date</th><th>Publisher</th><th>Score</th><th>Tier</th><th>Triggered signals</th></tr>{rows_html}</table>

<h2>Signal weights (initial values, to be tuned in backtesting)</h2>
<table><tr><th>Signal</th><th>Weight</th></tr>
<tr><td>Install script newly added</td><td>35</td></tr>
<tr><td>CI/CD bypass</td><td>30</td></tr>
<tr><td>New publisher</td><td>25</td></tr>
<tr><td>Provenance missing</td><td>25</td></tr>
<tr><td>Publisher differs from usual</td><td>10</td></tr>
<tr><td>Dependency jump</td><td>10</td></tr>
<tr><td>Unusual publish hour</td><td>10</td></tr></table>
<p class="muted">Tier 1: score 1-39 (log only). Tier 2: 40-69 (alert). Tier 3: 70+ (block and rollback proposal, human approval required).</p>
</body></html>"""

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(page)
print("Created dashboard.html")
webbrowser.open("file://" + os.path.abspath("dashboard.html"))