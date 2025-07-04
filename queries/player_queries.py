# queries/player_queries.py
from .db_connection import execute_query
import logging
from typing import Any, Union, cast
from .hand_strength import get_hand_strength

# Sampling cap to avoid huge aggregations
MAX_ACTIONS_SAMPLE = 50000  # antal actions att inkludera per spelare

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Hjälpfunktioner för typ-säker numerisk hantering
# ─────────────────────────────────────────────────────────────

Number = Union[int, float]


def _to_int(value: Any) -> int:
    """Försök konvertera till int annars 0."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float:
    """Försök konvertera till float annars 0.0."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def get_top_players_by_hands(limit: int = 25) -> list:
    """
    Hämtar de spelare med flest händer från actions-tabellen
    
    Args:
        limit: Antal spelare att returnera
        
    Returns:
        list: Lista med spelare och deras statistik
    """
    query = """
    SELECT 
        a.player_id,
        a.nickname,
        COUNT(DISTINCT a.hand_id) as total_hands,
        COUNT(a.action_order) as total_actions,
        SUM(CASE WHEN a.action = 'r' AND a.street = 'preflop' AND a.action_order = 0 THEN 1 ELSE 0 END) as total_opens,
        SUM(CASE WHEN a.action != 'f' AND a.street = 'preflop' THEN 1 ELSE 0 END) as vpip_count,
        SUM(CASE WHEN a.action = 'r' AND a.street = 'preflop' THEN 1 ELSE 0 END) as pfr_count,
        AVG(a.j_score) as avg_j_score,
        SUM(p.money_won) as total_winnings,
        AVG(h.big_blind) as avg_big_blind
    FROM actions a
    LEFT JOIN players p ON a.hand_id = p.hand_id AND a.position = p.position
    LEFT JOIN hand_info h ON a.hand_id = h.hand_id
    WHERE a.player_id IS NOT NULL
    GROUP BY a.player_id, a.nickname
    HAVING COUNT(DISTINCT a.hand_id) > 10
    ORDER BY total_hands DESC
    LIMIT ?
    """
    
    results = execute_query(query, (limit,))
    
    # Beräkna VPIP och PFR procent
    for player in results:
        vpip_cnt = _to_int(player.get('vpip_count'))
        fold_cnt = _to_int(player.get('fold_count'))
        preflop_hands = vpip_cnt + fold_cnt
        if preflop_hands > 0:
            player['vpip'] = round((_to_float(player.get('vpip_count')) / preflop_hands) * 100, 1)
            player['pfr'] = round((_to_float(player.get('pfr_count')) / preflop_hands) * 100, 1)
        else:
            player['vpip'] = 0
            player['pfr'] = 0
        
        # Beräkna BB/100 korrekt
        total_win = _to_float(player.get('total_winnings'))
        avg_bb = _to_float(player.get('avg_big_blind'))
        if avg_bb > 0:
            # BB/100 = (total_winnings in BB units) / total_hands * 100
            # First convert winnings to BB by dividing by avg_big_blind
            winnings_in_bb = total_win / avg_bb
            player['winrate_bb100'] = round((winnings_in_bb / max(_to_int(player.get('total_hands')), 1)) * 100, 2)
        else:
            player['winrate_bb100'] = 0
        
        # Avrunda J-score
        player['avg_j_score'] = round(_to_float(player.get('avg_j_score')), 1)
    
    return results

