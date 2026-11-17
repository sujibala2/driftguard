import sqlite3

conn = sqlite3.connect("driftguard.db")
cur = conn.cursor()
cur.execute(
    "SELECT version, publish_time, publisher FROM releases "
    "ORDER BY publish_time DESC LIMIT 15"
)

print(f"{'VERSION':<12}{'PUBLISH TIME':<28}{'PUBLISHER'}")
print("-" * 60)
for version, publish_time, publisher in cur.fetchall():
    print(f"{version:<12}{str(publish_time):<28}{publisher}")