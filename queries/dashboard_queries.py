from .db_connection import execute_query
import logging

log = logging.getLogger(__name__)

def get_dashboard_summary() -> dict:
    """Dashboard main stats from heavy_analysis.db"""
    
    # Check if we have the required table
    try:
        test_query = "SELECT COUNT(*) FROM actions LIMIT 1"
        execute_query(test_query, db_name='heavy_analysis.db')
    except Exception as e:
        log.error(f"Cannot access heavy_analysis.db: {e}")
        return {}
    
    query = """
    SELECT 
        COUNT(DISTINCT a.player_id) as total_players,
        COUNT(DISTINCT a.hand_id) as total_hands,
        AVG(CASE WHEN a.action != 'f' AND a.street = 'preflop' THEN 1.0 ELSE 0.0 END) * 100 as avg_vpip,
        AVG(CASE WHEN a.action = 'r' AND a.street = 'preflop' THEN 1.0 ELSE 0.0 END) * 100 as avg_pfr,
        AVG(a.j_score) as avg_j_score,
        COUNT(a.action_order) as total_actions
    FROM actions a
    WHERE a.player_id IS NOT NULL AND a.player_id != ''
    """
    
    try:
        result = execute_query(query, db_name='heavy_analysis.db')
        return result[0] if result else {}
    except Exception as e:
        log.error(f"Dashboard summary query failed: {e}")
        return {}