def get_player_stats(player_id: str) -> dict:
    """
    Hämtar detaljerad statistik för en specifik spelare
    
    Args:
        player_id: Spelarens ID
        
    Returns:
        dict: Spelarens statistik
    """
    # Grundläggande stats
    basic_query = """
    SELECT 
        a.player_id,
        a.nickname,
        COUNT(DISTINCT a.hand_id) as total_hands,
        COUNT(a.action_order) as total_actions,
        AVG(a.j_score) as avg_j_score,
        -- VPIP / PFR underlag
        SUM(CASE WHEN a.action != 'f' AND a.street = 'preflop' THEN 1 ELSE 0 END) as vpip_count,
        SUM(CASE WHEN a.action = 'r' AND a.street = 'preflop' THEN 1 ELSE 0 END) as pfr_count,
        SUM(CASE WHEN a.street = 'preflop' THEN 1 ELSE 0 END) as preflop_actions,
        AVG(a.preflop_score) as avg_preflop_score,
        AVG(a.postflop_score) as avg_postflop_score
    FROM actions a
    WHERE a.player_id = ?
    GROUP BY a.player_id, a.nickname
    """
    
    # Street-specifik statistik
    street_query = """
    SELECT 
        street,
        COUNT(*) as actions_count,
        AVG(j_score) as avg_j_score,
        SUM(CASE WHEN action = 'r' THEN 1 ELSE 0 END) as raise_count,
        SUM(CASE WHEN action = 'c' THEN 1 ELSE 0 END) as call_count,
        SUM(CASE WHEN action = 'f' THEN 1 ELSE 0 END) as fold_count
    FROM actions
    WHERE player_id = ?
    GROUP BY street
    """
    
    # Position stats
    position_query = """
    SELECT 
        position,
        COUNT(DISTINCT hand_id) as hands,
        AVG(j_score) as avg_j_score
    FROM actions
    WHERE player_id = ? AND action_order = 0
    GROUP BY position
    """
    
    basic_stats = execute_query(basic_query, (player_id,))
    street_stats = execute_query(street_query, (player_id,))
    position_stats = execute_query(position_query, (player_id,))
    
    if basic_stats:
        result = basic_stats[0]
        # Beräkna VPIP och PFR-procent
        preflop_actions = _to_int(result.get('preflop_actions'))
        if preflop_actions > 0:
            result['vpip'] = round((_to_float(result.get('vpip_count')) / preflop_actions) * 100, 1)
            result['pfr']  = round((_to_float(result.get('pfr_count'))  / preflop_actions) * 100, 1)
        else:
            result['vpip'] = 0
            result['pfr']  = 0
        
        result['street_stats'] = street_stats
        result['position_stats'] = position_stats
        return result
    
    return {}

def get_player_comparison(player1_id: str, player2_id: str) -> dict:
    """
    Jämför två spelare
    
    Args:
        player1_id: Första spelarens ID
        player2_id: Andra spelarens ID
        
    Returns:
        dict: Jämförelsedata
    """
    query = """
    SELECT 
        player_id,
        nickname,
        COUNT(DISTINCT hand_id) as total_hands,
        AVG(j_score) as avg_j_score,
        SUM(CASE WHEN action != 'f' AND street = 'preflop' THEN 1 ELSE 0 END) as vpip_count,
        SUM(CASE WHEN action = 'r' AND street = 'preflop' THEN 1 ELSE 0 END) as pfr_count,
        SUM(CASE WHEN street = 'preflop' THEN 1 ELSE 0 END) as preflop_actions,
        AVG(CASE WHEN action = 'r' THEN size_frac ELSE NULL END) as avg_raise_size
    FROM actions
    WHERE player_id IN (?, ?)
    GROUP BY player_id
    """
    
    results = execute_query(query, (player1_id, player2_id))
    
    comparison = {}
    for player in results:
        # Beräkna VPIP och PFR
        preflop_act = _to_int(player.get('preflop_actions'))
        if preflop_act > 0:
            player['vpip'] = round((_to_float(player.get('vpip_count')) / preflop_act) * 100, 1)
            player['pfr'] = round((_to_float(player.get('pfr_count')) / preflop_act) * 100, 1)
        else:
            player['vpip'] = 0
            player['pfr'] = 0
            
        player['avg_j_score'] = round(_to_float(player.get('avg_j_score')), 1)
        player['avg_raise_size'] = round(_to_float(player.get('avg_raise_size')), 1)
        
        comparison[player['player_id']] = player
    
    return comparison

