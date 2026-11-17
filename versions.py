import sqlite3

conn = sqlite3.connect("driftguard.db")
rows = conn.execute(
    "SELECT version, publish_time, publisher FROM releases "
    "WHERE package='axios' AND publish_time >= '2026-03-01' "
    "AND publish_time < '2026-04-15' ORDER BY publish_time"
).fetchall()

print(f"{'VERSION':<12}{'PUBLISH TIME':<28}{'PUBLISHER'}")
print("-" * 60)
for v, t, p in rows:
    print(f"{v:<12}{t:<28}{p}")
print(f"\nReleases in window: {len(rows)}")