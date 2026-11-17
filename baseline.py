import sqlite3
from collections import Counter

PACKAGE = "axios"
WINDOW = 20  # how many past releases define "normal"

conn = sqlite3.connect("driftguard.db")
rows = conn.execute(
    "SELECT version, publish_time, publisher FROM releases "
    "WHERE package=? AND publish_time IS NOT NULL "
    "ORDER BY publish_time ASC",
    (PACKAGE,),
).fetchall()

print(f"Package: {PACKAGE}  |  Total releases: {len(rows)}")
overall = Counter(r[2] for r in rows)
print("Publishers overall:", dict(overall))
print("-" * 70)

flagged = 0
for i in range(10, len(rows)):  # need some history first
    version, time, publisher = rows[i]
    history = rows[max(0, i - WINDOW):i]
    seen_ever = {r[2] for r in rows[:i]}
    usual = Counter(r[2] for r in history).most_common(1)[0][0]

    signals = []
    if publisher not in seen_ever:
        signals.append("NEW publisher never seen before")
    if publisher != usual:
        signals.append(f"differs from usual publisher ({usual})")

    if signals:
        flagged += 1
        print(f"{version:<10}{time:<26}{publisher}")
        for s in signals:
            print(f"    - {s}")

print("-" * 70)
print(f"Releases deviating from baseline: {flagged}")