def search_player_hands(player_filter: str = "", min_pot: int = 0, limit: int = 50) -> list:
    """
    Söker efter händer baserat på filter
    
    Args:
        player_filter: Spelarnamn att filtrera på
        min_pot: Minsta pottstorlek
        limit: Max antal resultat
        
    Returns:
        list: Lista med händer
    """
    query = """
    SELECT DISTINCT
        h.hand_id,
        h.hand_date,
        h.big_blind,
        h.pot_type,
        h.players_cnt,
        MAX(a.pot_after) as final_pot,
        GROUP_CONCAT(DISTINCT p.nickname) as players,
        CASE 
            WHEN SUM(p.money_won) > 0 THEN p.nickname 
            ELSE 'Split' 
        END as winner
    FROM hand_info h
    JOIN actions a ON h.hand_id = a.hand_id
    JOIN players p ON h.hand_id = p.hand_id
    WHERE 1=1
    """
    
    params = []
    
    if player_filter:
        query += " AND p.nickname LIKE ?"
        params.append(f"%{player_filter}%")
    
    if min_pot > 0:
        query += " AND a.pot_after >= ?"
        params.append(min_pot * 100)  # Konvertera till chips (BB * 100)
    
    query += """
    GROUP BY h.hand_id
    ORDER BY h.hand_date DESC, h.seq DESC
    LIMIT ?
    """
    params.append(limit)
    
    results = execute_query(query, tuple(params))
    
    # Formatera resultaten
    for hand in results:
        hand['pot_size_bb'] = round(_to_float(hand.get('final_pot')) / max(_to_float(hand.get('big_blind')), 1), 1)
        hand['timestamp'] = hand['hand_date']
        
    return results

def get_betting_vs_strength_data(
    player_id = None,
    streets = None,
    action_labels = None,
    limit: int = 1000
) -> list:
    """
    Get betting actions vs hand strength data for scatter plot
    
    Args:
        player_id: Filter by specific player (optional)
        streets: List of streets to include ['flop', 'turn', 'river'] (optional)
        action_labels: List of action labels to include ['bet', '2bet', '3bet', 'checkraise', etc.] (optional)
        limit: Maximum number of data points
    
    Returns:
        List of dicts with hand_strength, bet_size_pct, street, action_label, player info
    """
    
    # Base query for betting actions with strength and sizing data
    query = """
    SELECT 
        a.hand_id,
        a.player_id,
        a.nickname,
        a.street,
        a.action_label,
        a.j_score,
        a.holecards,
        a.board_cards,
        a.size_frac,
        CASE 
            WHEN a.street = 'preflop' THEN 
                CASE WHEN a.size_frac IS NOT NULL THEN a.size_frac * 100 / 3.0 ELSE NULL END
            ELSE 
                CASE WHEN a.size_frac IS NOT NULL THEN a.size_frac * 100 ELSE NULL END
        END as bet_size_pct,
        a.pot_before,
        a.invested_this_action,
        a.action_order
    FROM actions a
    WHERE a.action IN ('r', 'b')  -- Only raise and bet actions
      AND a.size_frac IS NOT NULL
      AND a.size_frac > 0
      AND (a.holecards IS NOT NULL OR a.j_score IS NOT NULL)  -- Ha antingen cards eller j_score
    """
    
    params = []
    
    # Filter by player
    if player_id:
        query += " AND (a.player_id = ? OR a.nickname = ?)"
        params.extend([player_id, player_id])
    
    # Filter by streets (exclude preflop by default for bet sizing analysis)
    if streets:
        street_placeholders = ','.join(['?' for _ in streets])
        query += f" AND a.street IN ({street_placeholders})"
        params.extend(streets)
    else:
        # Default: include all streets (preflop opens are also interesting for sizing)
        # If you want only postflop, specify streets=['flop', 'turn', 'river']
        pass  # No street filter - include all
    
    # Filter by action labels
    if action_labels:
        action_placeholders = ','.join(['?' for _ in action_labels])
        query += f" AND a.action_label IN ({action_placeholders})"
        params.extend(action_labels)
    else:
        # Default: common betting actions (include all raise/bet actions)
        query += " AND a.action_label IN ('open', 'raise', 'bet', '2bet', '3bet', '4bet', '5bet', 'checkraise', 'donk', 'probe', 'lead', 'cont', 'squeeze', 'limp_raise')"
    
    query += """
    ORDER BY a.hand_id DESC, a.action_order ASC
    LIMIT ?
    """
    params.append(limit)
    
    try:
        results = execute_query(query, tuple(params), db_name='heavy_analysis.db')
        
        # Clean and format results
        formatted_results = []
        for row in results:
            # Ensure bet_size_pct is reasonable (0-150%)
            raw_bet_size = _to_float(row.get('bet_size_pct'))
            if raw_bet_size > 0.0:
                bet_size_pct = min(cast(float, raw_bet_size), 150.0)
            else:
                bet_size_pct = 0.0
            
            # Skip invalid bet sizes
            if bet_size_pct <= 0:
                continue
            
            # Calculate actual hand strength using hole cards and board
            holecards = row.get('holecards', '')
            board_cards = row.get('board_cards', '')
            street = row.get('street', 'preflop')
            
            # Try to get hand strength from cards if available
            hand_strength = 0
            if holecards:
                # Remove commas from holecards and board_cards (database stores them as 'As,Jd')
                holecards_clean = holecards.replace(',', '') if holecards else ''
                board_cards_clean = board_cards.replace(',', '') if board_cards else ''
                
                hand_strength = get_hand_strength(holecards_clean, board_cards_clean, street)
            
            # If no hand strength from cards, use J-score as proxy (scale 0-100)
            if hand_strength <= 0:
                j_score = _to_float(row.get('j_score'))
                if j_score is not None:
                    # Scale J-score to 0-100 range (assuming J-score is roughly -10 to +10)
                    hand_strength = max(0, min(100, (j_score + 10) * 5))
            
            # Skip if still no valid hand strength
            if hand_strength <= 0:
                continue
                
            formatted_results.append({
                'hand_id': row['hand_id'],
                'player_id': row['player_id'],
                'nickname': row['nickname'],
                'street': row['street'],
                'action_label': row['action_label'] or 'bet',  # Default to 'bet' if null
                'hand_strength': round(hand_strength, 1),
                'j_score': row.get('j_score'),  # Keep J-score for decision quality
                'holecards': holecards,
                'bet_size_pct': round(bet_size_pct, 1),
                'raw_size_frac': row['size_frac'],
                'pot_before': row['pot_before'],
                'invested': row['invested_this_action']
            })
        
        log.info(f"Retrieved {len(formatted_results)} betting vs strength data points")
        return formatted_results
        
    except Exception as e:
        log.error(f"Betting vs strength query failed: {e}")
        return []

