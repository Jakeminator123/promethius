from .db_connection import execute_query
import logging

log = logging.getLogger(__name__)

def get_all_players_for_comparison(search: str = "", limit: int = 100) -> list:
    """Get players for comparison dropdown from heavy_analysis.db"""
    query = """
    SELECT 
        a.player_id,
        a.nickname,
        COUNT(DISTINCT a.hand_id) as hands_played,
        AVG(a.j_score) as avg_j_score,
        AVG(CASE WHEN a.action != 'f' AND a.street = 'preflop' THEN 1.0 ELSE 0.0 END) * 100 as vpip,
        AVG(CASE WHEN a.action = 'r' AND a.street = 'preflop' THEN 1.0 ELSE 0.0 END) * 100 as pfr,
        
        -- Position-based performance
        AVG(CASE WHEN a.position IN ('EP', 'UTG', 'UTG+1') THEN a.j_score ELSE NULL END) as early_pos_score,
        AVG(CASE WHEN a.position IN ('LP', 'CO', 'BTN') THEN a.j_score ELSE NULL END) as late_pos_score,
        
        -- Street performance
        AVG(CASE WHEN a.street = 'preflop' THEN a.j_score ELSE NULL END) as preflop_score,
        AVG(CASE WHEN a.street = 'flop' THEN a.j_score ELSE NULL END) as flop_score,
        AVG(CASE WHEN a.street = 'turn' THEN a.j_score ELSE NULL END) as turn_score,
        AVG(CASE WHEN a.street = 'river' THEN a.j_score ELSE NULL END) as river_score,
        
        -- Action tendencies
        AVG(CASE WHEN a.action = 'r' THEN 1.0 ELSE 0.0 END) * 100 as aggression_freq,
        AVG(CASE WHEN a.action = 'c' THEN 1.0 ELSE 0.0 END) * 100 as call_freq,
        AVG(CASE WHEN a.action = 'f' THEN 1.0 ELSE 0.0 END) * 100 as fold_freq,
        
        -- Sizing data
        AVG(CASE WHEN a.action = 'r' THEN a.size_frac ELSE NULL END) as avg_raise_size,
        AVG(a.pot_after) as avg_pot_size
        
    FROM actions a
    WHERE a.player_id IS NOT NULL AND a.player_id != ''
    """
    
    params = []
    if search:
        query += " AND (a.player_id LIKE ? OR a.nickname LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    
    query += """
    GROUP BY a.player_id, a.nickname
    HAVING hands_played > 20
    ORDER BY hands_played DESC
    LIMIT ?
    """
    params.append(limit)
    
    try:
        results = execute_query(query, tuple(params), db_name='heavy_analysis.db')
        
        # Format results for frontend
        for player in results:
            # Round numeric values
            for key in ['avg_j_score', 'vpip', 'pfr', 'early_pos_score', 'late_pos_score',
                       'preflop_score', 'flop_score', 'turn_score', 'river_score',
                       'aggression_freq', 'call_freq', 'fold_freq', 'avg_raise_size']:
                val = player.get(key)
                if isinstance(val, (int, float)):
                    player[key] = round(float(val), 1)
                else:
                    player[key] = 0.0
            
            # Set hands and winrate for compatibility
            player['hands'] = player['hands_played']
            player['winrate'] = 0  # Would need poker.db for actual winrate
        
        return results
    except Exception as e:
        log.error(f"Players search query failed: {e}")
        return []

