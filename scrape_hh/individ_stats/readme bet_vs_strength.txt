Readme / Databasöversikt
Använda tabeller och kolumner:

Tabell: hand_analysis

Kolumner:

hand_id (unikt id för handen)

data_json (JSON-sträng med all handinformation)

Data i JSON-fältet:

"actions": lista eller tabell över samtliga actions i handen

"blinds": dict med sb, bb, och ev. ante

"players": lista med spelare (för att räkna antalet)

Actions: Varje action är ett dict med olika fält, ofta:

"action", "amount", "strength" (eller "j_score"), "pot_before"

Alternativt "Player", "Raw", "stack_before", "stack_after"

Syfte:

Hämta ut alla "bet" och "raise"-actions för en hand och beräkna:

Spelfas ("stage": preflop/flop/turn/river)

Spelare ("player")

Bet-typ ("action")

Storlek ("amount")

Pot före ("pot_before")

Bet/Pot-ratio ("ratio")

Handens styrka ("strength"/"j_score")

Övrigt:

Funktionerna kan lätt återanvändas i andra script.

