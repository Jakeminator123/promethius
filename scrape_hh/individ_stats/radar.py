import plotly.graph_objects as go
import sqlite3

def create_empty_figure():
    fig = go.Figure()
    fig.add_annotation(
        text="No values to show",
        x=0.5, y=0.5,
        xref="paper", yref="paper",
        showarrow=False,
        font=dict(size=16)
    )
    return fig

def load_intention_scores(filepath):
    """Läs in intention scores från fil"""
    intention_scores = {}
    if not filepath:
        return intention_scores
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
        for line in lines[1:]:  # skip header
            if line.strip():
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        intention_scores[" ".join(parts[:-1])] = float(parts[-1])
                    except ValueError:
                        intention_scores[" ".join(parts[:-1])] = 0
    except Exception:
        pass
    return intention_scores

def build_radar_figure(conn, player_id, k=0, street=None, intention_file=None):
    """
    Skapa radar-figur för en spelare.
    conn: sqlite3.Connection
    player_id: str
    k: visa top k intentioner (0 = alla)
    street: filtera på 'preflop', 'flop', 'turn', 'river' eller None
    intention_file: path till intentions.txt
    """
    # Hämta intentioner för spelaren
    query = """
        SELECT intention, n_actions
        FROM player_intention
        WHERE player_id = ? AND n_actions > 0
    """
    params = [player_id]
    if street and street.lower() in ('preflop', 'flop', 'turn', 'river'):
        query += " AND street = ?"
        params.append(street.upper())
    query += " ORDER BY n_actions DESC"
    player_intentions = conn.execute(query, params).fetchall()
    if not player_intentions:
        return create_empty_figure()

    # Top k
    if k and k > 0 and len(player_intentions) > k:
        player_intentions = player_intentions[:k]
    axes = [row[0] for row in player_intentions]
    counts = {row[0]: row[1] for row in player_intentions}
    if not axes:
        return create_empty_figure()
    # Läs intention scores
    intention_scores = load_intention_scores(intention_file)
    player_max = max(counts.values()) if counts else 1

    def get_score(intention_name):
        base_name = intention_name.split(" - ")[0] if " - " in intention_name else intention_name
        return intention_scores.get(base_name, 0)

    sorted_axes = sorted(axes, key=lambda x: (-get_score(x), x))
    positive_axes = [ax for ax in sorted_axes if get_score(ax) > 0]
    neutral_axes = [ax for ax in sorted_axes if get_score(ax) == 0]
    negative_axes = [ax for ax in sorted_axes if get_score(ax) < 0]
    organized_axes = positive_axes + neutral_axes + negative_axes
    values = [round(counts.get(ax, 0) / player_max, 2) for ax in organized_axes]
    labels = organized_axes.copy()
    axis_types = []
    for ax in organized_axes:
        score = get_score(ax)
        if score > 0:
            axis_types.append("positive")
        elif score < 0:
            axis_types.append("negative")
        else:
            axis_types.append("neutral")
    # Avsluta polygonen
    values.append(values[0])
    labels.append(labels[0])
    axis_types.append(axis_types[0])

    # Data för olika intentionstyper
    positive_values, negative_values, neutral_values = [], [], []
    for value, axis_type in zip(values[:-1], axis_types[:-1]):
        if axis_type == "positive":
            positive_values.append(value)
            negative_values.append(0)
            neutral_values.append(0)
        elif axis_type == "negative":
            positive_values.append(0)
            negative_values.append(value)
            neutral_values.append(0)
        else:
            positive_values.append(0)
            negative_values.append(0)
            neutral_values.append(value)
    positive_values.append(positive_values[0] if positive_values else 0)
    negative_values.append(negative_values[0] if negative_values else 0)
    neutral_values.append(neutral_values[0] if neutral_values else 0)

    fig = go.Figure()
    # Lägg till traces för positiva, negativa, neutrala intentioner
    if any(v > 0 for v in positive_values):
        fig.add_trace(go.Scatterpolar(r=positive_values, theta=labels, fill="toself", name="Positiva Intentioner"))
    if any(v > 0 for v in negative_values):
        fig.add_trace(go.Scatterpolar(r=negative_values, theta=labels, fill="toself", name="Negativa Intentioner"))
    if any(v > 0 for v in neutral_values):
        fig.add_trace(go.Scatterpolar(r=neutral_values, theta=labels, fill="toself", name="Neutrala Intentioner"))
    if len(fig.data) == 0:
        fig.add_trace(go.Scatterpolar(r=values, theta=labels, fill="toself", name=""))
    # Titeln
    title = "Player Intention Profile"
    if street:
        title += f" - {street.upper()}"
    fig.update_layout(title=title)
    return fig

# Exempel på användning
if __name__ == "__main__":
    db_path = "heavy_analysis.db"
    intention_file = "intentions.txt"
    with sqlite3.connect(db_path) as conn:
        fig = build_radar_figure(conn, player_id="DIN_SPELARE", k=0, street=None, intention_file=intention_file)
        fig.show()