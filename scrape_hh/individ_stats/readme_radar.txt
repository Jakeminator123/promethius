Readme / Databasöversikt
Tabeller och kolumner:

Tabell: player_intention

player_id (str): spelarens id

intention (str): namn på intention

n_actions (int): antal gånger denna intention har förekommit

street (str): gata ("PREFLOP", "FLOP", "TURN", "RIVER")

Textfil: intentions.txt

Format:

python-repl
Copy
Edit
Intentionnamn1   Värde1
Intentionnamn2   Värde2
...
(Första raden är header)

Syfte:

Visualisera och jämföra hur ofta olika intentioner används av en spelare (och deras "värde" om intentions.txt finns).

Intentionernas poäng används för att färgkoda/ordna axlar.