def get_detailed_player_comparison(player1_id: str, player2_id: str) -> dict:
    """Detailed head-to-head comparison from heavy_analysis.db"""
    query = """
    SELECT 
        a.player_id,
        a.nickname,
        COUNT(DISTINCT a.hand_id) as hands_played,
        
        -- Basic stats
        AVG(a.j_score) as avg_j_score,
        AVG(CASE WHEN a.action != 'f' AND a.street = 'preflop' THEN 1.0 ELSE 0.0 END) * 100 as vpip,
        AVG(CASE WHEN a.action = 'r' AND a.street = 'preflop' THEN 1.0 ELSE 0.0 END) * 100 as pfr,
        
        -- Positional breakdown
        AVG(CASE WHEN a.position IN ('EP', 'UTG', 'UTG+1') THEN a.j_score ELSE NULL END) as early_pos_score,
        COUNT(CASE WHEN a.position IN ('EP', 'UTG', 'UTG+1') THEN 1 END) as early_pos_hands,
        AVG(CASE WHEN a.position IN ('MP', 'MP+1', 'MP+2') THEN a.j_score ELSE NULL END) as middle_pos_score,
        COUNT(CASE WHEN a.position IN ('MP', 'MP+1', 'MP+2') THEN 1 END) as middle_pos_hands,
        AVG(CASE WHEN a.position IN ('LP', 'CO', 'BTN') THEN a.j_score ELSE NULL END) as late_pos_score,
        COUNT(CASE WHEN a.position IN ('LP', 'CO', 'BTN') THEN 1 END) as late_pos_hands,
        AVG(CASE WHEN a.position IN ('SB', 'BB') THEN a.j_score ELSE NULL END) as blind_score,
        COUNT(CASE WHEN a.position IN ('SB', 'BB') THEN 1 END) as blind_hands,
        
        -- Street performance
        AVG(CASE WHEN a.street = 'preflop' THEN a.j_score ELSE NULL END) as preflop_score,
        COUNT(CASE WHEN a.street = 'preflop' THEN 1 END) as preflop_actions,
        AVG(CASE WHEN a.street = 'flop' THEN a.j_score ELSE NULL END) as flop_score,
        COUNT(CASE WHEN a.street = 'flop' THEN 1 END) as flop_actions,
        AVG(CASE WHEN a.street = 'turn' THEN a.j_score ELSE NULL END) as turn_score,
        COUNT(CASE WHEN a.street = 'turn' THEN 1 END) as turn_actions,
        AVG(CASE WHEN a.street = 'river' THEN a.j_score ELSE NULL END) as river_score,
        COUNT(CASE WHEN a.street = 'river' THEN 1 END) as river_actions,
        
        -- Action frequency
        AVG(CASE WHEN a.action = 'r' THEN 1.0 ELSE 0.0 END) * 100 as raise_freq,
        AVG(CASE WHEN a.action = 'c' THEN 1.0 ELSE 0.0 END) * 100 as call_freq,
        AVG(CASE WHEN a.action = 'f' THEN 1.0 ELSE 0.0 END) * 100 as fold_freq,
        
        -- Sizing analysis
        AVG(CASE WHEN a.action = 'r' THEN a.size_frac ELSE NULL END) as avg_raise_size,
        AVG(CASE WHEN a.action = 'r' AND a.street = 'preflop' THEN a.size_frac ELSE NULL END) as preflop_raise_size,
        AVG(CASE WHEN a.action = 'r' AND a.street != 'preflop' THEN a.size_frac ELSE NULL END) as postflop_raise_size,
        
        -- Advanced metrics
        AVG(a.pot_after) as avg_pot_involved,
        MAX(a.pot_after) as max_pot_played,
        AVG(a.preflop_score) as preflop_skill_score,
        AVG(a.postflop_score) as postflop_skill_score
        
    FROM actions a
    WHERE a.player_id IN (?, ?) AND a.player_id IS NOT NULL
    GROUP BY a.player_id, a.nickname
    """
    
    try:
        results = execute_query(query, (player1_id, player2_id), db_name='heavy_analysis.db')
        
        comparison = {}
        for player in results:
            # Round all numeric values
            numeric_keys = [
                'avg_j_score', 'vpip', 'pfr', 'early_pos_score', 'middle_pos_score', 
                'late_pos_score', 'blind_score', 'preflop_score', 'flop_score', 
                'turn_score', 'river_score', 'raise_freq', 'call_freq', 'fold_freq',
                'avg_raise_size', 'preflop_raise_size', 'postflop_raise_size',
                'avg_pot_involved', 'preflop_skill_score', 'postflop_skill_score'
            ]
            
            for key in numeric_keys:
                val = player.get(key)
                if isinstance(val, (int, float)):
                    player[key] = round(float(val), 1)
                else:
                    player[key] = 0.0
            
            # Add compatibility fields
            player['hands'] = player['hands_played']
            player['winrate'] = 0  # Would need poker.db
            
            comparison[player['player_id']] = player
        
        return comparison
    except Exception as e:
        log.error(f"Player comparison query failed: {e}")
        return {}

def get_player_head_to_head(player1_id: str, player2_id: str) -> dict:
    """Get head-to-head stats when both players were in same hands"""
    query = """
    SELECT 
        a1.player_id as player1_id,
        a1.nickname as player1_name,
        a2.player_id as player2_id, 
        a2.nickname as player2_name,
        COUNT(DISTINCT a1.hand_id) as shared_hands,
        AVG(a1.j_score) as player1_avg_score,
        AVG(a2.j_score) as player2_avg_score,
        AVG(a1.pot_after) as avg_pot_size,
        
        -- Win rates in shared hands (would need poker.db for actual winnings)
        COUNT(CASE WHEN a1.j_score > a2.j_score THEN 1 END) as player1_better_decisions,
        COUNT(CASE WHEN a2.j_score > a1.j_score THEN 1 END) as player2_better_decisions
        
    FROM actions a1
    JOIN actions a2 ON a1.hand_id = a2.hand_id AND a1.player_id != a2.player_id
    WHERE a1.player_id = ? AND a2.player_id = ?
    GROUP BY a1.player_id, a2.player_id
    """
    
    try:
        result = execute_query(query, (player1_id, player2_id), db_name='heavy_analysis.db')
        return result[0] if result else {}
    except Exception as e:
        log.error(f"Head-to-head query failed: {e}")
        return {} 