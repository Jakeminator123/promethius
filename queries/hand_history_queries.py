from .db_connection import execute_query
import logging
import json

log = logging.getLogger(__name__)

def search_hands_advanced(
    player_filter: str = "",
    min_pot: int = 0,
    max_pot: int = 1000,
    street_filter: str = "",
    position_filter: str = "",
    game_type: str = "",  # "cash", "mtt", eller ""
    limit: int = 50
) -> list:
    """Advanced hand history search using heavy_analysis.db"""
    query = """
    SELECT DISTINCT
        a.hand_id,
        a.player_id,
        a.nickname,
        a.street,
        a.position,
        a.action,
        a.size_frac,
        a.pot_after,
        a.j_score,
        a.preflop_score,
        a.postflop_score,
        a.action_order,
        h.hand_date as timestamp,
        h.big_blind,
        h.pot_type,
        h.players_cnt,
        m.is_cash,
        m.is_mtt
    FROM actions a
    JOIN hand_info h ON a.hand_id = h.hand_id
    LEFT JOIN hand_meta m ON a.hand_id = m.id
    WHERE a.player_id IS NOT NULL AND a.player_id != ''
    """
    
    params = []
    
    if player_filter:
        query += " AND (a.player_id LIKE ? OR a.nickname LIKE ?)"
        params.extend([f"%{player_filter}%", f"%{player_filter}%"])
    
    if min_pot > 0:
        query += " AND a.pot_after >= ?"
        params.append(min_pot * 100)  # Assume 100 chips = 1 BB
    
    if max_pot < 1000:
        query += " AND a.pot_after <= ?"
        params.append(max_pot * 100)
    
    if street_filter:
        query += " AND a.street = ?"
        params.append(street_filter)
    
    if position_filter:
        query += " AND a.position = ?"
        params.append(position_filter)
    
    if game_type:
        if game_type.lower() == "cash":
            query += " AND m.is_cash = 1"
        elif game_type.lower() == "mtt":
            query += " AND m.is_mtt = 1"
    
    query += """
    ORDER BY h.hand_date DESC, a.action_order ASC
    LIMIT ?
    """
    params.append(limit)
    
    try:
        results = execute_query(query, tuple(params), db_name='heavy_analysis.db')
        
        # Format for frontend
        formatted_results = []
        for result in results:
            formatted_results.append({
                'hand_id': result['hand_id'],
                'timestamp': result['timestamp'],
                'player_id': result['player_id'],
                'nickname': result['nickname'],
                'street': result['street'],
                'position': result['position'],
                'action': result['action'],
                'pot_size_bb': round(result['pot_after'] / 100, 1) if result['pot_after'] else 0,
                'j_score': round(result['j_score'], 1) if result['j_score'] else 0,
                'size_frac': round(result['size_frac'], 2) if result['size_frac'] else 0,
                'pot_type': result['pot_type'],
                'players_count': result['players_cnt'],
                'is_cash': result.get('is_cash', 0),
                'is_mtt': result.get('is_mtt', 0),
                'game_type': 'Cash' if result.get('is_cash') else ('MTT' if result.get('is_mtt') else 'Unknown')
            })
        
        return formatted_results
    except Exception as e:
        log.error(f"Hand search query failed: {e}")
        return []

def get_hand_details(hand_id: str) -> list:
    """Get detailed hand breakdown from heavy_analysis.db"""
    query = """
    SELECT 
        a.*,
        h.hand_date,
        h.big_blind,
        h.pot_type,
        h.players_cnt
    FROM actions a
    JOIN hand_info h ON a.hand_id = h.hand_id
    WHERE a.hand_id = ?
    ORDER BY a.action_order ASC
    """
    
    try:
        return execute_query(query, (hand_id,), db_name='heavy_analysis.db')
    except Exception as e:
        log.error(f"Hand details query failed: {e}")
        return []

