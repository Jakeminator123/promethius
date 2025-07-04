# app.py - FastAPI backend för prom-projektet
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import logging
from typing import Optional
from queries import (
    # Main queries
    get_dashboard_summary,
    get_top_players_table,
    get_all_players_for_comparison,
    search_hands_advanced,
    get_betting_vs_strength_data,
    get_player_top_opponents,
    get_player_intentions_radar,
    get_player_recent_hands,
    get_hand_detailed_view,
    # Legacy queries
    get_top_players_by_hands,
    get_player_stats,
    get_player_comparison,
    search_player_hands,
    # Advanced comparison queries
    get_segmented_player_data,
    get_segment_hands,
    get_segment_distribution,
    get_available_filters
)
# Import with alias to avoid naming conflict
from queries.dashboard_queries import dash_summary_new, player_row_new, player_rows_new, top_players_new
from queries.player_queries import get_player_detailed_stats as get_detailed_player_stats, debug_bb100_calculation
from queries.db_connection import execute_query
from queries.ai_analysis import analyze_player, analyze_multiple_players, get_ai_status
import sqlite3
import re, datetime

# Setup logging (undvik dubbla handlers)
import logging
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )
log = logging.getLogger("prom-app")

# FastAPI app
app = FastAPI(
    title="Prom Poker Analytics",
    description="Professional Poker Analysis API",
    version="1.0.0"
)

# CORS för frontend utveckling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    token: str | None = None
    message: str | None = None

class PlayerStats(BaseModel):
    player_id: str
    hands_played: int
    winrate_bb100: float
    vpip: float
    pfr: float

# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from queries.db_connection import is_heavy_analysis_ready
    
    db_ready = is_heavy_analysis_ready()
    
    return {
        "status": "healthy", 
        "service": "prom-app",
        "database_ready": db_ready,
        "message": "Database ready for queries" if db_ready else "Database still being built - scraping in progress"
    }