def get_top_players_table(limit: int = 25) -> list:
    """Top players for dashboard table from heavy_analysis.db - now showing 25 players with preflop/postflop scores"""
    
    # First check if the required columns exist
    try:
        test_query = "SELECT preflop_score, postflop_score FROM actions LIMIT 1"
        execute_query(test_query, db_name='heavy_analysis.db')
        has_score_columns = True
    except Exception:
        has_score_columns = False
        log.warning("preflop_score/postflop_score columns not found, using fallback query")
    
    if has_score_columns:
        query = """
        SELECT 
            a.player_id,
            a.nickname,
            COUNT(DISTINCT a.hand_id) as hands_played,
            AVG(a.j_score) as avg_j_score,
            
            -- Calculate VPIP: non-fold actions preflop / total preflop opportunities
            AVG(CASE WHEN a.action != 'f' AND a.street = 'preflop' THEN 1.0 ELSE 0.0 END) * 100 as vpip,
            
            -- Calculate PFR: raise actions preflop / total preflop opportunities  
            AVG(CASE WHEN a.action = 'r' AND a.street = 'preflop' THEN 1.0 ELSE 0.0 END) * 100 as pfr,
            
            -- Aggregated skill scores (1-100 scale)
            AVG(a.preflop_score) as avg_preflop_score,
            AVG(a.postflop_score) as avg_postflop_score,
            
            -- Street performance breakdown
            AVG(CASE WHEN a.street = 'preflop' THEN a.j_score ELSE NULL END) as preflop_j_score,
            AVG(CASE WHEN a.street = 'flop' THEN a.j_score ELSE NULL END) as flop_score,
            AVG(CASE WHEN a.street = 'turn' THEN a.j_score ELSE NULL END) as turn_score,
            AVG(CASE WHEN a.street = 'river' THEN a.j_score ELSE NULL END) as river_score,
            
            -- Position stats
            COUNT(CASE WHEN a.position IN ('EP', 'UTG', 'UTG+1') THEN 1 END) as early_pos_hands,
            COUNT(CASE WHEN a.position IN ('MP', 'MP+1', 'MP+2') THEN 1 END) as middle_pos_hands,
            COUNT(CASE WHEN a.position IN ('LP', 'CO', 'BTN') THEN 1 END) as late_pos_hands,
            COUNT(CASE WHEN a.position IN ('SB', 'BB') THEN 1 END) as blind_hands,
            
            -- Score coverage (how many actions have scores)
            COUNT(CASE WHEN a.preflop_score IS NOT NULL THEN 1 END) as preflop_scored_actions,
            COUNT(CASE WHEN a.postflop_score IS NOT NULL THEN 1 END) as postflop_scored_actions,
            
            -- Solver Precision Score: percentage of "y" out of all non-null "solver_best" values
            CASE 
                WHEN COUNT(CASE WHEN a.solver_best IS NOT NULL THEN 1 END) > 0 THEN
                    ROUND(
                        (COUNT(CASE WHEN a.solver_best = 'y' THEN 1 END) * 100.0) / 
                        COUNT(CASE WHEN a.solver_best IS NOT NULL THEN 1 END), 
                        1
                    )
                ELSE NULL 
            END as solver_precision_score,
            
            -- Calldown Accuracy: win rate when calling on river
            CASE 
                WHEN COUNT(CASE WHEN a.street = 'river' AND a.action_label = 'call' THEN 1 END) > 0 THEN
                    ROUND(
                        (COUNT(CASE 
                            WHEN a.street = 'river' 
                            AND a.action_label = 'call' 
                            AND p.money_won > 0 
                            THEN 1 
                        END) * 100.0) / 
                        COUNT(CASE WHEN a.street = 'river' AND a.action_label = 'call' THEN 1 END), 
                        0
                    )
                ELSE NULL 
            END as calldown_accuracy,
            
            -- Bet Deviance: How much player deviates from standard bet sizing (0-100, higher = more deviant)
            CASE 
                WHEN COUNT(CASE WHEN a.action = 'r' AND a.size_frac IS NOT NULL THEN 1 END) > 5 THEN
                    ROUND(
                        AVG(CASE 
                            WHEN a.action = 'r' AND a.size_frac IS NOT NULL THEN
                                ABS(a.size_frac - avg_sizes.avg_size) / NULLIF(avg_sizes.avg_size, 0) * 100
                            ELSE NULL
                        END), 
                        0
                    )
                ELSE NULL 
            END as bet_deviance,
            
            -- Tilt Factor: Performance drop after losses (0-100, higher = more tilt)
            CASE 
                WHEN COUNT(CASE WHEN prev_result.prev_money_won < 0 THEN 1 END) > 5 THEN
                    ROUND(
                        100 - (
                            AVG(CASE WHEN prev_result.prev_money_won < 0 THEN a.j_score ELSE NULL END) / 
                            NULLIF(AVG(CASE WHEN prev_result.prev_money_won >= 0 THEN a.j_score ELSE NULL END), 0)
                        ) * 100,
                        0
                    )
                ELSE NULL 
            END as tilt_factor,
            
            -- Get total winnings and average big blind for proper BB/100 calculation
            SUM(p.money_won) as total_winnings,
            AVG(h.big_blind) as avg_big_blind
            
        FROM actions a
        LEFT JOIN players p ON a.hand_id = p.hand_id AND a.position = p.position
        LEFT JOIN hand_info h ON a.hand_id = h.hand_id
        -- Join för average bet sizes per street/action
        LEFT JOIN (
            SELECT street, action_label, AVG(size_frac) as avg_size
            FROM actions
            WHERE action = 'r' AND size_frac IS NOT NULL
            GROUP BY street, action_label
        ) avg_sizes ON a.street = avg_sizes.street AND a.action_label = avg_sizes.action_label
        -- Join för previous hand result
        LEFT JOIN (
            SELECT 
                a2.player_id,
                a2.hand_id,
                LAG(p2.money_won) OVER (PARTITION BY a2.player_id ORDER BY a2.hand_id) as prev_money_won
            FROM actions a2
            JOIN players p2 ON a2.hand_id = p2.hand_id AND a2.position = p2.position
            GROUP BY a2.player_id, a2.hand_id, p2.money_won
        ) prev_result ON a.player_id = prev_result.player_id AND a.hand_id = prev_result.hand_id
        WHERE a.player_id IS NOT NULL AND a.player_id != ''
        GROUP BY a.player_id, a.nickname
        HAVING hands_played > 10
        ORDER BY hands_played DESC
        LIMIT ?
        """
    else:
        # Fallback query without preflop_score/postflop_score columns
        query = """
        SELECT 
            a.player_id,
            a.nickname,
            COUNT(DISTINCT a.hand_id) as hands_played,
            AVG(a.j_score) as avg_j_score,
            
            -- Calculate VPIP: non-fold actions preflop / total preflop opportunities
            AVG(CASE WHEN a.action != 'f' AND a.street = 'preflop' THEN 1.0 ELSE 0.0 END) * 100 as vpip,
            
            -- Calculate PFR: raise actions preflop / total preflop opportunities  
            AVG(CASE WHEN a.action = 'r' AND a.street = 'preflop' THEN 1.0 ELSE 0.0 END) * 100 as pfr,
            
            -- Fallback: Use J-scores by street as approximation
            AVG(CASE WHEN a.street = 'preflop' THEN a.j_score ELSE NULL END) as avg_preflop_score,
            AVG(CASE WHEN a.street != 'preflop' THEN a.j_score ELSE NULL END) as avg_postflop_score,
            
            -- Street performance breakdown
            AVG(CASE WHEN a.street = 'preflop' THEN a.j_score ELSE NULL END) as preflop_j_score,
            AVG(CASE WHEN a.street = 'flop' THEN a.j_score ELSE NULL END) as flop_score,
            AVG(CASE WHEN a.street = 'turn' THEN a.j_score ELSE NULL END) as turn_score,
            AVG(CASE WHEN a.street = 'river' THEN a.j_score ELSE NULL END) as river_score,
            
            -- Position stats
            COUNT(CASE WHEN a.position IN ('EP', 'UTG', 'UTG+1') THEN 1 END) as early_pos_hands,
            COUNT(CASE WHEN a.position IN ('MP', 'MP+1', 'MP+2') THEN 1 END) as middle_pos_hands,
            COUNT(CASE WHEN a.position IN ('LP', 'CO', 'BTN') THEN 1 END) as late_pos_hands,
            COUNT(CASE WHEN a.position IN ('SB', 'BB') THEN 1 END) as blind_hands,
            
            -- Fallback score coverage 
            0 as preflop_scored_actions,
            0 as postflop_scored_actions,
            
            -- Get total winnings and average big blind for proper BB/100 calculation
            SUM(p.money_won) as total_winnings,
            AVG(h.big_blind) as avg_big_blind
            
        FROM actions a
        LEFT JOIN players p ON a.hand_id = p.hand_id AND a.position = p.position
        LEFT JOIN hand_info h ON a.hand_id = h.hand_id
        WHERE a.player_id IS NOT NULL AND a.player_id != ''
        GROUP BY a.player_id, a.nickname
        HAVING hands_played > 10
        ORDER BY hands_played DESC
        LIMIT ?
        """
    
    try:
        results = execute_query(query, (limit,), db_name='heavy_analysis.db')
        
        # Clean up and format results
        for player in results:
            # Calculate proper BB/100 if we have the data
            if player.get('total_winnings') is not None and player.get('avg_big_blind') and player['avg_big_blind'] > 0 and player['hands_played'] > 0:
                # BB/100 = (total_winnings in BB units) / total_hands * 100
                # First convert winnings to BB by dividing by avg_big_blind
                winnings_in_bb = player['total_winnings'] / player['avg_big_blind']
                player['winrate_bb100'] = round((winnings_in_bb / player['hands_played']) * 100, 2)
            else:
                player['winrate_bb100'] = 0
            
            player['total_hands'] = player['hands_played']
            
            # Round scores and percentages
            score_keys = [
                'avg_j_score', 'avg_preflop_score', 'avg_postflop_score',
                'preflop_j_score', 'flop_score', 'turn_score', 'river_score'
            ]
            
            for key in score_keys:
                if player.get(key) is not None:
                    player[key] = round(player[key], 1)
                    
            # Round percentages
            for key in ['vpip', 'pfr']:
                if player.get(key) is not None:
                    player[key] = round(player[key], 1)
        
        return results
    except Exception as e:
        log.error(f"Top players query failed: {e}")
        return []