def get_player_top_opponents(player_id: str, limit: int = 3) -> list:
    """
    Get player's most frequent opponents and head-to-head results
    """
    query = """
    WITH player_hands AS (
        SELECT DISTINCT a1.hand_id
        FROM actions a1
        WHERE (a1.player_id = ? OR a1.nickname = ?)
    ),
    opponent_hands AS (
        SELECT 
            a2.player_id,
            a2.nickname,
            COUNT(DISTINCT a2.hand_id) as hands_together,
            AVG(a2.j_score) as opponent_avg_score,
            AVG(a1.j_score) as player_avg_score
        FROM player_hands ph
        JOIN actions a1 ON ph.hand_id = a1.hand_id 
            AND (a1.player_id = ? OR a1.nickname = ?)
        JOIN actions a2 ON ph.hand_id = a2.hand_id 
            AND a2.player_id != a1.player_id
            AND a2.nickname != a1.nickname
        WHERE a1.j_score IS NOT NULL AND a2.j_score IS NOT NULL
        GROUP BY a2.player_id, a2.nickname
        HAVING hands_together > 5
        ORDER BY hands_together DESC
        LIMIT ?
    )
    SELECT * FROM opponent_hands
    """
    
    try:
        results = execute_query(query, (player_id, player_id, player_id, player_id, limit), db_name='heavy_analysis.db')
        
        # Format results
        for opponent in results:
            opponent['hands_together'] = opponent['hands_together']
            opponent['opponent_avg_score'] = round(opponent.get('opponent_avg_score', 0), 1)
            opponent['player_avg_score'] = round(opponent.get('player_avg_score', 0), 1)
            opponent['score_diff'] = round(opponent['player_avg_score'] - opponent['opponent_avg_score'], 1)
        
        return results
        
    except Exception as e:
        log.error(f"Top opponents query failed: {e}")
        return []

