import os
import sqlite3
import argparse

# Funktion för att skapa och köra SQL-frågor
def execute_query(query, filters):
    """Utför SQL-frågan baserat på argumenten och filtren"""
    # Hämta den korrekta databasanslutningen
    conn = get_database_connection()
    cursor = conn.cursor()
    
    # Lägg till WHERE-klausul baserat på filter
    if filters:
        query += " WHERE " + " AND ".join([f"{key} = '{value}'" for key, value in filters.items()])
    
    cursor.execute(query)
    
    # Skriv ut resultaten
    results = cursor.fetchall()
    for row in results:
        print(row)
    
    # Stäng anslutningen
    conn.close()

# Funktion för att skapa databasanslutning till rätt databas
def get_database_connection():
    """Hämta korrekt databasanslutning genom att navigera upp till roten och ner till mappen med databasen"""
    # Hämta skriptets aktuella mapp
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Navigera upp till roten av projektet
    project_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))

    # Bygg sökvägen till databasen
    database_path = os.path.join(project_root, "local_data", "database", "heavy_analysis.db")

    # Anslut till databasen
    conn = sqlite3.connect(database_path)
    return conn

# Bygg SQL-frågor baserat på användarens val
def build_query(query_type, filters):
    """Bygg olika SQL-frågor baserat på användarens behov"""
    if query_type == 'average_performance':
        query = """
        SELECT street, position, 
               AVG(r_perf) AS avg_r_perf, AVG(r_opp) AS avg_r_opp, 
               AVG(c_perf) AS avg_c_perf, AVG(c_opp) AS avg_c_opp, 
               AVG(x_perf) AS avg_x_perf, AVG(x_opp) AS avg_x_opp, 
               AVG(f_perf) AS avg_f_perf, AVG(f_opp) AS avg_f_opp, 
               AVG(avg_score) AS avg_avg_score, AVG(avg_diff) AS avg_avg_diff
        FROM actions
        """
    elif query_type == 'best_hands':
        query = """
        SELECT position, combo, AVG(best) AS avg_best
        FROM preflop_scores
        """
    elif query_type == 'action_summary':
        query = """
        SELECT street, COUNT(*) AS total_hands, AVG(action_score) AS avg_action_score
        FROM actions
        """
    elif query_type == 'player_performance':
        query = """
        SELECT position, nickname, AVG(action_score) AS avg_action_score
        FROM actions
        WHERE street = 'flop'
        """
    else:
        raise ValueError("Invalid query type")

    return query

# Funktion för att hantera kommandoradsargument
def parse_arguments():
    """Hantera kommandoradsargument"""
    parser = argparse.ArgumentParser(description="Kör dynamiska SQL-frågor på pokerdata.")
    
    # Frågetyp (avg_performance, best_hands, action_summary, player_performance)
    parser.add_argument('--query_type', required=True, choices=['average_performance', 'best_hands', 'action_summary', 'player_performance'],
                        help="Typen av fråga att köra (average_performance, best_hands, action_summary, player_performance)")

    # Filterargument
    parser.add_argument('--street', type=str, help="Filtrera på street (t.ex. 'preflop', 'flop', 'turn', 'river')")
    parser.add_argument('--position', type=str, help="Filtrera på position (t.ex. 'BB', 'BTN', 'CO')")
    parser.add_argument('--player_id', type=str, help="Filtrera på specifik spelare (player_id)")
    parser.add_argument('--combo', type=str, help="Filtrera på handkombination (t.ex. 'Ah,Ad')")
    parser.add_argument('--action_type', type=str, help="Filtrera på specifik åtgärd (t.ex. 'raise', 'call', 'fold')")

    return parser.parse_args()

def main():
    # Hämta argument från kommandoraden
    args = parse_arguments()

    # Bygg filter baserat på användarens input
    filters = {}
    if args.street:
        filters['street'] = args.street
    if args.position:
        filters['position'] = args.position
    if args.player_id:
        filters['player_id'] = args.player_id
    if args.combo:
        filters['combo'] = args.combo
    if args.action_type:
        filters['action_label'] = args.action_type

    # Bygg och kör SQL-frågan baserat på val av frågetyp
    query = build_query(args.query_type, filters)
    execute_query(query, filters)

if __name__ == '__main__':
    main()
