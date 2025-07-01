# ⚡️ 1 M-hand Performance Upgrade (June 2025)

We hit the wall at ~300 k hands because every API request was
re-aggregating **8.8 million rows** in `actions`.  
Fix: **pre-compute** the heavy stuff once per ETL cycle and serve tiny tables.

## What’s new

| Item | File/endpoint | Purpose |
|------|---------------|---------|
| **8_materialise_dashboard.py** | `scrape_hh/scripts/8_materialise_dashboard.py` | Runs after script 7, builds three materialised tables + helper indexes |
| `dashboard_summary` | 1 row | Global totals for `/api/dashboard-summary` |
| `top25_players` | 25 rows | Already-aggregated leaderboard for the same endpoint |
| `player_summary` | 1 row / player (≈ 259 rows) | Powers `/api/players`, `/api/players/new`, `/api/player/{id}/stats` |
| Three indexes | created inside script 8 | keep ad-hoc lookups instant |
| **Updated endpoints** | `app.py` | now read the tiny tables, 200 ms instead of 120 s |

### Typical latencies (1 079 k hand test DB, local laptop)

| Endpoint | Before | After |
|----------|--------|-------|
| `/api/dashboard-summary` | **132 s** | **0.2 s** |
| `/api/players` (search box) | N/A (heavy) | **90 ms** |
| `/api/player/{id}/stats` | ~8 s | **80 ms** (uses materialised row, falls back if missing) |
| `/api/players/new` | new | **~250 ms** with sort+pagination |

---

## 1 minute upgrade guide

### 0. Pull the branch

```bash
git pull origin perf-materialised
poetry install     # or pip install -r requirements.txt
````

### 1. Run the ETL incl. the new step

```bash
python scrape_hh/scripts/1_build_heavy_analysis.py     # as before …
…
python scrape_hh/scripts/7_input_scores.py
python scrape_hh/scripts/8_materialise_dashboard.py    # NEW – 1-2 s
```

> **💡 You do NOT need to change `run_combined.py`.**
> It already autoloads `1_*` … `9_*` scripts.
> When you push, Render will detect `8_*` and run it automatically after every scrape batch.

### 2. Start the API

```bash
python start_server.py          # uvicorn with 2 workers
# or: uvicorn app:app --reload
```

### 3. Smoke tests

```bash
# Global dashboard (instant):
curl http://localhost:8000/api/dashboard-summary | jq .

# Table / paging demo:
curl 'http://localhost:8000/api/players/new?sort_by=vpip&order=asc&limit=15&page=2' | jq .

# Single player stats (materialised row):
curl http://localhost:8000/api/player/coinpoker-454403/stats | jq .
```

---

## Deploying to **Render**

1. Push the branch – no extra env vars needed.
2. First scrape cycle runs scripts 1-8 (you’ll see `🎯 Materialising summary tables` in the logs).
3. Hit `<YOUR-SERVICE-URL>/api/dashboard-summary` – should be ≤ 300 ms.

---

## DIY SQL cheat-sheet

You can query the new tables directly from a notebook or DB viewer:

```sql
-- instant totals
SELECT * FROM dashboard_summary;

-- top 25 (already sorted by hands_played desc)
SELECT * FROM top25_players;

-- full leaderboard – sort any way you like:
SELECT player_id,
       total_hands AS hands_played,
       ROUND(vpip_cnt*100.0/preflop_actions,1) AS vpip,
       ROUND(pfr_cnt*100.0/preflop_actions,1) AS pfr,
       avg_preflop_score,
       avg_postflop_score
FROM   player_summary
ORDER  BY vpip DESC
LIMIT  50 OFFSET 50;         -- page 2, 50 rows/page
```

Want more columns (e.g. **“intention score”**)?

* Add them to the big CTE in `8_materialise_dashboard.py`
* Rerun the script – it recreates the tables in < 2 s.
* Expose the new field in the endpoint or UI.

---

## FAQ

* **Does the dashboard refresh automatically?**
  Yes. Every time the scraper finishes a batch and script 7 runs, script 8
  recreates the three tiny tables.

* **Do I need to keep the old heavy queries?**
  We left them in as a *fallback* (`player_stats` still works on very small DBs),
  but they’re no longer executed on big databases.

* **What if a column is NULL in `player_summary`?**
  Endpoints round / default to 0 so the frontend won’t crash.
