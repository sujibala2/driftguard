import sqlite3
from collections import Counter

PACKAGE = "axios"
CI = {"GitHub Actions"}
WINDOW = 5

ACTIONS = {
    "clean": "No action needed.",
    "TIER 1": "Log only. No alert is sent; kept for audit and trend review.",
    "TIER 2": "ALERT a human. Hold the update, pin to the last known-good "
              "version, notify the security team.",
    "TIER 3": "HIGH CONFIDENCE. Proposed: block this release in CI/CD and open "
              "a rollback PR to the last verified-safe version. A human must "
              "approve; nothing is merged automatically.",
}

def tier(s):
    return "TIER 3" if s >= 70 else "TIER 2" if s >= 40 else "TIER 1" if s > 0 else "clean"

def score(rows, i):
    v, t, pub, inst, prov, deps = rows[i]
    recent = rows[max(0, i - WINDOW):i]
    seen = {r[2] for r in rows[:i]}
    usual = Counter(r[2] for r in recent).most_common(1)[0][0]
    sig = []  # (weight, signal, reason)

    if pub not in seen:
        sig.append((25, "New publisher",
                    f"'{pub}' has never published this package before."))
    elif pub != usual:
        sig.append((10, "Publisher differs from usual",
                    f"Recent releases were published by '{usual}', not '{pub}'."))
    if all(r[2] in CI for r in recent) and pub not in CI:
        sig.append((30, "CI/CD bypass",
                    "Last releases came from the automated pipeline; this one was published by an account."))
    if all(r[4] for r in recent) and not prov:
        sig.append((25, "Provenance missing",
                    "Earlier releases carried build provenance; this one does not."))
    if inst and not any(r[3] for r in recent):
        sig.append((35, "Install script added",
                    "Package never ran install-time scripts before; this release does."))
    if deps - rows[i - 1][5] >= 2:
        sig.append((10, "Dependency jump",
                    f"{deps - rows[i - 1][5]} new dependencies compared with the previous release."))
    hours = {int(r[1][11:13]) for r in rows[max(0, i - 20):i]}
    if int(t[11:13]) not in hours:
        sig.append((10, "Unusual publish hour",
                    f"Hour {t[11:13]}:00 UTC is outside this package's usual publishing hours."))
    return sum(s[0] for s in sig), sig

def report(rows, i, title=None):
    s, sig = score(rows, i)
    tr = tier(s)
    v, t, pub = rows[i][0], rows[i][1], rows[i][2]
    print("=" * 66)
    if title:
        print(title)
    print(f"Release : {PACKAGE}@{v}   published {t} by {pub}")
    print(f"Score   : {s}      Classification: {tr}")
    if sig:
        print("Triggered signals and reasons:")
        for w, name, why in sig:
            print(f"  +{w:<3}{name}: {why}")
    else:
        print("Triggered signals: none (matches this package's normal behavior)")
    print(f"Action  : {ACTIONS[tr]}")

conn = sqlite3.connect("driftguard.db")
real = conn.execute(
    "SELECT version, publish_time, publisher, install_script, provenance, dep_count "
    "FROM releases WHERE package=? AND publish_time IS NOT NULL "
    "ORDER BY publish_time ASC", (PACKAGE,)).fetchall()

# Part 1: controlled scenarios (simulated releases appended to real history)
last = real[-1]
scenarios = [
    ("A: normal CI release (SIMULATED)",
     ("9.9.1", "2026-11-01T18:00:00Z", "GitHub Actions", 0, last[4], last[5])),
    ("D: two new dependencies only (SIMULATED)",
     ("9.9.4", "2026-11-01T18:00:00Z", "GitHub Actions", 0, last[4], last[5] + 2)),
    ("B: unknown account publishes manually (SIMULATED)",
     ("9.9.2", "2026-11-01T18:00:00Z", "new-account", 0, last[4], last[5])),
    ("C: full hijack pattern (SIMULATED)",
     ("9.9.3", "2026-11-01T03:12:00Z", "new-account", 1, 0, last[5] + 2)),
]
print("\nPART 1 - CONTROLLED TEST SCENARIOS")
for title, rel in scenarios:
    report(real + [rel], len(real), title)

# Part 2: three highest-scoring real releases, to show explanations on real data
scored = sorted(((score(real, i)[0], i) for i in range(10, len(real))), reverse=True)[:3]
print("\n\nPART 2 - HIGHEST-SCORING REAL AXIOS RELEASES")
for s, i in scored:
    report(real, i, "REAL release")