def get_raw_hand_history(hand_id: str) -> dict:
    """Get raw hand history from poker.db"""
    query = """
    SELECT 
        id,
        hand_date,
        seq,
        raw_json
    FROM hands
    WHERE id = ?
    """
    
    try:
        result = execute_query(query, (hand_id,), db_name='poker.db')
        if result:
            hand_data = result[0]
            # Parse the JSON data
            try:
                hand_data['parsed_json'] = json.loads(hand_data['raw_json'])
            except json.JSONDecodeError:
                hand_data['parsed_json'] = {}
            return hand_data
        return {}
    except Exception as e:
        log.error(f"Raw hand history query failed: {e}")
        return {}

def get_player_hand_summary(player_id: str, limit: int = 50) -> list:
    """Get summary of recent hands for a specific player"""
    query = """
    SELECT 
        a.hand_id,
        h.hand_date as timestamp,
        h.pot_type,
        h.players_cnt,
        COUNT(a.action_order) as actions_taken,
        AVG(a.j_score) as avg_j_score,
        MAX(a.pot_after) as final_pot,
        GROUP_CONCAT(DISTINCT a.street) as streets_played,
        GROUP_CONCAT(DISTINCT a.action) as actions_made,
        AVG(CASE WHEN a.action = 'r' THEN a.size_frac ELSE NULL END) as avg_raise_size
    FROM actions a
    JOIN hand_info h ON a.hand_id = h.hand_id
    WHERE a.player_id = ? AND a.player_id IS NOT NULL
    GROUP BY a.hand_id
    ORDER BY h.hand_date DESC
    LIMIT ?
    """
    
    try:
        results = execute_query(query, (player_id, limit), db_name='heavy_analysis.db')
        
        # Format results
        for result in results:
            result['pot_size_bb'] = round(result['final_pot'] / 100, 1) if result['final_pot'] else 0
            result['avg_j_score'] = round(result['avg_j_score'], 1) if result['avg_j_score'] else 0
            result['avg_raise_size'] = round(result['avg_raise_size'], 2) if result['avg_raise_size'] else 0
        
        return results
    except Exception as e:
        log.error(f"Player hand summary query failed: {e}")
        return []

def get_hand_statistics() -> dict:
    """Get overall hand statistics from heavy_analysis.db"""
    query = """
    SELECT 
        COUNT(DISTINCT a.hand_id) as total_hands,
        COUNT(DISTINCT a.player_id) as unique_players,
        COUNT(a.action_order) as total_actions,
        AVG(a.j_score) as avg_j_score,
        AVG(a.pot_after) as avg_pot_size,
        
        -- Street breakdown
        COUNT(CASE WHEN a.street = 'preflop' THEN 1 END) as preflop_actions,
        COUNT(CASE WHEN a.street = 'flop' THEN 1 END) as flop_actions,
        COUNT(CASE WHEN a.street = 'turn' THEN 1 END) as turn_actions,
        COUNT(CASE WHEN a.street = 'river' THEN 1 END) as river_actions,
        
        -- Action breakdown
        COUNT(CASE WHEN a.action = 'r' THEN 1 END) as raise_actions,
        COUNT(CASE WHEN a.action = 'c' THEN 1 END) as call_actions,
        COUNT(CASE WHEN a.action = 'f' THEN 1 END) as fold_actions,
        
        -- Pot type breakdown
        COUNT(CASE WHEN h.pot_type = 'SRP' THEN 1 END) as srp_hands,
        COUNT(CASE WHEN h.pot_type = '3BP' THEN 1 END) as three_bet_hands,
        COUNT(CASE WHEN h.pot_type = '4BP' THEN 1 END) as four_bet_hands
        
    FROM actions a
    JOIN hand_info h ON a.hand_id = h.hand_id
    WHERE a.player_id IS NOT NULL
    """
    
    try:
        result = execute_query(query, db_name='heavy_analysis.db')
        return result[0] if result else {}
    except Exception as e:
        log.error(f"Hand statistics query failed: {e}")
        return {} 