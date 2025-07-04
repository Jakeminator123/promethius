#!/usr/bin/env python3
"""
4_action_label.py
─────────────────
Lägger in action_label + ip_status i tabellen actions (heavy_analysis.db).

• Läser regler från action_rules.yml för flexibilitet
• Skapar kolumnerna om de saknas
• Kör bara på rader där action_label IS NULL (kan köras om)

Kör:  python 4_action_label.py
      python 4_action_label.py -db "C:/sökväg/annan.db"
"""

from __future__ import annotations
import argparse, sqlite3, sys, re, yaml
from pathlib import Path
from typing import List, Tuple, Dict, Any

# ─────────────────── 0. projektrot & db ────────────────────────────
# Import centraliserad path-hantering
sys.path.append(str(Path(__file__).resolve().parent))
from script_paths import ROOT, DST_DB

DEFAULT_DB = DST_DB  # Använder centraliserad path-hantering
YAML_PATH = Path(__file__).parent / "action_rules.yml"

# ─────────────────── Ladda YAML-regler ─────────────────────────────
def load_action_rules() -> List[Dict[str, Any]]:
    """Läser action rules från YAML-filen."""
    if not YAML_PATH.exists():
        sys.exit(f"❌ {YAML_PATH} saknas!")
    
    with open(YAML_PATH, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Sortera regler efter prioritet
    rules = data.get('rules', [])
    return sorted(rules, key=lambda r: r.get('priority', 9999))

# ─────────────────── Fallback-regler (om YAML misslyckas) ──────────
FALLBACK_RULES = {
    "preflop": {1: "open", 2: "2bet", 3: "3bet", 4: "4bet", 5: "5bet", 6: "6bet"},
    "postflop": {
        "first_bet": "bet", "first_raise": "2bet", "second_raise": "3bet",
        "checkraise": "checkraise", "donk": "lead", "probe": "probe"
    }
}

# ─────────────────── 1. PositionTracker ────────────────────────────
class PositionTracker:
    """IP/OOP-hjälp med UTG↔LJ-alias för 6-max."""
    ORDER_6MAX = ["UTG/LJ", "HJ", "CO", "BTN", "SB", "BB"]

    def __init__(self, preflop_pos: List[str]):
        order: List[str] = []
        for spot in self.ORDER_6MAX:
            if "/" in spot:                      # "UTG/LJ"
                a, b = spot.split("/")
                order.append(a if a in preflop_pos else b if b in preflop_pos else None)
            elif spot in preflop_pos:
                order.append(spot)
        self.order = [p for p in order if p]     # filtrera bort None
        self.flop_btn = self.order.index("BTN") if "BTN" in self.order else 0

    def ip_status(self, street: str, pos: str) -> str:
        if street.lower() == "preflop":
            return "IP" if pos == "BTN" else "OOP"
        idx = self.order.index(pos)
        return "IP" if idx == (self.flop_btn - 1) % len(self.order) else "OOP"

# ─────────────────── 2. ActionTracker (YAML-baserad) ───────────────
class ActionTracker:
    """Etiketterar actions baserat på YAML-regler."""
    def __init__(self):
        self.rules = load_action_rules()
        self.hands_history = {}  # hand_id -> hand data
        self.new_street("preflop")
        
    def new_street(self, street: str):
        self.street = street.lower()
        self.raise_cnt = 0
        self.bet_cnt = 0
        self.checks = set()
        self.first_bet = True
        self.street_actions = []
        
    def record_action(self, hand_id: str, street: str, pos: str, tok: str):
        """Sparar historik för regelutvärdering."""
        if hand_id not in self.hands_history:
            self.hands_history[hand_id] = {
                'streets': {},
                'preflop_aggressor': None,
                'prev_street_checks': 0
            }
        
        hand = self.hands_history[hand_id]
        if street not in hand['streets']:
            hand['streets'][street] = []
        
        hand['streets'][street].append({'pos': pos, 'action': tok})
        
        # Spåra preflop aggressor
        if street.lower() == 'preflop' and tok.startswith('r') and not hand['preflop_aggressor']:
            hand['preflop_aggressor'] = pos
            
    def evaluate_conditions(self, conditions: Dict, context: Dict) -> bool:
        """Utvärderar när-villkor från YAML."""
        for key, expected in conditions.items():
            actual = context.get(key)
            
            # Specialhantering för olika villkorstyper
            if key.endswith('_gt'):
                base_key = key[:-3]
                if context.get(base_key, 0) <= expected:
                    return False
            elif key.endswith('_contains'):
                base_key = key[:-9]
                if expected not in context.get(base_key, []):
                    return False
            elif actual != expected:
                return False
                
        return True
        
    def process(self, hand_id: str, street: str, pos: str, tok: str, ip: str) -> str:
        # Ny gata?
        if street.lower() != self.street:
            self.new_street(street)
            
        # Spara action för historik
        self.record_action(hand_id, street, pos, tok)
        
        # ── Passiva handlingar ─────────────────────────────
        if tok == "x":
            self.checks.add(pos)
            return "check"
        if tok == "f":
            return "fold"
        if tok == "c":
            # Float logic
            if ip == "IP" and self.raise_cnt == 0 and street.lower() != "preflop":
                return "float"
            return "call"
            
        # ── Raises/Bets ────────────────────────────────────
        action_type = None
        if tok.startswith("r"):
            action_type = "raise"
            self.raise_cnt += 1
        elif tok.startswith("b"):
            action_type = "bet"
            self.bet_cnt += 1
            
        if not action_type:
            return "unknown"
            
        # Bygg kontext för regelutvärdering
        hand = self.hands_history.get(hand_id, {})
        player_prev_actions = []
        
        # Samla spelarens tidigare actions denna gata
        for act in hand.get('streets', {}).get(street, []):
            if act['pos'] == pos and act != hand['streets'][street][-1]:
                player_prev_actions.append(act['action'])
                
        # Kolla om förra gatan slutade med två checkar
        prev_streets = ['preflop', 'flop', 'turn', 'river']
        prev_street_idx = prev_streets.index(street.lower()) - 1
        prev_street_ended_with_checks = False
        prev_street_had_bet = False
        
        if prev_street_idx >= 0:
            prev_street = prev_streets[prev_street_idx]
            prev_actions = hand.get('streets', {}).get(prev_street, [])
            if len(prev_actions) >= 2:
                if prev_actions[-1]['action'] == 'x' and prev_actions[-2]['action'] == 'x':
                    prev_street_ended_with_checks = True
                # Kolla om det fanns bet/raise förra gatan
                for act in prev_actions:
                    if act['action'].startswith(('b', 'r')):
                        prev_street_had_bet = True
                        break
                        
        context = {
            'current_token': action_type,
            'raise_count': self.raise_cnt - 1,  # antal raises innan denna
            'raise_count_plus1': self.raise_cnt + 1,
            'bet_count': self.bet_cnt,
            'player_prev_actions': player_prev_actions,
            'player_position': ip,
            'is_preflop_aggressor': pos == hand.get('preflop_aggressor'),
            'first_bet_this_street': self.first_bet and action_type == 'bet',
            'prev_street_ended_with_two_checks': prev_street_ended_with_checks,
            'prev_street_had_bet': prev_street_had_bet
        }
        
        # Utvärdera YAML-regler
        current_scope = street.upper() if street.upper() in ['PREFLOP', 'FLOP', 'TURN', 'RIVER'] else 'POSTFLOP'
        if current_scope in ['FLOP', 'TURN', 'RIVER']:
            postflop_scope = 'POSTFLOP'
        else:
            postflop_scope = None
            
        for rule in self.rules:
            # Kolla scope
            rule_scope = rule.get('scope', 'ANY')
            if rule_scope not in ['ANY', current_scope]:
                if not (postflop_scope and rule_scope == postflop_scope):
                    continue
                    
            # Utvärdera villkor
            conditions = rule.get('when', {})
            if self.evaluate_conditions(conditions, context):
                # Applicera regel
                if 'result' in rule:
                    result = rule['result']
                elif 'result_template' in rule:
                    # Ersätt variabler i template
                    template = rule['result_template']
                    for var, value in context.items():
                        template = template.replace(f"{{{var}}}", str(value))
                    result = template
                else:
                    continue
                    
                if result:  # Tom sträng = använd fallback
                    if self.first_bet and action_type == 'bet':
                        self.first_bet = False
                    return result
                    
        # Fallback till enkla regler om ingen YAML-regel matchar
        if street.lower() == "preflop" and action_type == "raise":
            return FALLBACK_RULES["preflop"].get(self.raise_cnt, f"{self.raise_cnt}bet")
        elif action_type == "bet":
            return "bet"
        elif action_type == "raise":
            if self.raise_cnt == 1:
                return "raise"
            return f"{self.raise_cnt}bet"
            
        return "unknown"

# ─────────────────── 3. DB-helpers ─────────────────────────────────
def ensure_cols(con: sqlite3.Connection):
    cols = {c[1] for c in con.execute("PRAGMA table_info(actions)")}
    if "action_label" not in cols:
        con.execute("ALTER TABLE actions ADD COLUMN action_label TEXT")
    if "ip_status" not in cols:
        con.execute("ALTER TABLE actions ADD COLUMN ip_status TEXT")

def process_hand(cur: sqlite3.Cursor, hid: str, act_tr: ActionTracker) -> List[Tuple[str,str,int]]:
    rows = cur.execute(
        "SELECT rowid, street, position, action "
        "FROM actions WHERE hand_id=? ORDER BY action_order", (hid,)
    ).fetchall()
    if not rows: return []
    
    pre = [r["position"] for r in rows if r["street"] == "preflop"]
    pos_tr = PositionTracker(pre)
    
    # Reset tracker för ny hand
    act_tr.new_street("preflop")
    
    out, last_st = [], None
    for r in rows:
        if r["street"] != last_st:
            act_tr.new_street(r["street"])
            last_st = r["street"]
        ip = pos_tr.ip_status(r["street"], r["position"])
        label = act_tr.process(hid, r["street"], r["position"], r["action"], ip)
        out.append((label, ip, r["rowid"]))
    return out

# ─────────────────── 4. main ───────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("-db")
    a = p.parse_args()
    
    db = Path(a.db).expanduser().resolve() if a.db else DEFAULT_DB
    if not db.exists():
        sys.exit(f"❌ hittar inte {db}")
        
    try:
        # Testa att YAML kan laddas
        test_rules = load_action_rules()
        print(f"✓ Laddat {len(test_rules)} regler från {YAML_PATH.name}")
    except Exception as e:
        print(f"⚠️  Fel vid YAML-laddning: {e}")
        print("   Använder inbyggda fallback-regler istället")

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    ensure_cols(con)
    cur = con.cursor()
    
    # Skapa en ActionTracker som återanvänds
    act_tr = ActionTracker()

    hids = [r[0] for r in cur.execute(
        "SELECT DISTINCT hand_id FROM actions WHERE action_label IS NULL")]
    total = 0
    
    for hid in hids:
        upd = process_hand(cur, hid, act_tr)
        if upd:
            cur.executemany(
                "UPDATE actions SET action_label=?, ip_status=? WHERE rowid=?", upd)
            total += len(upd)
            if total and total % 5000 == 0:
                con.commit()
                print(f"✓ {total:,} actions uppdaterade …")
                
    con.commit()
    con.close()
    print(f"✅ klart – {total:,} actions fick action_label + ip_status")

if __name__ == "__main__":
    main()
