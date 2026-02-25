"""Extract YouTube/Google cookies from Firefox.
Firefox stores cookies as plain SQLite — no encryption needed.
"""
import glob
import os
import shutil
import sqlite3
import tempfile

OUTPUT = r"c:\100star\merge-video\cookies.txt"

# Find largest cookies.sqlite across all Firefox profiles
profiles_dir = os.path.join(os.environ["APPDATA"], "Mozilla", "Firefox", "Profiles")
all_cookies = glob.glob(os.path.join(profiles_dir, "*", "cookies.sqlite"))

if not all_cookies:
    print("❌ No cookies.sqlite found in any Firefox profile")
    print("   Open Firefox, go to youtube.com and log in first")
    exit(1)

# Pick the largest one (most likely the active profile)
cookies_db = max(all_cookies, key=os.path.getsize)

print(f"📂 Using: {cookies_db}")

# Copy DB (Firefox may lock it)
tmp = tempfile.mktemp(suffix=".sqlite")
shutil.copy2(cookies_db, tmp)

conn = sqlite3.connect(tmp)
rows = conn.execute(
    "SELECT host, name, value, path, expiry, isSecure, isHttpOnly "
    "FROM moz_cookies WHERE host LIKE '%youtube%' OR host LIKE '%google%'"
).fetchall()
conn.close()
os.unlink(tmp)

if not rows:
    print("❌ No YouTube/Google cookies found. Log into youtube.com in Firefox first!")
    exit(1)

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("# Netscape HTTP Cookie File\n")
    f.write("# Extracted from Firefox\n\n")
    for host, name, value, path, expiry, secure, httponly in rows:
        flag = "TRUE" if host.startswith(".") else "FALSE"
        sec = "TRUE" if secure else "FALSE"
        f.write(f"{host}\t{flag}\t{path}\t{sec}\t{expiry}\t{name}\t{value}\n")

print(f"✅ {len(rows)} cookies saved to {OUTPUT}")