def get_player_intentions_radar(player_id: str, limit: int = 10) -> list:
    """
    Get player's most frequent intentions for radar chart
    """
    query = """
    SELECT 
        a.intention,
        COUNT(*) as n_actions,
        AVG(a.j_score) as avg_j_score,
        AVG(CASE WHEN a.street = 'preflop' THEN a.j_score ELSE NULL END) as preflop_score,
        AVG(CASE WHEN a.street != 'preflop' THEN a.j_score ELSE NULL END) as postflop_score
    FROM actions a
    WHERE (a.player_id = ? OR a.nickname = ?)
      AND a.intention IS NOT NULL 
      AND a.intention != ''
      AND a.intention != 'unknown'
    GROUP BY a.intention
    HAVING n_actions >= 3
    ORDER BY n_actions DESC
    LIMIT ?
    """
    
    try:
        results = execute_query(query, (player_id, player_id, limit), db_name='heavy_analysis.db')
        
        if not results:
            return []
        
        # Normalize to percentage values for radar chart (0-100)
        max_actions = max(_to_int(result['n_actions']) for result in results)
        
        formatted_results = []
        for result in results:
            # Normalize action frequency to 0-100 scale
            frequency_pct = round((_to_float(result['n_actions']) / max_actions) * 100, 1)
            
            formatted_results.append({
                'intention': result['intention'],
                'n_actions': result['n_actions'],
                'frequency_pct': frequency_pct,
                'avg_j_score': round(cast(float, _to_float(result.get('avg_j_score'))), 1),
                'preflop_score': (round(cast(float, _to_float(result.get('preflop_score'))), 1)
                                 if result.get('preflop_score') is not None else None),
                'postflop_score': (round(cast(float, _to_float(result.get('postflop_score'))), 1)
                                  if result.get('postflop_score') is not None else None),
            })
        
        log.info(f"Retrieved {len(formatted_results)} intentions for player {player_id}")
        return formatted_results
        
    except Exception as e:
        log.error(f"Player intentions query failed: {e}")
        return []

def get_player_recent_hands(player_id: str, limit: int = 20) -> list:
    """
    Get player's most recent hands with basic info
    """
    query = """
    SELECT DISTINCT
        a.hand_id,
        h.hand_date,
        h.big_blind,
        h.small_blind,
        h.ante,
        h.pot_type,
        h.players_cnt,
        MAX(a.pot_after) as final_pot,
        p.position,
        p.holecards,
        p.money_won,
        COUNT(CASE WHEN a.player_id = ? OR a.nickname = ? THEN 1 END) as player_actions,
        AVG(CASE WHEN a.player_id = ? OR a.nickname = ? THEN a.j_score END) as avg_j_score
    FROM actions a
    JOIN hand_info h ON a.hand_id = h.hand_id
    LEFT JOIN players p ON a.hand_id = p.hand_id 
        AND (p.nickname = ? OR p.nickname LIKE ?)
    WHERE a.hand_id IN (
        SELECT DISTINCT hand_id FROM actions 
        WHERE (player_id = ? OR nickname = ?)
    )
    GROUP BY a.hand_id
    ORDER BY h.hand_date DESC, a.hand_id DESC
    LIMIT ?
    """
    
    try:
        # Use player_id for all parameters
        like_param = f"%{player_id}%"
        results = execute_query(query, (
            player_id, player_id, player_id, player_id, 
            player_id, like_param, player_id, player_id, limit
        ), db_name='heavy_analysis.db')
        
        formatted_results = []
        for hand in results:
            final_pot_bb = round(_to_float(hand.get('final_pot')) / max(_to_float(hand.get('big_blind')), 1.0), 1) if hand.get('final_pot') and hand.get('big_blind') else 0
            
            formatted_results.append({
                'hand_id': hand['hand_id'],
                'hand_date': hand['hand_date'],
                'position': hand['position'],
                'holecards': hand['holecards'],
                'pot_type': hand['pot_type'],
                'final_pot_bb': final_pot_bb,
                'money_won': round(_to_float(hand.get('money_won')), 2) if hand.get('money_won') else 0,
                'player_actions': hand['player_actions'],
                'avg_j_score': round(cast(float, _to_float(hand.get('avg_j_score'))), 1) if hand.get('avg_j_score') else 0,
                'players_count': hand['players_cnt'],
                'blinds': f"{hand['small_blind']}/{hand['big_blind']}" + (f"/{hand['ante']}" if hand['ante'] else "")
            })
        
        return formatted_results
        
    except Exception as e:
        log.error(f"Recent hands query failed: {e}")
        return []

