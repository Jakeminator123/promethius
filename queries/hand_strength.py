"""
Hand strength calculation module for poker hands
Based on preflop rankings and postflop evaluation
"""
import re
from typing import Dict, List, Optional
import logging

log = logging.getLogger(__name__)

# Try to import treys for postflop evaluation
try:
    from treys import Card, Evaluator
    TREYS_AVAILABLE = True
except ImportError:
    log.warning("treys package not available - using fallback for postflop")
    TREYS_AVAILABLE = False
    Card = None
    Evaluator = None

# Card cleaning regex
_CARD_RE = re.compile(r"[2-9TJQKA][shdc]", re.I)

# Rank values
RANKS = {r: i for i, r in enumerate("..23456789TJQKA", 0)}

# Chen formula base values
CHEN_BASE = {
    "A": 10, "K": 8, "Q": 7, "J": 6,
    "T": 5, "9": 4.5, "8": 4, "7": 3.5,
    "6": 3, "5": 2.5, "4": 2, "3": 1.5, "2": 1,
}

# Built-in preflop range (best to worst)
PREFLOP_RANGE_TEXT = """
AA, KK, QQ, AKs, JJ, AQs, KQs, AJs, KJs, TT, AKo, ATs, QJs, KTs, QTs, JTs, 99, AQo, A9s, KQo,
88, K9s, T9s, A8s, Q9s, J9s, AJo, A5s, 77, A7s, KJo, A4s, A6s, QJo, 66, K8s, T8s, A2s, A3s, 
89s, J8s, ATo, Q8s, K7s, KTo, 55, JTo, 78s, QTo, 44, 22, 33, K6s, 79s, K5s, 67s, T7s, K4s,
K3s, K2s, Q7s, 68s, 56s, J7s, 45s, Q6s, 57s, 69s, Q5s, 46s, Q4s, Q3s, T9o, T6s, Q2s, A9o,
35s, 58s, J6s, J9o, K9o, J5s, Q9o, 34s, 47s, J4s, J3s, 59s, J2s, 36s, A8o, 25s, T5s, 48s,
T4s, T3s, 24s, T2s, 89o, T8o, A5o, A7o, 37s, A4o, 23s, 49s, 39s, J8o, A3o, A6o, 29s, K8o,
A2o, 78o, Q8o, 38s, 28s, 79o, 27s, 67o, K7o, 56o, T7o, K6o, 68o, 45o, K5o, J7o, 57o, Q7o,
K4o, K3o, K2o, 69o, 46o, Q6o, 35o, 58o, T6o, Q5o, 34o, Q4o, Q3o, Q2o, 47o, J6o, 36o, J5o,
25o, J4o, J3o, 24o, J2o, 48o, T5o, T4o, T3o, T2o, 23o, 37o, 49o, 39o, 29o, 38o, 28o, 27o
"""

# Global cache for preflop scores
PREFLOP_HAND_SCORE: Dict[str, float] = {}

# Treys evaluator instance
if TREYS_AVAILABLE and Evaluator is not None:
    _evaluator = Evaluator()
else:
    _evaluator = None


def _clean_card_string(raw: Optional[str]) -> str:
    """Clean card string to standard format: 'Jc, Kh, Ts' -> 'JcKhTs'"""
    if not raw:
        return ""
    return "".join(_CARD_RE.findall(raw))


def _canonical_hole(hole: str) -> str:
    """Convert hole cards to canonical form: 'AhKd' -> 'AKo', 'KhKd' -> 'KK'"""
    if len(hole) != 4:
        return ""
    r1, s1, r2, s2 = hole[0], hole[1], hole[2], hole[3]
    if RANKS[r2] > RANKS[r1]:
        r1, s1, r2, s2 = r2, s2, r1, s1
    if r1 == r2:
        return f"{r1}{r2}"
    return f"{r1}{r2}{'s' if s1 == s2 else 'o'}"


def _chen_score(hole: str) -> float:
    """Calculate Chen formula score (0-20) and normalize to 0-1"""
    if len(hole) != 4:
        return 0.25
    
    r1, s1, r2, s2 = hole[0], hole[1], hole[2], hole[3]
    if RANKS[r2] > RANKS[r1]:
        r1, s1, r2, s2 = r2, s2, r1, s1
    
    pts = CHEN_BASE[r1]
    
    # Pair bonus
    if r1 == r2:
        pts = max(pts * 2, 5)
        if r1 == "5":
            pts += 1
    
    # Suited bonus
    if s1 == s2:
        pts += 2
    
    # Gap penalty
    gap = RANKS[r1] - RANKS[r2] - 1
    pts -= [0, 0, 1, 2, 4, 5][min(gap, 5)]
    
    # Straight potential bonus
    if gap <= 1 and RANKS[r1] < RANKS["Q"]:
        pts += 1
    
    return max(0, pts) / 20.0


def _init_preflop_scores():
    """Initialize preflop hand scores from built-in range"""
    global PREFLOP_HAND_SCORE
    
    # Parse range text
    hands = []
    for token in re.split(r"[,\s]+", PREFLOP_RANGE_TEXT):
        token = token.strip()
        if len(token) == 2:  # Pair
            hands.append(token.upper())
        elif len(token) == 3:  # Suited/offsuit
            r1, r2, suited = token[0].upper(), token[1].upper(), token[2].lower()
            if RANKS[r2] > RANKS[r1]:
                r1, r2 = r2, r1
            hands.append(f"{r1}{r2}{suited}")
    
    # Assign scores based on position in range
    n = len(hands)
    for idx, hand in enumerate(hands):
        PREFLOP_HAND_SCORE[hand] = 1.0 - (idx / n)
    
    # Fill missing combos with Chen score
    ranks = "AKQJT98765432"
    for i, r1 in enumerate(ranks):
        # Pairs
        par = r1 + r1
        if par not in PREFLOP_HAND_SCORE:
            PREFLOP_HAND_SCORE[par] = _chen_score(par * 2)
        
        # Non-pairs
        for r2 in ranks[i + 1:]:
            for suited in ("s", "o"):
                lbl = f"{r1}{r2}{suited}"
                if lbl not in PREFLOP_HAND_SCORE:
                    chen = _chen_score(r1 + "s" + r2 + ("s" if suited == "s" else "h"))
                    PREFLOP_HAND_SCORE[lbl] = chen * (1.0 if suited == "s" else 0.85)


