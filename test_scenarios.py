import sqlite3
from collections import Counter

CI = {"GitHub Actions"}
conn = sqlite3.connect("driftguard.db")
real = conn.execute(
    "SELECT version, publish_time, publisher, install_script, provenance, dep_count "
    "FROM releases WHERE package='axios' AND publish_time IS NOT NULL "
    "ORDER BY publish_time ASC").fetchall()

def score(rows, i, window=5):
    v, t, pub, inst, prov, deps = rows[i]
    recent = rows[max(0, i - window):i]
    seen = {r[2] for r in rows[:i]}
    usual = Counter(r[2] for r in recent).most_common(1)[0][0]
    sig = []
    if pub not in seen: sig.append((25, "New publisher never seen before"))
    elif pub != usual: sig.append((10, f"Differs from usual publisher ({usual})"))
    if all(r[2] in CI for r in recent) and pub not in CI:
        sig.append((30, "Manual publish, bypassing CI/CD"))
    if all(r[4] for r in recent) and not prov:
        sig.append((25, "Provenance missing"))
    if inst and not any(r[3] for r in recent):
        sig.append((35, "Install script newly added"))
    if deps - rows[i-1][5] >= 2:
        sig.append((10, f"{deps - rows[i-1][5]} new dependencies"))
    hours = {int(r[1][11:13]) for r in rows[max(0, i - 20):i]}
    if int(t[11:13]) not in hours: sig.append((10, "Unusual publish hour"))
    return sum(s[0] for s in sig), sig

def tier(s):
    return "TIER 3" if s >= 70 else "TIER 2" if s >= 40 else "TIER 1" if s > 0 else "clean"

last = real[-1]
scenarios = {
    "A: normal CI release": ("9.9.1", "2026-11-01T18:00:00Z", "GitHub Actions", 0, last[4], last[5]),
    "B: new publisher only": ("9.9.2", "2026-11-01T18:00:00Z", "new-account", 0, last[4], last[5]),
    "C: hijack simulation": ("9.9.3", "2026-11-01T03:12:00Z", "new-account", 1, 0, last[5] + 2),
}
for name, rel in scenarios.items():
    s, sig = score(real + [rel], len(real))
    print(f"\n{name}  ->  score={s}  {tier(s)}")
    for w, text in sig:
        print(f"    +{w}  {text}")