def get_player_detailed_stats(player_id: str) -> dict:
    """
    Get comprehensive player statistics - the "low hanging fruit" stats
    """
    # Begränsa aggregeringen till de senaste MAX_ACTIONS_SAMPLE actions för spelaren
    query = f"""
    SELECT 
        COUNT(DISTINCT a.hand_id) as total_hands,
        COUNT(a.action_order) as total_actions,
        
        -- Basic preflop stats
        AVG(CASE WHEN a.action != 'f' AND a.street = 'preflop' THEN 1.0 ELSE 0.0 END) * 100 as vpip,
        AVG(CASE WHEN a.action = 'r' AND a.street = 'preflop' THEN 1.0 ELSE 0.0 END) * 100 as pfr,
        
        -- Aggression stats
        COUNT(CASE WHEN a.action = 'r' THEN 1 END) as total_raises,
        COUNT(CASE WHEN a.action = 'c' THEN 1 END) as total_calls,
        COUNT(CASE WHEN a.action = 'f' THEN 1 END) as total_folds,
        
        -- Position stats
        COUNT(CASE WHEN a.position IN ('EP', 'UTG', 'UTG+1') THEN 1 END) as early_pos_hands,
        COUNT(CASE WHEN a.position IN ('LP', 'CO', 'BTN') THEN 1 END) as late_pos_hands,
        
        -- Street performance
        AVG(CASE WHEN a.street = 'preflop' THEN a.j_score ELSE NULL END) as preflop_avg,
        AVG(CASE WHEN a.street = 'flop' THEN a.j_score ELSE NULL END) as flop_avg,
        AVG(CASE WHEN a.street = 'turn' THEN a.j_score ELSE NULL END) as turn_avg,
        AVG(CASE WHEN a.street = 'river' THEN a.j_score ELSE NULL END) as river_avg,
        
        -- Pot sizes
        AVG(a.pot_after) as avg_pot_size,
        MAX(a.pot_after) as max_pot_played,
        
        -- Sizing stats  
        AVG(CASE WHEN a.action = 'r' THEN a.size_frac ELSE NULL END) as avg_bet_size,
        
        -- Overall performance
        AVG(a.j_score) as overall_j_score,
        
        -- Action tendencies by street
        COUNT(CASE WHEN a.street = 'preflop' THEN 1 END) as preflop_actions,
        COUNT(CASE WHEN a.street = 'flop' THEN 1 END) as flop_actions,
        COUNT(CASE WHEN a.street = 'turn' THEN 1 END) as turn_actions,
        COUNT(CASE WHEN a.street = 'river' THEN 1 END) as river_actions
        
    FROM actions a
    WHERE (a.player_id = ? OR a.nickname = ?)
      AND a.player_id IS NOT NULL
      AND a.rowid IN (
          SELECT rowid FROM actions
          WHERE (player_id = ? OR nickname = ?)
          ORDER BY rowid DESC
          LIMIT {MAX_ACTIONS_SAMPLE}
      )
    """
    
    try:
        params = (player_id, player_id, player_id, player_id)
        result = execute_query(query, params, db_name='heavy_analysis.db')
        
        if not result:
            return {}
            
        raw = result[0]
        # Konvertera alla numeriska värden till float/int för typ-säkerhet
        stats = {k: (float(v) if isinstance(v, (int, float)) else 0.0) for k, v in raw.items()}
        
        # Calculate derived stats
        total_actions = stats['total_actions']
        if total_actions > 0:
            # Aggression Factor = (Raises + Bets) / Calls
            aggression_factor = (stats['total_raises'] / max(stats['total_calls'], 1))
            
            # Fold to aggression
            fold_pct = (stats['total_folds'] / total_actions) * 100
            
            # Positional tendencies
            pos_tendency = "Unknown"
            if stats['early_pos_hands'] + stats['late_pos_hands'] > 0:
                late_pct = stats['late_pos_hands'] / (stats['early_pos_hands'] + stats['late_pos_hands'])
                if late_pct > 0.6:
                    pos_tendency = "Late Position Player"
                elif late_pct < 0.4:
                    pos_tendency = "Early Position Player" 
                else:
                    pos_tendency = "Balanced Position"
            
            # Round all numeric values
            formatted_stats = {
                'total_hands': stats['total_hands'],
                'total_actions': total_actions,
                'vpip': round(stats.get('vpip', 0), 1),
                'pfr': round(stats.get('pfr', 0), 1),
                'aggression_factor': round(aggression_factor, 2),
                'fold_percentage': round(fold_pct, 1),
                'position_tendency': pos_tendency,
                'preflop_score': round(stats.get('preflop_avg', 0), 1),
                'flop_score': round(stats.get('flop_avg', 0), 1), 
                'turn_score': round(stats.get('turn_avg', 0), 1),
                'river_score': round(stats.get('river_avg', 0), 1),
                'overall_score': round(stats.get('overall_j_score', 0), 1),
                'avg_bet_size': round(stats.get('avg_bet_size', 0), 2),
                'avg_pot_bb': round(stats.get('avg_pot_size', 0) / 100, 1),  # Convert to BB
                'max_pot_bb': round(stats.get('max_pot_played', 0) / 100, 1),
                'street_distribution': {
                    'preflop': stats.get('preflop_actions', 0),
                    'flop': stats.get('flop_actions', 0),
                    'turn': stats.get('turn_actions', 0),
                    'river': stats.get('river_actions', 0)
                }
            }
            
            return formatted_stats
        
        return {}
        
    except Exception as e:
        log.error(f"Detailed stats query failed: {e}")
        return {}

