import sqlite3
from collections import Counter

PACKAGE = "axios"
WINDOW = 5          # recent releases that define "normal"
MIN_HISTORY = 10    # need some history before scoring
CI_PUBLISHERS = {"GitHub Actions"}

conn = sqlite3.connect("driftguard.db")
rows = conn.execute(
    "SELECT version, publish_time, publisher, install_script, provenance, dep_count "
    "FROM releases WHERE package=? AND publish_time IS NOT NULL "
    "ORDER BY publish_time ASC", (PACKAGE,)).fetchall()

def score_release(i):
    v, t, pub, inst, prov, deps = rows[i]
    recent = rows[max(0, i - WINDOW):i]
    prev = rows[i - 1]
    seen = {r[2] for r in rows[:i]}
    usual = Counter(r[2] for r in recent).most_common(1)[0][0]
    signals = []

    if pub not in seen:
        signals.append((25, "New publisher never seen before"))
    elif pub != usual:
        signals.append((10, f"Differs from usual publisher ({usual})"))

    if all(r[2] in CI_PUBLISHERS for r in recent) and pub not in CI_PUBLISHERS:
        signals.append((30, "Manual publish, bypassing the usual CI/CD pipeline"))

    if all(r[4] for r in recent) and not prov:
        signals.append((25, "Provenance attestation missing (previous releases had it)"))

    if inst and not any(r[3] for r in recent):
        signals.append((35, "Install script newly added"))

    if deps - prev[5] >= 2:
        signals.append((10, f"{deps - prev[5]} new dependencies added"))

    hours = {int(r[1][11:13]) for r in rows[max(0, i - 20):i]}
    if int(t[11:13]) not in hours:
        signals.append((10, "Unusual publish hour"))

    return sum(s[0] for s in signals), signals

def tier(score):
    if score >= 70: return "TIER 3 - block + rollback PR proposal (stretch)"
    if score >= 40: return "TIER 2 - ALERT with recommendation"
    if score > 0:   return "TIER 1 - log only"
    return "clean"

counts = Counter()
for i in range(MIN_HISTORY, len(rows)):
    s, signals = score_release(i)
    label = tier(s)
    counts[label.split(" -")[0]] += 1
    if s >= 40:
        v, t, pub = rows[i][0], rows[i][1], rows[i][2]
        print(f"\n{label}\n  {PACKAGE}@{v}  {t}  by {pub}  score={s}")
        for w, text in signals:
            print(f"    +{w}  {text}")
        print("  Recommendation: hold the update, pin to last known-good version, notify security team.")

print("\n" + "-" * 60)
print(f"Package: {PACKAGE} | releases scored: {len(rows) - MIN_HISTORY}")
for k in ("clean", "TIER 1", "TIER 2", "TIER 3"):
    print(f"  {k:<8}{counts[k]}")