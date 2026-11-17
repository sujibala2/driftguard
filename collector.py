import requests
import sqlite3
import time

PACKAGE = "axios"  # change this to any npm package

def fetch_package(name, tries=5):
    headers = {"User-Agent": "DriftGuard-student-project/0.1"}
    for attempt in range(1, tries + 1):
        try:
            resp = requests.get(
                f"https://registry.npmjs.org/{name}",
                headers=headers, timeout=60,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt}/{tries} failed: {type(e).__name__}")
            if attempt == tries:
                raise
            time.sleep(3 * attempt)

def has_install_script(info):
    scripts = info.get("scripts") or {}
    return int(any(k in scripts for k in ("preinstall", "install", "postinstall")))

def has_provenance(info):
    return int(bool((info.get("dist") or {}).get("attestations")))

def save_releases(name, data):
    conn = sqlite3.connect("driftguard.db")
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS releases")
    cur.execute("""
        CREATE TABLE releases (
            package TEXT, version TEXT, publish_time TEXT,
            publisher TEXT, publisher_email TEXT,
            install_script INTEGER, provenance INTEGER, dep_count INTEGER,
            PRIMARY KEY (package, version)
        )
    """)
    times = data.get("time", {})
    count = 0
    for version, info in data.get("versions", {}).items():
        user = info.get("_npmUser") or {}
        cur.execute(
            "INSERT OR REPLACE INTO releases VALUES (?,?,?,?,?,?,?,?)",
            (name, version, times.get(version), user.get("name"),
             user.get("email"), has_install_script(info),
             has_provenance(info), len(info.get("dependencies") or {})),
        )
        count += 1
    conn.commit()
    conn.close()
    return count

if __name__ == "__main__":
    n = save_releases(PACKAGE, fetch_package(PACKAGE))
    print(f"Saved {n} releases of {PACKAGE} to driftguard.db")