def _treys_strength(hole: str, board: str) -> float:
    """Calculate made hand strength using treys (0-1)"""
    if not TREYS_AVAILABLE or not _evaluator or Card is None:
        # Fallback: use Chen score reduced by 20%
        return _chen_score(hole) * 0.8
    
    try:
        # Convert to treys format
        h_cards = [hole[i:i+2] for i in range(0, len(hole), 2)]
        b_cards = [board[i:i+2] for i in range(0, len(board), 2)]
        
        # Evaluate hand
        score = _evaluator.evaluate(
            [Card.new(c) for c in b_cards],
            [Card.new(c) for c in h_cards]
        )
        
        # Convert to 0-1 range (lower score = better hand)
        return 1.0 - _evaluator.get_five_card_rank_percentage(score)
    except Exception as e:
        log.error(f"Treys evaluation failed: {e}")
        return _chen_score(hole) * 0.8


def _detect_draws(hole: str, board: str) -> Dict[str, bool]:
    """Detect flush and straight draws"""
    all_cards = [hole[i:i+2] for i in range(0, len(hole), 2)] + \
                [board[i:i+2] for i in range(0, len(board), 2)]
    
    # Count suits for flush draws
    suits: Dict[str, int] = {}
    for c in all_cards:
        if len(c) == 2:
            suits[c[1]] = suits.get(c[1], 0) + 1
    
    flush_draw = any(v == 4 for v in suits.values())
    backdoor_flush = any(v == 3 for v in suits.values())
    
    # Check for straight draws
    ranks = sorted({RANKS[c[0]] for c in all_cards if len(c) == 2})
    open_ended = gutshot = False
    
    for i in range(len(ranks) - 3):
        span = ranks[i + 3] - ranks[i]
        if span == 3 and len(set(ranks[i:i+4])) == 4:
            open_ended = True
        elif span == 4:
            gutshot = True
    
    return {
        "flush": flush_draw,
        "backdoor": backdoor_flush,
        "open_ended": open_ended,
        "gutshot": gutshot
    }


def _draw_equity(hole: str, board: str) -> float:
    """Calculate draw equity (approximate outs / remaining cards)"""
    draws = _detect_draws(hole, board)
    
    outs = 0
    if draws["flush"]:
        outs += 9
    elif draws["backdoor"]:
        outs += 1.5
    
    if draws["open_ended"]:
        outs += 8
    elif draws["gutshot"]:
        outs += 4
    
    # Calculate equity based on remaining cards
    cards_seen = len(hole) // 2 + len(board) // 2
    remaining = 52 - cards_seen
    
    return min(outs / remaining, 1.0)


def get_hand_strength(hole: str, board: str = "", street: str = "preflop") -> int:
    """
    Calculate hand strength (1-100)
    
    Args:
        hole: Hole cards (e.g., "AhKd")
        board: Community cards (e.g., "QsJhTc")
        street: Current street ("preflop", "flop", "turn", "river")
    
    Returns:
        Hand strength from 1-100
    """
    # Initialize preflop scores if needed
    if not PREFLOP_HAND_SCORE:
        _init_preflop_scores()
    
    # Clean inputs
    hole = _clean_card_string(hole)
    board = _clean_card_string(board)
    street = street.lower()
    
    # Validate hole cards
    if len(hole) != 4:
        return 50  # Default middle value for invalid input
    
    # Preflop: use ranking list
    if street == "preflop":
        canonical = _canonical_hole(hole)
        score = PREFLOP_HAND_SCORE.get(canonical, _chen_score(hole))
        return int(score * 99) + 1
    
    # Postflop: combine made hand and draw equity
    made_strength = _treys_strength(hole, board)
    
    if street == "river":
        # No draws on river
        score = made_strength
    else:
        # Weight made hands vs draws
        draw_eq = _draw_equity(hole, board)
        if street == "flop":
            # More weight on draws on flop
            score = 0.7 * made_strength + 0.3 * draw_eq
        else:  # turn
            # Less weight on draws on turn
            score = 0.85 * made_strength + 0.15 * draw_eq
    
    return max(1, min(100, int(score * 99) + 1))


def calculate_hand_strength_batch(actions_data: List[dict]) -> List[dict]:
    """
    Calculate hand strength for a batch of actions
    
    Args:
        actions_data: List of dicts with 'holecards', 'board_cards', 'street'
    
    Returns:
        Same list with added 'hand_strength' field
    """
    # Initialize preflop scores once
    if not PREFLOP_HAND_SCORE:
        _init_preflop_scores()
    
    results = []
    for action in actions_data:
        hole = action.get('holecards', '')
        board = action.get('board_cards', '')
        street = action.get('street', 'preflop')
        
        # Calculate actual hand strength
        strength = get_hand_strength(hole, board, street)
        
        # Add to result
        action['hand_strength'] = strength
        results.append(action)
    
    return results 