def get_hand_detailed_view(hand_id: str) -> dict:
    """
    Get comprehensive hand details for viewer
    """
    # Get basic hand info
    hand_info_query = """
    SELECT h.*, 
           GROUP_CONCAT(DISTINCT s.street || ':' || s.board) as street_boards
    FROM hand_info h
    LEFT JOIN streets s ON h.hand_id = s.hand_id
    WHERE h.hand_id = ?
    GROUP BY h.hand_id
    """
    
    # Get all players
    players_query = """
    SELECT * FROM players WHERE hand_id = ?
    ORDER BY position
    """
    
    # Get all actions in order
    actions_query = """
    SELECT * FROM actions 
    WHERE hand_id = ?
    ORDER BY action_order ASC
    """
    
    try:
        hand_info = execute_query(hand_info_query, (hand_id,), db_name='heavy_analysis.db')
        players = execute_query(players_query, (hand_id,), db_name='heavy_analysis.db')
        actions = execute_query(actions_query, (hand_id,), db_name='heavy_analysis.db')
        
        if not hand_info:
            return {}
        
        # Parse street boards
        street_boards = {}
        if hand_info[0]['street_boards']:
            for street_board in str(hand_info[0]['street_boards']).split(','):
                if ':' in street_board:
                    street, board = street_board.split(':', 1)
                    street_boards[street] = board
        
        return {
            'hand_info': hand_info[0],
            'players': players,
            'actions': actions,
            'street_boards': street_boards,
            'hand_id': hand_id
        }
        
    except Exception as e:
        log.error(f"Hand detailed view query failed: {e}")
        return {} 

def get_detailed_player_stats(player_id: str) -> dict:
    """Get basic stats for a specific player"""
    return {}  # This is filled by player_row_new

