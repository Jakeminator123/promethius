#!/usr/bin/env python3
import os, re, requests, sys
from pathlib import Path
from bs4 import BeautifulSoup   # pip install beautifulsoup4

BASE   = "https://prod.battle-backend.prometheuspoker.com"
ORG    = "coinpoker"
EVENT  = "default"
DATE   = sys.argv[1] if len(sys.argv) > 1 else "2025-01-15"   # pick any

USER = os.getenv("BATTLE_API_USERNAME")
PWD  = os.getenv("BATTLE_API_PASSWORD")
print(USER, PWD)
assert USER and PWD, "Set BATTLE_API_USERNAME/PASSWORD first"

sess = requests.Session()

# --- login the same way as the scraper ---------------------------------
login_html = sess.get(f"{BASE}/admin/login/?next=/admin/").text
token      = BeautifulSoup(login_html, "html.parser").find("input", {"name": "csrfmiddlewaretoken"}).get("value")

resp = sess.post(f"{BASE}/admin/login/",
                 data={"username":USER, "password":PWD,
                       "csrfmiddlewaretoken":token, "next":"/admin/"},
                 headers={"Referer":f"{BASE}/admin/login/?next=/admin/"},
                 allow_redirects=False)
resp.raise_for_status()
print("✅ Logged in")

# --- pull the first page of hands --------------------------------------
epi  = f"Ep{DATE}"
url  = f"{BASE}/v1/solver/power_ranking/organizers/{ORG}/events/{EVENT}/episodes/{epi}/hands?limit=5&offset=0"
data = sess.get(url, timeout=30).json()
print(f"Count returned: {len(data.get('results', []))}")
print("First stub(s):", [r.get("stub") for r in data.get("results", [])][:3])
