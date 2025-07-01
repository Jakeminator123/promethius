import json
import sqlite3
import pandas as pd

BET_ACTIONS = {"bet", "raise"}
POT_CONTRIB = BET_ACTIONS | {"call", "post_small_blind", "post_big_blind", "post_ante"}
STAGES = ("preflop", "flop", "turn", "river")

def parse_int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None

def fetch_hand(conn, hand_id):
    """Returnerar (actions, start_pot)"""
    (raw_json,) = conn.execute(
        "SELECT data_json FROM hand_analysis WHERE hand_id=?", (hand_id,)
    ).fetchone()
    data = json.loads(raw_json)
    # Actions
    if isinstance(data.get("actions"), list):
        actions = data["actions"]
    else:
        hdr_rows = data["actions"]
        actions = [dict(zip(hdr_rows["headers"], r)) for r in hdr_rows["rows"]]
    # Blinds & startpot
    blinds = data.get("blinds", {})
    sb   = blinds.get("sb") or 0
    bb   = blinds.get("bb") or 0
    ante = blinds.get("ante") or 0
    n_players = len(data.get("players", []))
    start_pot = sb + bb + ante * n_players
    return actions, start_pot

def classify_kind(act):
    txt = ""
    for k in ("action", "Action", "action_type", "ActionType", "Decision"):
        v = act.get(k)
        if v:
            txt = str(v).lower()
            break
    raw = (act.get("Raw") or act.get("raw") or "").lower()
    txt_full = f"{txt} {raw}"
    if any(w in txt_full for w in ("fold", " muck")):
        return "fold"
    if "call" in txt_full:
        return "call"
    if any(w in txt_full for w in ("raise", "3bet", "donk", "probe", "blockbet", "overbet", "2bet")):
        return "raise"
    if "bet" in txt_full:
        return "bet"
    return ""

def derive_amount(act):
    for k in ("amount", "Amount", "size", "Size", "value", "Value"):
        amt = parse_int(act.get(k))
        if amt is not None:
            return amt
    sb = parse_int(act.get("stack_before") or act.get("StackBefore"))
    sa = parse_int(act.get("stack_after") or act.get("StackAfter"))
    if sb is not None and sa is not None:
        return sb - sa
    return None

def derive_stage(act, fallback):
    for k in ("street", "Street", "round", "Round", "phase", "Phase"):
        if k in act and act[k]:
            s = str(act[k]).lower()
            for st in STAGES:
                if st in s:
                    return st
    raw = (act.get("Raw") or "").lower()
    for st in STAGES:
        if st in raw:
            return st
    return fallback

def extract_bets(actions, pot0=0):
    pot, stage = pot0, "preflop"
    bets = []
    for act in actions:
        stage = derive_stage(act, stage)
        kind  = classify_kind(act)
        if kind not in POT_CONTRIB:
            continue
        amt = derive_amount(act)
        if amt is None:
            continue
        pot_before = parse_int(act.get("pot_before") or act.get("PotBefore")) or pot
        strength   = parse_int(act.get("strength") or act.get("j_score") or act.get("jscore"))
        if kind in BET_ACTIONS:
            ratio = round(amt / pot_before, 3) if pot_before else None
            bets.append((stage, act.get("player_id") or act.get("Player") or "unknown",
                         kind, amt, pot_before, ratio, strength))
        pot = pot_before + amt
    return bets

def bets_to_df(bets):
    df = pd.DataFrame(
        bets,
        columns=["stage", "player", "action", "amount", "pot_before", "ratio", "strength"]
    )
    df["ratio_clipped"] = df["ratio"].clip(upper=1.5)
    df["ratio_pct"] = df["ratio_clipped"].fillna(0.5) * 100
    df["clamped"] = df["ratio"] > 1.5
    df["errorflag"] = df["ratio"].isna()
    df["color_stage"] = df.apply(
        lambda r: "error" if (r["errorflag"] or r["clamped"]) else r["stage"], axis=1
    )
    return df

# Exempel på körning
def main():
    # Byt ut mot din lokala databas
    db_path = "heavy_analysis.db"
    with sqlite3.connect(db_path) as conn:
        hand_id = "DIN_HAND_ID"
        actions, pot0 = fetch_hand(conn, hand_id)
        bets = extract_bets(actions, pot0)
        df = bets_to_df(bets)
        print(df.head())

if __name__ == "__main__":
    main()
