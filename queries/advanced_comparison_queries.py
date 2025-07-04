# queries/advanced_comparison_queries.py
from .db_connection import execute_query
import logging
from typing import Dict, List, Optional, Any

log = logging.getLogger(__name__)

def get_segmented_player_data(
    player_id: str,
    comparison_player_id: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get segmented player data with population averages
    
    Filters can include:
    - street: 'preflop', 'flop', 'turn', 'river'
    - position: 'BTN', 'CO', 'MP', 'EP', 'SB', 'BB', etc
    - action_label: 'bet', 'checkraise', 'donk', 'cont', etc
    - min_j_score / max_j_score
    - min_preflop_score / max_preflop_score  
    - min_postflop_score / max_postflop_score
    - players_left: number of players remaining
    - pot_type: 'SRP', '3BP', '4BP', etc
    - size_cat: 'small', 'medium', 'large', 'huge'
    - intention: specific player intentions
    - ip_status: 'IP' or 'OOP'
    """
    
    # Build WHERE clause based on filters
    where_conditions = ["a.player_id IS NOT NULL"]
    params = []
    
    if filters:
        if filters.get('street'):
            where_conditions.append("a.street = ?")
            params.append(filters['street'])
            
        if filters.get('position'):
            where_conditions.append("a.position = ?")
            params.append(filters['position'])
            
        if filters.get('action_label'):
            where_conditions.append("a.action_label = ?")
            params.append(filters['action_label'])
            
        if filters.get('min_j_score') is not None:
            where_conditions.append("a.j_score >= ?")
            params.append(filters['min_j_score'])
            
        if filters.get('max_j_score') is not None:
            where_conditions.append("a.j_score <= ?")
            params.append(filters['max_j_score'])
            
        if filters.get('min_preflop_score') is not None:
            where_conditions.append("a.preflop_score >= ?")
            params.append(filters['min_preflop_score'])
            
        if filters.get('max_preflop_score') is not None:
            where_conditions.append("a.preflop_score <= ?")
            params.append(filters['max_preflop_score'])
            
        if filters.get('min_postflop_score') is not None:
            where_conditions.append("a.postflop_score >= ?")
            params.append(filters['min_postflop_score'])
            
        if filters.get('max_postflop_score') is not None:
            where_conditions.append("a.postflop_score <= ?")
            params.append(filters['max_postflop_score'])
            
        if filters.get('players_left'):
            where_conditions.append("a.players_left = ?")
            params.append(str(filters['players_left']))  # Convert to string
            
        if filters.get('pot_type'):
            where_conditions.append("h.pot_type = ?")
            params.append(filters['pot_type'])
            
        if filters.get('size_cat'):
            where_conditions.append("a.size_cat = ?")
            params.append(filters['size_cat'])
            
        if filters.get('intention'):
            where_conditions.append("a.intention = ?")
            params.append(filters['intention'])
            
        if filters.get('ip_status'):
            where_conditions.append("a.ip_status = ?")
            params.append(filters['ip_status'])
    
    where_clause = " AND ".join(where_conditions)
    
    # Main query for player stats
    player_query = f"""
    SELECT 
        COUNT(*) as action_count,
        COUNT(DISTINCT a.hand_id) as hand_count,
        AVG(a.j_score) as avg_j_score,
        MIN(a.j_score) as min_j_score,
        MAX(a.j_score) as max_j_score,
        
        AVG(a.preflop_score) as avg_preflop_score,
        AVG(a.postflop_score) as avg_postflop_score,
        
        -- Action distribution
        SUM(CASE WHEN a.action = 'r' THEN 1 ELSE 0 END) as raise_count,
        SUM(CASE WHEN a.action = 'c' THEN 1 ELSE 0 END) as call_count,
        SUM(CASE WHEN a.action = 'f' THEN 1 ELSE 0 END) as fold_count,
        SUM(CASE WHEN a.action = 'x' THEN 1 ELSE 0 END) as check_count,
        
        -- Sizing stats
        AVG(CASE WHEN a.action = 'r' THEN a.size_frac ELSE NULL END) as avg_raise_size,
        MIN(CASE WHEN a.action = 'r' THEN a.size_frac ELSE NULL END) as min_raise_size,
        MAX(CASE WHEN a.action = 'r' THEN a.size_frac ELSE NULL END) as max_raise_size,
        
        -- Pot stats
        AVG(a.pot_before) as avg_pot_before,
        AVG(a.pot_after) as avg_pot_after,
        
        -- Success metrics
        AVG(CASE WHEN p.money_won > 0 THEN 1.0 ELSE 0.0 END) * 100 as win_rate,
        SUM(p.money_won) as total_winnings,
        
        -- Additional context
        GROUP_CONCAT(DISTINCT a.intention) as intentions_used,
        GROUP_CONCAT(DISTINCT a.size_cat) as size_categories_used
        
    FROM actions a
    LEFT JOIN hand_info h ON a.hand_id = h.hand_id
    LEFT JOIN players p ON a.hand_id = p.hand_id AND a.position = p.position
    WHERE {where_clause} AND (a.player_id = ? OR a.nickname = ?)
    """
    
    # Population average query (same filters but all players)
    population_query = f"""
    SELECT 
        COUNT(*) as total_actions,
        COUNT(DISTINCT a.player_id) as unique_players,
        AVG(a.j_score) as avg_j_score,
        AVG(a.preflop_score) as avg_preflop_score,
        AVG(a.postflop_score) as avg_postflop_score,
        
        AVG(CASE WHEN a.action = 'r' THEN a.size_frac ELSE NULL END) as avg_raise_size,
        AVG(CASE WHEN p.money_won > 0 THEN 1.0 ELSE 0.0 END) * 100 as avg_win_rate
        
    FROM actions a
    LEFT JOIN hand_info h ON a.hand_id = h.hand_id
    LEFT JOIN players p ON a.hand_id = p.hand_id AND a.position = p.position
    WHERE {where_clause}
    """
    
    try:
        # Get player stats
        player_params = params + [player_id, player_id]
        player_result = execute_query(player_query, tuple(player_params), db_name='heavy_analysis.db')
        player_stats = player_result[0] if player_result else {}
        
        # Get population stats
        pop_result = execute_query(population_query, tuple(params), db_name='heavy_analysis.db')
        population_stats = pop_result[0] if pop_result else {}
        
        # Get comparison player stats if specified
        comparison_stats = {}
        if comparison_player_id:
            comp_params = params + [comparison_player_id, comparison_player_id]
            comp_result = execute_query(player_query, tuple(comp_params), db_name='heavy_analysis.db')
            comparison_stats = comp_result[0] if comp_result else {}
        
        return {
            'player_stats': player_stats,
            'population_stats': population_stats,
            'comparison_stats': comparison_stats,
            'filters_applied': filters or {},
            'player_id': player_id,
            'comparison_player_id': comparison_player_id
        }
        
    except Exception as e:
        log.error(f"Segmented player data query failed: {e}")
        return {}

def get_segment_hands(
    player_id: str,
    filters: Dict[str, Any],
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get specific hands matching the segment filters"""
    
    # Build WHERE clause
    where_conditions = ["a.player_id IS NOT NULL", "(a.player_id = ? OR a.nickname = ?)"]
    params = [player_id, player_id]
    
    if filters:
        if filters.get('street'):
            where_conditions.append("a.street = ?")
            params.append(filters['street'])
            
        if filters.get('position'):
            where_conditions.append("a.position = ?")
            params.append(filters['position'])
            
        if filters.get('action_label'):
            where_conditions.append("a.action_label = ?")
            params.append(filters['action_label'])
            
        if filters.get('min_j_score') is not None:
            where_conditions.append("a.j_score >= ?")
            params.append(filters['min_j_score'])
            
        if filters.get('max_j_score') is not None:
            where_conditions.append("a.j_score <= ?")
            params.append(filters['max_j_score'])
            
        if filters.get('min_preflop_score') is not None:
            where_conditions.append("a.preflop_score >= ?")
            params.append(filters['min_preflop_score'])
            
        if filters.get('max_preflop_score') is not None:
            where_conditions.append("a.preflop_score <= ?")
            params.append(filters['max_preflop_score'])
            
        if filters.get('min_postflop_score') is not None:
            where_conditions.append("a.postflop_score >= ?")
            params.append(filters['min_postflop_score'])
            
        if filters.get('max_postflop_score') is not None:
            where_conditions.append("a.postflop_score <= ?")
            params.append(filters['max_postflop_score'])
            
        if filters.get('players_left'):
            where_conditions.append("a.players_left = ?")
            params.append(str(filters['players_left']))  # Convert to string
            
        if filters.get('pot_type'):
            where_conditions.append("h.pot_type = ?")
            params.append(filters['pot_type'])
            
        if filters.get('size_cat'):
            where_conditions.append("a.size_cat = ?")
            params.append(filters['size_cat'])
            
        if filters.get('intention'):
            where_conditions.append("a.intention = ?")
            params.append(filters['intention'])
            
        if filters.get('ip_status'):
            where_conditions.append("a.ip_status = ?")
            params.append(filters['ip_status'])
    
    where_clause = " AND ".join(where_conditions)
    
    query = f"""
    SELECT 
        a.hand_id,
        a.action_order,
        a.street,
        a.position,
        a.action,
        a.action_label,
        a.j_score,
        a.preflop_score,
        a.postflop_score,
        a.size_frac,
        a.pot_before,
        a.pot_after,
        a.players_left,
        a.intention,
        a.ip_status,
        a.holecards,
        a.board_cards,
        h.hand_date,
        h.pot_type,
        h.players_cnt,
        p.money_won
    FROM actions a
    JOIN hand_info h ON a.hand_id = h.hand_id
    LEFT JOIN players p ON a.hand_id = p.hand_id AND a.position = p.position
    WHERE {where_clause}
    ORDER BY h.hand_date DESC, a.action_order
    LIMIT ?
    """
    
    params.append(str(limit))
    
    try:
        results = execute_query(query, tuple(params), db_name='heavy_analysis.db')
        return results
    except Exception as e:
        log.error(f"Segment hands query failed: {e}")
        return []

def get_segment_distribution(
    filters: Dict[str, Any],
    group_by: str = 'player_id'
) -> List[Dict[str, Any]]:
    """Get distribution of players/actions for a given segment"""
    
    # Build WHERE clause
    where_conditions = ["a.player_id IS NOT NULL"]
    params = []
    
    if filters:
        if filters.get('street'):
            where_conditions.append("a.street = ?")
            params.append(filters['street'])
            
        if filters.get('position'):
            where_conditions.append("a.position = ?")
            params.append(filters['position'])
            
        if filters.get('action_label'):
            where_conditions.append("a.action_label = ?")
            params.append(filters['action_label'])
            
        # Add other filter conditions...
    
    where_clause = " AND ".join(where_conditions)
    
    # Different groupings available
    if group_by == 'player_id':
        group_col = "a.player_id, a.nickname"
        select_col = "a.player_id, a.nickname"
    elif group_by == 'position':
        group_col = "a.position"
        select_col = "a.position"
    elif group_by == 'action_label':
        group_col = "a.action_label"
        select_col = "a.action_label"
    elif group_by == 'intention':
        group_col = "a.intention"
        select_col = "a.intention"
    else:
        group_col = "a.player_id, a.nickname"
        select_col = "a.player_id, a.nickname"
    
    query = f"""
    SELECT 
        {select_col},
        COUNT(*) as action_count,
        COUNT(DISTINCT a.hand_id) as hand_count,
        AVG(a.j_score) as avg_j_score,
        MIN(a.j_score) as min_j_score,
        MAX(a.j_score) as max_j_score,
        AVG(CASE WHEN p.money_won > 0 THEN 1.0 ELSE 0.0 END) * 100 as win_rate
    FROM actions a
    LEFT JOIN hand_info h ON a.hand_id = h.hand_id
    LEFT JOIN players p ON a.hand_id = p.hand_id AND a.position = p.position
    WHERE {where_clause}
    GROUP BY {group_col}
    ORDER BY action_count DESC
    LIMIT 50
    """
    
    try:
        results = execute_query(query, tuple(params), db_name='heavy_analysis.db')
        return results
    except Exception as e:
        log.error(f"Segment distribution query failed: {e}")
        return []

def get_available_filters() -> Dict[str, List[str]]:
    """Get all available filter options from the database"""

    queries = {
        'streets': "SELECT DISTINCT street FROM actions WHERE street IS NOT NULL ORDER BY street",
        'positions': "SELECT DISTINCT position FROM actions WHERE position IS NOT NULL ORDER BY position",
        'action_labels': "SELECT DISTINCT action_label FROM actions WHERE action_label IS NOT NULL AND action_label != '' ORDER BY action_label",
        'pot_types': "SELECT DISTINCT pot_type FROM hand_info WHERE pot_type IS NOT NULL ORDER BY pot_type",
        'size_categories': "SELECT DISTINCT size_cat FROM actions WHERE size_cat IS NOT NULL ORDER BY size_cat",
        'intentions': "SELECT DISTINCT intention FROM actions WHERE intention IS NOT NULL AND intention != '' AND intention != 'unknown' ORDER BY intention",
        'ip_status': "SELECT DISTINCT ip_status FROM actions WHERE ip_status IS NOT NULL ORDER BY ip_status"
    }

    # SQLite doesn't have FIELD() so we'll handle ordering in Python
    street_order = ['preflop', 'flop', 'turn', 'river']

    available_filters = {}

    for key, query in queries.items():
        try:
            results = execute_query(query, db_name='heavy_analysis.db')

            if key == 'streets':
                # Sort by our preferred order
                values = [r['street'] for r in results]
                values_sorted = [s for s in street_order if s in values]
                # Add any streets not in our order at the end
                for v in values:
                    if v not in values_sorted:
                        values_sorted.append(str(v))
                available_filters[key] = values_sorted
            else:
                available_filters[key] = [str(r[list(r.keys())[0]]) for r in results if r[list(r.keys())[0]]]
        except Exception as e:
            log.error(f"Failed to get {key}: {e}")
            available_filters[key] = []

    return available_filters