def get_recent_activity() -> list:
    """Get recent activity stats"""
    query = """
    SELECT 
        DATE(h.hand_date) as play_date,
        COUNT(DISTINCT a.hand_id) as hands_count,
        COUNT(DISTINCT a.player_id) as unique_players,
        AVG(a.j_score) as avg_j_score
    FROM actions a
    JOIN hand_info h ON a.hand_id = h.hand_id
    WHERE a.player_id IS NOT NULL
    GROUP BY DATE(h.hand_date)
    ORDER BY play_date DESC
    LIMIT 7
    """
    
    try:
        return execute_query(query, db_name='heavy_analysis.db')
    except Exception as e:
        log.error(f"Recent activity query failed: {e}")
        return [] 
    

# new queries for table materialization

def dash_summary_new()      -> dict : return execute_query(
    "SELECT * FROM dashboard_summary LIMIT 1",             db_name='heavy_analysis.db')[0]

def top_players_new(limit: int = 25) -> list:
    """Return top players; kompatibel med både total_hands och hands_played kolumnnamn."""
    try:
        return execute_query(
            "SELECT * FROM top25_players ORDER BY total_hands DESC LIMIT ?",
            (limit,), db_name='heavy_analysis.db')
    except Exception:
        # Fallback om kolumnen heter hands_played
        return execute_query(
            "SELECT * FROM top25_players ORDER BY hands_played DESC LIMIT ?",
            (limit,), db_name='heavy_analysis.db')

def player_row_new(pid:str)  -> dict|None:
    rows = execute_query(
        "SELECT * FROM player_summary WHERE player_id = ?", (pid,),
        db_name='heavy_analysis.db')
    return rows[0] if rows else None

def player_rows_new(search:str="", limit:int=50)->list:
    sql  = "SELECT * FROM player_summary WHERE 1"
    args = []
    if search:
        sql += " AND (player_id LIKE ? OR nickname LIKE ?)"
        args += [f"%{search}%"]*2
    sql += " ORDER BY COALESCE(total_hands, hands_played) DESC LIMIT ?"
    args.append(limit)
    return execute_query(sql, tuple(args), db_name='heavy_analysis.db')