@app.post("/api/create-materialized-tables")
async def create_materialized_tables_endpoint(bg_tasks: BackgroundTasks):
    """Trigger creation of materialized tables in the background to avoid blocking the API thread."""

    def _run_builder() -> None:
        try:
            import subprocess, sys
            from pathlib import Path
            from utils.paths import HEAVY_DB

            script_path = Path(__file__).parent / "scrape_hh" / "scripts" / "8_materialise_dashboard.py"
            if not script_path.exists():
                log.error("Script 8 not found – cannot materialise dashboard")
                return

            log.info("[BG] Starting dashboard materialisation …")
            proc = subprocess.run(
                [sys.executable, str(script_path), "--db", str(HEAVY_DB)],
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0:
                log.info("[BG] Materialised tables created successfully")
            else:
                log.error(f"[BG] Materialisation failed: {proc.stderr}")
        except Exception as e_bg:
            log.error(f"[BG] Materialisation crashed: {e_bg}")

    # queue background task and return immediately
    bg_tasks.add_task(_run_builder)
    return {"success": True, "message": "Materialisation started in background"}

# ─────────────────────────────────────────────────────────────
# Startup: ensure helpful indexes exist to speed up aggregations
# ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def ensure_sqlite_indexes() -> None:
    """Create indexes in heavy_analysis.db if they don't exist to speed up materialisation queries."""
    try:
        from utils.paths import HEAVY_DB
        if not HEAVY_DB.exists():
            return  # DB not yet present on first startup

        idx_statements = [
            "CREATE INDEX IF NOT EXISTS idx_hands_player ON hands(player_id)",
            "CREATE INDEX IF NOT EXISTS idx_hands_date   ON hands(play_date)",
            "CREATE INDEX IF NOT EXISTS idx_actions_player ON actions(player_id)",
        ]

        conn = sqlite3.connect(str(HEAVY_DB))
        cur = conn.cursor()
        for stmt in idx_statements:
            try:
                cur.execute(stmt)
            except sqlite3.OperationalError:
                # Table might not exist yet – ignore and continue
                pass
        conn.commit()
        conn.close()
        log.info("Ensured basic indexes in heavy_analysis.db")
    except Exception as e:
        log.error(f"Failed to create indexes: {e}")

@app.post("/api/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authentication endpoint"""
    if request.username == "test" and request.password == "test":
        return LoginResponse(
            success=True,
            token="dummy-token-12345",
            message="Login successful"
        )
    return LoginResponse(
        success=False,
        message="Invalid username or password"
    )

@app.get("/api/dashboard-summary")
async def get_dashboard_data(date: str = ""):
    """Get dashboard summary from heavy_analysis.db - showing 25 top players"""
    from queries.db_connection import is_heavy_analysis_ready
    
    # Check if database is ready
    if not is_heavy_analysis_ready():
        return {
            "total_players": 0,
            "total_hands": 0,
            "avg_vpip": 0,
            "avg_pfr": 0,
            "avg_j_score": 0,
            "avg_preflop_score": 0,
            "avg_postflop_score": 0,
            "total_actions": 0,
            "top_players": [],
            "database_status": "building",
            "message": "Database is being built - scraping and processing in progress. Please wait..."
        }
    
    try:
        # Om datum angivet: peka utils.paths till arkivreferenser
        if date:
            from utils.db_rotation import get_db_paths_for_date
            poker_db_path, heavy_db_path = get_db_paths_for_date(date)

            # Monkeypatch db_connection så att rätt fil öppnas
            import queries.db_connection as dbc  # type: ignore
            setattr(
                dbc,
                "DB_FILES",
                {
                    "poker.db": poker_db_path,
                    "heavy_analysis.db": heavy_db_path,
                },
            )

        # Check if materialized tables exist, if not create them
        try:
            log.info("Materialized tables missing. Checking lock file before spawning builder …")
            import subprocess, sys, os
            from pathlib import Path

            script_path = Path(__file__).parent / "scrape_hh" / "scripts" / "8_materialise_dashboard.py"
            lock_path   = script_path.with_suffix(".lock")  # e.g. 8_materialise_dashboard.lock

            # Om låsfil existerar – någon annan process bygger redan → svara att DB håller på att materialiseras
            if lock_path.exists():
                log.warning("Materialization already running – returning 'materializing' status")
                return {
                    "total_players": 0,
                    "total_hands": 0,
                    "avg_vpip": 0,
                    "avg_pfr": 0,
                    "avg_j_score": 0,
                    "avg_preflop_score": 0,
                    "avg_postflop_score": 0,
                    "total_actions": 0,
                    "top_players": [],
                    "database_status": "materializing",
                    "message": "Creating summary tables, please wait..."
                }

            # Försök skapa låsfil atomärt
            try:
                lock_path.touch(exist_ok=False)
            except FileExistsError:
                # Race-condition safeguard
                log.warning("Materialization lock obtained by another worker just now – abort spawn")
                return {
                    "total_players": 0,
                    "total_hands": 0,
                    "avg_vpip": 0,
                    "avg_pfr": 0,
                    "avg_j_score": 0,
                    "avg_preflop_score": 0,
                    "avg_postflop_score": 0,
                    "total_actions": 0,
                    "top_players": [],
                    "database_status": "materializing",
                    "message": "Creating summary tables, please wait..."
                }

            try:
                # Use the correct database path from utils.paths
                from utils.paths import HEAVY_DB
                result = subprocess.run(
                    [sys.executable, str(script_path), "--db", str(HEAVY_DB)],
                    capture_output=True, text=True
                )

                if result.returncode == 0:
                    log.info("Materialized tables created successfully")
                    summary = dash_summary_new()  # ny hämtning
                    if summary is None:
                        summary = {}
                else:
                    log.error(f"Materialization failed: {result.stderr}")
                    return {
                        "total_players": 0,
                        "total_hands": 0,
                        "avg_vpip": 0,
                        "avg_pfr": 0,
                        "avg_j_score": 0,
                        "avg_preflop_score": 0,
                        "avg_postflop_score": 0,
                        "total_actions": 0,
                        "top_players": [],
                        "database_status": "materializing_error",
                        "message": "Failed to build summary tables"
                    }
            finally:
                # Ta bort låset oavsett utfall
                try:
                    lock_path.unlink(missing_ok=True)  # py>=3.8
                except Exception as e_rm:
                    log.error(f"Could not remove materialization lock: {e_rm}")
        except Exception as e:
            if "no such table" in str(e) or "no such column" in str(e):
                # Run script 8 to create materialized tables
                log.info("Materialized tables missing, creating them now...")
                import subprocess
                import sys
                from pathlib import Path
                
                script_path = Path(__file__).parent / "scrape_hh" / "scripts" / "8_materialise_dashboard.py"
                if script_path.exists():
                    # Use the correct database path from utils.paths
                    from utils.paths import HEAVY_DB
                    result = subprocess.run(
                        [sys.executable, str(script_path), "--db", str(HEAVY_DB)], 
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        log.info("Materialized tables created successfully")
                        # Try again
                        summary = dash_summary_new()
                        if summary is None:
                            summary = {}
                    else:
                        log.error(f"Failed to create materialized tables: {result.stderr}")
                        # Return empty data instead of crashing
                        return {
                            "total_players": 0,
                            "total_hands": 0,
                            "avg_vpip": 0,
                            "avg_pfr": 0,
                            "avg_j_score": 0,
                            "avg_preflop_score": 0,
                            "avg_postflop_score": 0,
                            "total_actions": 0,
                            "top_players": [],
                            "database_status": "materializing",
                            "message": "Creating summary tables, please wait..."
                        }
                else:
                    log.error(f"Script 8 not found at {script_path}")
                    raise
            else:
                raise
        
        # Get top 25 players - use materialized table if available, else fallback
        try:
            top_players = top_players_new(25)
        except sqlite3.OperationalError as e:
            if "no such table: top25_players" in str(e):
                log.warning("top25_players table not yet created - using fallback query")
                try:
                    top_players = get_top_players_table(25)
                except Exception as fallback_error:
                    log.error(f"Fallback query also failed: {fallback_error}")
                    top_players = []
            else:
                raise
        
        # Ensure summary is a dictionary
        if summary is None:
            summary = {}
            
        # Safe rounding helper
        def safe_round(value, decimals=1):
            if value is None:
                return 0
            try:
                return round(value, decimals)
            except TypeError:
                return 0
        
        return {
            "total_players": summary.get('total_players', 0),
            "total_hands": summary.get('total_hands', 0),
            "avg_vpip": safe_round(summary.get('avg_vpip', 0)),
            "avg_pfr": safe_round(summary.get('avg_pfr', 0)),
            "avg_j_score": safe_round(summary.get('avg_j_score', 0)),
            "avg_preflop_score": safe_round(summary.get('avg_preflop_score', 0)),
            "avg_postflop_score": safe_round(summary.get('avg_postflop_score', 0)),
            "total_actions": summary.get('total_actions', 0),
            "top_players": top_players,
            "database_status": "connected" if summary and top_players else "missing_data"
        }
    except Exception as e:
        log.error(f"Error fetching dashboard data: {e}")
        # Return empty data if database not available
        return {
            "total_players": 0,
            "total_hands": 0,
            "avg_vpip": 0,
            "avg_pfr": 0,
            "avg_j_score": 0,
            "avg_preflop_score": 0,
            "avg_postflop_score": 0,
            "total_actions": 0,
            "top_players": [],
            "database_status": "error",
            "error_message": str(e)
        }

@app.get("/api/players")
async def get_players_for_comparison(search: str = "", limit: int = 50):
    """Get players for comparison from heavy_analysis.db"""
    try:
        players = player_rows_new(search, limit)
        return {"players": players}
    except Exception as e:
        log.error(f"Error fetching players: {e}")
        return {"players": []}
    
@app.get("/api/players/new")
async def list_players(
    sort_by: str = Query("hands_played", description="Which column to sort by"),
    order: str = Query("desc", regex="^(asc|desc)$", description="asc or desc"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(25, ge=1, le=100, description="Rows per page"),
):
    """
    Leaderboard of all players, sorted + paginated.
    """

    ALLOWED = {
        "hands_played",        # ← human-friendly alias
        "total_actions",
        "vpip",
        "pfr",
        "avg_j_score",
        "avg_preflop_score",
        "avg_postflop_score",
    }
    if sort_by not in ALLOWED:
        sort_by = "hands_played"

    order_sql = "ASC" if order.lower() == "asc" else "DESC"
    offset = (page - 1) * limit

    # map human-friendly field → real SQL expression
    if sort_by == "hands_played":
        order_expr = "hands_played"               # real column name
    else:
        order_expr = sort_by                      # column exists as-is

    query = f"""
        SELECT
            player_id,
            nickname,
            hands_played,
            total_actions,
            avg_j_score,
            vpip,
            pfr,
            avg_preflop_score,
            avg_postflop_score
        FROM player_summary
        ORDER BY {order_expr} {order_sql}
        LIMIT ? OFFSET ?
    """

    rows = execute_query(query, (limit, offset), db_name="heavy_analysis.db")

    total = execute_query(
        "SELECT COUNT(*) AS cnt FROM player_summary",
        db_name="heavy_analysis.db"
    )[0]["cnt"]

    return {
        "page": page,
        "limit": limit,
        "sort_by": sort_by,
        "order": order_sql.lower(),
        "total": total,
        "players": rows,
    }


@app.get("/api/hand-history/search")
async def search_hand_history(
    player: str = "", 
    min_pot: int = 0, 
    max_pot: int = 1000,
    street: str = "",
    position: str = "",
    game_type: str = "",  # "cash", "mtt", eller ""
    limit: int = 50
):
    """Search hand histories from heavy_analysis.db"""
    try:
        hands = search_hands_advanced(
            player_filter=player,
            min_pot=min_pot,
            max_pot=max_pot,
            street_filter=street,
            position_filter=position,
            game_type=game_type,
            limit=limit
        )
        
        return {
            "hands": hands,
            "total_count": len(hands)
        }
    except Exception as e:
        log.error(f"Error searching hands: {e}")
        return {"hands": [], "total_count": 0}

@app.get("/api/player/{player_id}/stats")
async def get_player_stats_endpoint(player_id: str):
    """Get basic stats for a specific player."""
    # Convert player ID format (coinpoker/123 -> coinpoker-123)
    player_id_normalized = player_id.replace('/', '-')
    
    # 1) Try the materialized table first
    row = player_row_new(player_id_normalized)
    if row:
        return {
            "player_id":          row["player_id"],
            "nickname":           row.get("nickname", ""),
            "hands_played":       row.get("hands_played", 0),
            "total_actions":      row.get("total_actions", 0),
            "avg_j_score":        round(row["avg_j_score"], 1) if row.get("avg_j_score") is not None else 0.0,
            "vpip":               row.get("vpip", 0.0),
            "pfr":                row.get("pfr", 0.0),
            "avg_preflop_score":  row.get("avg_preflop_score"),
            "avg_postflop_score": row.get("avg_postflop_score"),
        }

    try:
        stats = get_player_stats(player_id_normalized)
        return stats if stats else {"error": "Player not found"}
    except Exception as e:
        log.error(f"Error fetching player stats fallback: {e}")
        return {"error": "Failed to fetch player stats"}

@app.get("/api/compare-players")
async def compare_two_players(player1: str, player2: str):
    """Compare two players head-to-head"""
    try:
        # Convert player ID format (coinpoker/123 -> coinpoker-123)
        player1_normalized = player1.replace('/', '-')
        player2_normalized = player2.replace('/', '-')
        comparison = get_player_comparison(player1_normalized, player2_normalized)
        return comparison
    except Exception as e:
        log.error(f"Error comparing players: {e}")
        return {"error": "Failed to compare players"}

@app.get("/api/betting-vs-strength")
async def get_betting_vs_strength_chart_data(
    player: str = "",
    streets: str = "flop,turn,river",
    actions: str = "bet,2bet,3bet,checkraise,donk,probe,lead,cont",
    limit: int = 1000
):
    """Get betting size vs hand strength data for scatter plot visualization"""
    try:
        # Parse comma-separated parameters
        street_list = [s.strip() for s in streets.split(",") if s.strip()] if streets else None
        action_list = [a.strip() for a in actions.split(",") if a.strip()] if actions else None
        
        # Convert player ID format (coinpoker/123 -> coinpoker-123)
        player_id = player.replace('/', '-') if player else None
        
        # Get the data
        data = get_betting_vs_strength_data(
            player_id=player_id,
            streets=street_list,
            action_labels=action_list,
            limit=limit
        )
        
        # Get top opponents and intentions if player is specified
        top_opponents = []
        player_intentions = []
        if player_id:
            top_opponents = get_player_top_opponents(player_id, 3)
            player_intentions = get_player_intentions_radar(player_id, 10)
        
        # Group data for easier frontend handling
        summary = {
            "total_data_points": len(data),
            "streets": list(set(d['street'] for d in data)),
            "action_labels": list(set(d['action_label'] for d in data)),
            "hand_strength_range": {
                "min": min((d['hand_strength'] for d in data), default=0),
                "max": max((d['hand_strength'] for d in data), default=100)
            },
            "bet_size_range": {
                "min": min((d['bet_size_pct'] for d in data), default=0),
                "max": max((d['bet_size_pct'] for d in data), default=150)
            }
        }
        
        return {
            "success": True,
            "data": data,
            "summary": summary,
            "top_opponents": top_opponents,
            "player_intentions": player_intentions,
            "player_filter": player if player else "All players",
            "filters": {
                "streets": street_list,
                "actions": action_list,
                "limit": limit
            }
        }
    except Exception as e:
        log.error(f"Error fetching betting vs strength data: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "summary": {}
        }

@app.get("/api/player-recent-hands")
async def get_player_recent_hands_api(player_id: str, limit: int = 20):
    """Get player's recent hands"""
    try:
        # Convert player ID format (coinpoker/123 -> coinpoker-123)
        player_id_normalized = player_id.replace('/', '-')
        log.info(f"Getting recent hands for player: {player_id_normalized}, limit: {limit}")
        data = get_player_recent_hands(player_id_normalized, limit)
        return {"success": True, "data": data}
    except Exception as e:
        log.error(f"Error getting recent hands: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/player-detailed-stats-comprehensive")
async def get_player_detailed_stats_comprehensive(player_id: str):
    """Get comprehensive player statistics"""
    try:
        # Convert player ID format (coinpoker/123 -> coinpoker-123)
        player_id_normalized = player_id.replace('/', '-')
        log.info(f"Getting detailed stats for player: {player_id_normalized}")
        data = get_detailed_player_stats(player_id_normalized)
        return {"success": True, "data": data}
    except Exception as e:
        log.error(f"Error getting detailed stats: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/hand-detailed-view")
async def get_hand_detailed_view_api(hand_id: str):
    """Get comprehensive hand details"""
    try:
        log.info(f"Getting detailed view for hand: {hand_id}")
        data = get_hand_detailed_view(hand_id)
        return {"success": True, "data": data}
    except Exception as e:
        log.error(f"Error getting hand details: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/hand-normalized-json")
async def get_hand_normalized_json(hand_id: str, date: str = ""):
    """Get hand JSON with normalized values (amounts adjusted by chip_value)"""
    try:
        log.info(f"Getting normalized JSON for hand: {hand_id}")
        
        # Determine which database to use
        db_path = "poker.db"
        if date:
            from utils.paths import ARCHIVE_DIR
            archive_path = ARCHIVE_DIR / date / "poker.db"
            if archive_path.exists():
                db_path = str(archive_path)
        
        # Get raw hand data from poker.db
        query = """
        SELECT json_data, chip_value_in_displayed_currency
        FROM hand 
        WHERE id = ?
        """
        
        result = execute_query(query, (hand_id,), db_name=db_path)
        
        if not result:
            return {"success": False, "error": "Hand not found"}
        
        import json
        raw_data = json.loads(result[0]['json_data'])
        chip_value = float(result[0]['chip_value_in_displayed_currency'])
        
        # Apply normalization if chip_value is not 1
        if chip_value != 1.0:
            # Normalize amounts in various fields
            fields_to_normalize = [
                'big_blind', 'small_blind', 'ante', 'min_bet', 'max_bet',
                'pot', 'total_pot', 'main_pot', 'side_pots'
            ]
            
            def normalize_value(value):
                if isinstance(value, (int, float)):
                    return round(value * chip_value, 2)
                return value
            
            def normalize_dict(data):
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key in fields_to_normalize:
                            data[key] = normalize_value(value)
                        elif key == 'seats' and isinstance(value, list):
                            # Normalize seat stacks
                            for seat in value:
                                if 'stack' in seat:
                                    seat['stack'] = normalize_value(seat['stack'])
                        elif key == 'streets' and isinstance(value, list):
                            # Normalize street pots and bets
                            for street in value:
                                if 'pot' in street:
                                    street['pot'] = normalize_value(street['pot'])
                                if 'actions' in street:
                                    for action in street['actions']:
                                        if 'amount' in action:
                                            action['amount'] = normalize_value(action['amount'])
                        elif isinstance(value, (dict, list)):
                            normalize_dict(value)
                elif isinstance(data, list):
                    for item in data:
                        normalize_dict(item)
            
            normalize_dict(raw_data)
        
        return {
            "success": True,
            "data": raw_data,
            "chip_value": chip_value,
            "was_normalized": chip_value != 1.0
        }
        
    except Exception as e:
        log.error(f"Error getting normalized hand JSON: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/debug/bb100")
async def debug_bb100():
    """Debug BB/100 calculation to understand why it shows 0"""
    try:
        log.info("Running BB/100 debug...")
        results = debug_bb100_calculation(limit=10)
        
        # Also check the materialized view
        materialized_check = execute_query(
            """
            SELECT player_id, nickname, total_hands, winrate_bb100
            FROM top25_players
            WHERE total_hands > 10
            ORDER BY total_hands DESC
            LIMIT 10
            """, 
            db_name='heavy_analysis.db'
        )
        
        return {
            "success": True,
            "debug_results": results,
            "materialized_view": materialized_check,
            "message": "Check server logs for detailed output"
        }
    except Exception as e:
        log.error(f"BB/100 debug failed: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/advanced-comparison/filters")
async def get_comparison_filters():
    """Get available filter options for advanced comparison"""
    try:
        filters = get_available_filters()
        return {"success": True, "filters": filters}
    except Exception as e:
        log.error(f"Error getting comparison filters: {e}")
        return {"success": False, "error": str(e), "filters": {}}

@app.get("/api/advanced-comparison/segment")
async def get_player_segment(
    player_id: str,
    comparison_player_id: str = "",
    # Filter parameters
    street: str = "",
    position: str = "",
    action_label: str = "",
    min_j_score: Optional[float] = None,
    max_j_score: Optional[float] = None,
    min_preflop_score: Optional[float] = None,
    max_preflop_score: Optional[float] = None,
    min_postflop_score: Optional[float] = None,
    max_postflop_score: Optional[float] = None,
    players_left: Optional[int] = None,
    pot_type: str = "",
    size_cat: str = "",
    intention: str = "",
    ip_status: str = ""
):
    """Get segmented player data with population averages and optional comparison player"""
    try:
        # Build filters dict from parameters
        filters = {}
        if street:
            filters['street'] = street
        if position:
            filters['position'] = position
        if action_label:
            filters['action_label'] = action_label
        if min_j_score is not None:
            filters['min_j_score'] = min_j_score
        if max_j_score is not None:
            filters['max_j_score'] = max_j_score
        if min_preflop_score is not None:
            filters['min_preflop_score'] = min_preflop_score
        if max_preflop_score is not None:
            filters['max_preflop_score'] = max_preflop_score
        if min_postflop_score is not None:
            filters['min_postflop_score'] = min_postflop_score
        if max_postflop_score is not None:
            filters['max_postflop_score'] = max_postflop_score
        if players_left is not None:
            filters['players_left'] = players_left
        if pot_type:
            filters['pot_type'] = pot_type
        if size_cat:
            filters['size_cat'] = size_cat
        if intention:
            filters['intention'] = intention
        if ip_status:
            filters['ip_status'] = ip_status
        
        log.info(f"Getting segmented data for player {player_id} with filters: {filters}")
        
        data = get_segmented_player_data(
            player_id=player_id,
            comparison_player_id=comparison_player_id if comparison_player_id else None,
            filters=filters if filters else {}
        )
        
        return {"success": True, "data": data}
    except Exception as e:
        log.error(f"Error getting segmented player data: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/advanced-comparison/hands")
async def get_segment_hand_list(
    player_id: str,
    # Same filter parameters as above
    street: str = "",
    position: str = "",
    action_label: str = "",
    min_j_score: Optional[float] = None,
    max_j_score: Optional[float] = None,
    min_preflop_score: Optional[float] = None,
    max_preflop_score: Optional[float] = None,
    min_postflop_score: Optional[float] = None,
    max_postflop_score: Optional[float] = None,
    players_left: Optional[int] = None,
    pot_type: str = "",
    size_cat: str = "",
    intention: str = "",
    ip_status: str = "",
    limit: int = 20
):
    """Get specific hands matching the segment filters"""
    try:
        # Build filters dict
        filters = {}
        if street:
            filters['street'] = street
        if position:
            filters['position'] = position
        if action_label:
            filters['action_label'] = action_label
        if min_j_score is not None:
            filters['min_j_score'] = min_j_score
        if max_j_score is not None:
            filters['max_j_score'] = max_j_score
        if min_preflop_score is not None:
            filters['min_preflop_score'] = min_preflop_score
        if max_preflop_score is not None:
            filters['max_preflop_score'] = max_preflop_score
        if min_postflop_score is not None:
            filters['min_postflop_score'] = min_postflop_score
        if max_postflop_score is not None:
            filters['max_postflop_score'] = max_postflop_score
        if players_left is not None:
            filters['players_left'] = players_left
        if pot_type:
            filters['pot_type'] = pot_type
        if size_cat:
            filters['size_cat'] = size_cat
        if intention:
            filters['intention'] = intention
        if ip_status:
            filters['ip_status'] = ip_status
        
        hands = get_segment_hands(player_id, filters, limit)
        
        return {"success": True, "hands": hands, "count": len(hands)}
    except Exception as e:
        log.error(f"Error getting segment hands: {e}")
        return {"success": False, "error": str(e), "hands": []}

@app.get("/api/advanced-comparison/distribution")
async def get_segment_distribution_data(
    group_by: str = "player_id",
    # Filter parameters
    street: str = "",
    position: str = "",
    action_label: str = "",
    min_j_score: Optional[float] = None,
    max_j_score: Optional[float] = None,
    players_left: Optional[int] = None,
    pot_type: str = "",
    size_cat: str = "",
    intention: str = "",
    ip_status: str = ""
):
    """Get distribution of players/actions for a given segment"""
    try:
        # Build filters dict
        filters = {}
        if street:
            filters['street'] = street
        if position:
            filters['position'] = position
        if action_label:
            filters['action_label'] = action_label
        if min_j_score is not None:
            filters['min_j_score'] = min_j_score
        if max_j_score is not None:
            filters['max_j_score'] = max_j_score
        if players_left is not None:
            filters['players_left'] = players_left
        if pot_type:
            filters['pot_type'] = pot_type
        if size_cat:
            filters['size_cat'] = size_cat
        if intention:
            filters['intention'] = intention
        if ip_status:
            filters['ip_status'] = ip_status
        
        distribution = get_segment_distribution(filters, group_by)
        
        return {"success": True, "distribution": distribution, "group_by": group_by}
    except Exception as e:
        log.error(f"Error getting segment distribution: {e}")
        return {"success": False, "error": str(e), "distribution": []}

# TODO: Implement advanced comparison when ready
# @app.get("/api/advanced-comparison")
# async def advanced_comparison(
#     player_names: str = Query(..., description="Comma-separated player names"),
#     date_start: str = Query(None),
#     date_end: str = Query(None)
# ):
#     """Get advanced comparison data for multiple players"""
#     players_list = [p.strip() for p in player_names.split(',')]
#     return get_advanced_comparison_data(players_list, date_start, date_end)

# ── AI Analysis endpoints ─────────────────────────────────────────────
@app.get("/api/ai/status")
async def ai_status():
    """Check AI service availability"""
    return get_ai_status()


@app.post("/api/ai/analyze-player")
async def analyze_single_player(player_data: dict):
    """Analyze a single player using AI"""
    return analyze_player(player_data)


@app.post("/api/ai/analyze-table")
async def analyze_table(request: dict):
    """Analyze multiple players for table dynamics"""
    players = request.get("players", [])
    max_players = request.get("max_players", 5)
    return analyze_multiple_players(players, max_players)

@app.get("/api")
async def api_root():
    """API root with documentation"""
    return {
        "message": "Prom Poker Analytics API",
        "docs": "/docs",
        "database": "heavy_analysis.db (primary), poker.db (raw data)",
        "endpoints": [
            "/api/login",
            "/api/dashboard-summary", 
            "/api/players",
            "/api/hand-history/search",
            "/api/player/{player_id}/stats",
            "/api/compare-players",
            "/api/betting-vs-strength",
            "/api/player-recent-hands",
            "/api/player-detailed-stats-comprehensive",
            "/api/hand-detailed-view",
            "/api/hand-normalized-json",
            "/api/advanced-comparison/filters",
            "/api/advanced-comparison/segment",
            "/api/advanced-comparison/hands",
            "/api/advanced-comparison/distribution",
            "/api/available-dates"
        ]
    }

@app.get("/api/available-dates")
async def list_available_dates() -> dict:
    """Returnera ISO-datum (YYYY-MM-DD) för vilka både poker.db och heavy_analysis.db finns i archive."""
    from utils.paths import ARCHIVE_DIR
    dates: list[str] = []

    date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    if not ARCHIVE_DIR.exists():
        return {"dates": []}

    for sub in ARCHIVE_DIR.iterdir():
        if sub.is_dir() and date_re.match(sub.name):
            p = sub / "poker.db"
            h = sub / "heavy_analysis.db"
            if p.exists() and h.exists():
                dates.append(sub.name)

    # sort descending (newest first)
    dates.sort(reverse=True)
    return {"dates": dates}

# Serve frontend if dist folder exists (both dev and production)
# IMPORTANT: This must come AFTER all API routes
frontend_path = Path(__file__).resolve().parent / "frontend" / "dist"
if frontend_path.exists():
    try:
        # Use absolute path for Windows compatibility
        app.mount("/", StaticFiles(directory=str(frontend_path.absolute()), html=True), name="static")
        log.info(f"✅ Frontend mounted from: {frontend_path.absolute()}")
        
        # Verify index.html exists
        index_file = frontend_path / "index.html"
        if index_file.exists():
            log.info(f"✅ index.html found at: {index_file.absolute()}")
        else:
            log.error(f"❌ index.html NOT found at: {index_file.absolute()}")
    except Exception as e:
        log.error(f"❌ Failed to mount frontend: {e}")
else:
    log.warning(f"❌ Frontend dist not found at {frontend_path.absolute()} - run 'npm run build' in frontend/")

# ---
# Removed standalone server start to undvika dubbla Uvicorn-instanser.
# Webbserver startas nu enbart via main.py eller externt `uvicorn app:app`. 