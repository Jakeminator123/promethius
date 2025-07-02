# app.py - FastAPI backend för prom-projektet
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
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
from queries.player_queries import get_player_detailed_stats as get_detailed_player_stats
from queries.db_connection import execute_query

# Setup logging
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
async def get_dashboard_data():
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
        # Check if materialized tables exist, if not create them
        try:
            summary = dash_summary_new()
        except Exception as e:
            if "no such table" in str(e) or "no such column" in str(e):
                # Run script 8 to create materialized tables
                log.info("Materialized tables missing, creating them now...")
                import subprocess
                import sys
                from pathlib import Path
                
                script_path = Path(__file__).parent / "scrape_hh" / "scripts" / "8_materialise_dashboard.py"
                if script_path.exists():
                    result = subprocess.run([sys.executable, str(script_path)], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        log.info("Materialized tables created successfully")
                        # Try again
                        summary = dash_summary_new()
                    else:
                        log.error(f"Failed to create materialized tables: {result.stderr}")
                        raise
                else:
                    log.error(f"Script 8 not found at {script_path}")
                    raise
            else:
                raise
        
        # Get top 25 players from materialized table
        top_players = top_players_new(25)
        
        return {
            "total_players": summary.get('total_players', 0),
            "total_hands": summary.get('total_hands', 0),
            "avg_vpip": round(summary.get('avg_vpip', 0), 1),
            "avg_pfr": round(summary.get('avg_pfr', 0), 1),
            "avg_j_score": round(summary.get('avg_j_score', 0), 1),
            "avg_preflop_score": round(summary.get('avg_preflop_score', 0), 1),
            "avg_postflop_score": round(summary.get('avg_postflop_score', 0), 1),
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
    # 1) Try the materialized table first
    row = player_row_new(player_id)
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
        stats = get_player_stats(player_id)
        return stats if stats else {"error": "Player not found"}
    except Exception as e:
        log.error(f"Error fetching player stats fallback: {e}")
        return {"error": "Failed to fetch player stats"}

@app.get("/api/compare-players")
async def compare_two_players(player1: str, player2: str):
    """Compare two players head-to-head"""
    try:
        comparison = get_player_comparison(player1, player2)
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
        
        # Get the data
        data = get_betting_vs_strength_data(
            player_id=player if player else None,
            streets=street_list,
            action_labels=action_list,
            limit=limit
        )
        
        # Get top opponents and intentions if player is specified
        top_opponents = []
        player_intentions = []
        if player:
            top_opponents = get_player_top_opponents(player, 3)
            player_intentions = get_player_intentions_radar(player, 10)
        
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
        log.info(f"Getting recent hands for player: {player_id}, limit: {limit}")
        data = get_player_recent_hands(player_id, limit)
        return {"success": True, "data": data}
    except Exception as e:
        log.error(f"Error getting recent hands: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/player-detailed-stats-comprehensive")
async def get_player_detailed_stats_comprehensive(player_id: str):
    """Get comprehensive player statistics"""
    try:
        log.info(f"Getting detailed stats for player: {player_id}")
        data = get_detailed_player_stats(player_id)
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
            "/api/advanced-comparison/filters",
            "/api/advanced-comparison/segment",
            "/api/advanced-comparison/hands",
            "/api/advanced-comparison/distribution"
        ]
    }

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

# Allow running with python app.py
if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable (Render sets this) or default to 8000
    port = int(os.environ.get("PORT", 8000))
    is_render = os.environ.get("RENDER") == "true"
    
    print("🚀 Starting Prom webserver...")
    if is_render:
        print(f"🌐 Running on Render.com on port {port}")
    else:
        print(f"📍 API docs: http://localhost:{port}/docs")
        print(f"🌐 Frontend: http://localhost:{port}")
        print("⏹️  Press Ctrl+C to stop\n")
    
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=not is_render) 