def debug_bb100_calculation(limit: int = 5) -> list:
    """Debug BB/100 calculation for top players"""
    try:
        query = """
        WITH player_hands AS (
            SELECT 
                a.player_id,
                a.nickname,
                COUNT(DISTINCT a.hand_id) AS hands_played,
                COUNT(DISTINCT p.hand_id) AS hands_with_results
            FROM actions a
            LEFT JOIN players p ON a.hand_id = p.hand_id AND a.position = p.position
            WHERE a.player_id IS NOT NULL AND a.player_id != ''
            GROUP BY a.player_id, a.nickname
            HAVING hands_played > 10
        ),
        winnings AS (
            SELECT 
                a.player_id,
                SUM(p.money_won) AS total_winnings,
                COUNT(DISTINCT CASE WHEN p.money_won IS NOT NULL THEN p.hand_id END) AS hands_with_winnings
            FROM actions a
            LEFT JOIN players p ON a.hand_id = p.hand_id AND a.position = p.position
            WHERE a.player_id IS NOT NULL AND a.player_id != ''
            GROUP BY a.player_id
        ),
        blinds AS (
            SELECT 
                a.player_id,
                AVG(h.big_blind) AS avg_big_blind,
                MIN(h.big_blind) AS min_big_blind,
                MAX(h.big_blind) AS max_big_blind,
                COUNT(DISTINCT h.hand_id) AS hands_with_blinds
            FROM actions a
            LEFT JOIN hand_info h ON a.hand_id = h.hand_id
            WHERE a.player_id IS NOT NULL AND a.player_id != ''
            GROUP BY a.player_id
        )
        SELECT 
            ph.player_id,
            ph.nickname,
            ph.hands_played,
            ph.hands_with_results,
            w.total_winnings,
            w.hands_with_winnings,
            b.avg_big_blind,
            b.min_big_blind,
            b.max_big_blind,
            b.hands_with_blinds,
            ROUND(CASE WHEN b.avg_big_blind > 0 
                       THEN (w.total_winnings / b.avg_big_blind) / ph.hands_played * 100 
                  END, 2) AS calculated_bb100
        FROM player_hands ph
        LEFT JOIN winnings w ON ph.player_id = w.player_id
        LEFT JOIN blinds b ON ph.player_id = b.player_id
        ORDER BY ph.hands_played DESC
        LIMIT ?
        """
        
        results = execute_query(query, (limit,), db_name='heavy_analysis.db')
        log.info(f"BB/100 debug for {limit} players:")
        for r in results:
            log.info(f"Player: {r['nickname']} - Hands: {r['hands_played']}, "
                    f"Winnings: {r['total_winnings']}, Avg BB: {r['avg_big_blind']}, "
                    f"BB/100: {r['calculated_bb100']}")
        return results
        
    except Exception as e:
        log.error(f"BB/100 debug query failed: {e}")
        return []

def search_hands_advanced(
    player_filter: str = "",
    min_pot: int = 0,
    limit: int = 50
) -> list:
    """
    Söker efter händer baserat på filter
    
    Args:
        player_filter: Spelarnamn att filtrera på
        min_pot: Minsta pottstorlek
        limit: Max antal resultat
        
    Returns:
        list: Lista med händer
    """
    query = """
    SELECT DISTINCT
        h.hand_id,
        h.hand_date,
        h.big_blind,
        h.pot_type,
        h.players_cnt,
        MAX(a.pot_after) as final_pot,
        GROUP_CONCAT(DISTINCT p.nickname) as players,
        CASE 
            WHEN SUM(p.money_won) > 0 THEN p.nickname 
            ELSE 'Split' 
        END as winner
    FROM hand_info h
    JOIN actions a ON h.hand_id = a.hand_id
    JOIN players p ON h.hand_id = p.hand_id
    WHERE 1=1
    """
    
    params = []
    
    if player_filter:
        query += " AND p.nickname LIKE ?"
        params.append(f"%{player_filter}%")
    
    if min_pot > 0:
        query += " AND a.pot_after >= ?"
        params.append(min_pot * 100)  # Konvertera till chips (BB * 100)
    
    query += """
    GROUP BY h.hand_id
    ORDER BY h.hand_date DESC, h.seq DESC
    LIMIT ?
    """
    params.append(limit)
    
    results = execute_query(query, tuple(params))
    
    # Formatera resultaten
    for hand in results:
        hand['pot_size_bb'] = round(_to_float(hand.get('final_pot')) / max(_to_float(hand.get('big_blind')), 1), 1)
        hand['timestamp'] = hand['hand_date']
        
    return results 