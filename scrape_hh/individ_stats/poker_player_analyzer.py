import pandas as pd
import sqlite3

DB_PATH = "heavy_analysis.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_players():
    with get_connection() as conn:
        df = pd.read_sql_query("""
            SELECT DISTINCT player_id 
            FROM main 
            WHERE player_id IS NOT NULL 
            AND total_hands > 50
            ORDER BY total_hands DESC
            LIMIT 100
        """, conn)
    return df["player_id"].tolist()

def load_player_overview(player_id=None):
    with get_connection() as conn:
        if player_id:
            df = pd.read_sql_query("SELECT * FROM main WHERE player_id = ?", conn, params=(player_id,))
        else:
            df = pd.read_sql_query("SELECT * FROM main WHERE total_hands > 50 ORDER BY total_hands DESC", conn)
    return df

def load_detailed_actions(player_id=None, filters=None):
    base_query = """
        SELECT
            hand_id, player_id, position, street, action_type, action_label,
            amount, hole_cards, community_cards, hand_strength, pot_before,
            money_won, net_win, table_size, active_players_count, pot_type,
            stakes, raise_percentage, bet_size_category, player_intention,
            created_at
        FROM detailed_actions
        WHERE 1=1
    """
    params = []
    if player_id:
        base_query += " AND player_id = ?"
        params.append(player_id)
    if filters:
        if filters.get("position") and filters["position"] != "ALL":
            base_query += " AND position = ?"
            params.append(filters["position"])
        if filters.get("street") and filters["street"] != "ALL":
            base_query += " AND street = ?"
            params.append(filters["street"])
        if filters.get("action_label") and filters["action_label"] != "ALL":
            base_query += " AND action_label = ?"
            params.append(filters["action_label"])
        if filters.get("table_size") and filters["table_size"] != "ALL":
            base_query += " AND table_size = ?"
            params.append(filters["table_size"])
        if filters.get("pot_type") and filters["pot_type"] != "ALL":
            base_query += " AND pot_type = ?"
            params.append(filters["pot_type"])
        if filters.get("min_hand_strength"):
            base_query += " AND hand_strength >= ?"
            params.append(filters["min_hand_strength"])
        if filters.get("max_hand_strength"):
            base_query += " AND hand_strength <= ?"
            params.append(filters["max_hand_strength"])
    base_query += " ORDER BY created_at DESC LIMIT 10000"
    with get_connection() as conn:
        df = pd.read_sql_query(base_query, conn, params=params)
    return df

def get_population_stats(metric, filters=None):
    metric_mapping = {
        "vpip": "vpip",
        "pfr": "pfr",
        "hand_strength": "hand_strength",
        "raise_percentage": "raise_percentage",
        "net_win": "net_win",
    }
    if metric in ("vpip", "pfr"):
        query = f"SELECT {metric} AS value FROM main WHERE {metric} > 0 AND {metric} < 100"
        with get_connection() as conn:
            df = pd.read_sql_query(query, conn)
    else:
        col = metric_mapping.get(metric, metric)
        query = f"SELECT {col} AS value FROM detailed_actions WHERE {col} IS NOT NULL"
        params = []
        if filters:
            if filters.get("position") and filters["position"] != "ALL":
                query += " AND position = ?"
                params.append(filters["position"])
            if filters.get("street") and filters["street"] != "ALL":
                query += " AND street = ?"
                params.append(filters["street"])
        with get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
    if df.empty:
        return {"mean": 0, "std": 0, "median": 0, "count": 0, "pct25": 0, "pct75": 0}
    return {
        "mean": df["value"].mean(),
        "std": df["value"].std(),
        "median": df["value"].median(),
        "count": len(df),
        "pct25": df["value"].quantile(0.25),
        "pct75": df["value"].quantile(0.75),
    }

# Exempel på hur man använder funktionerna:
if __name__ == "__main__":
    # Visa alla spelare med >50 händer
    print(load_players())
    # Visa översikt för en spelare
    print(load_player_overview("SPELARE_ID"))
    # Visa detaljerade actions med filter
    print(load_detailed_actions("SPELARE_ID", filters={"position": "BTN"}))
    # Visa statistik för populationen
    print(get_population_stats("vpip"))
