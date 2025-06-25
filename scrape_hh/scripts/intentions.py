# intention_classifier.py
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple

# Standardvärden för tillåtna intention-ord per gata
DEFAULT_INTENTIONS_BY_STREET = {
    "preflop": ["steal", "squeeze", "value", "3bet", "4bet", "steal-attempt", "limp-trap"],
    "flop": ["semi-bluff", "thin-value", "merge", "polarised-bluff-or-value", 
             "induce", "classic-value", "max-value", "probe-bet", "trap", "continuation"],
    "turn": ["semi-bluff", "merge", "polarised-bluff-or-value", "induce", 
             "classic-value", "max-value", "value-targeting", "double-barrel"],
    "river": ["bluff-missed-draws", "thin-value", "merge", "polarised-bluff-or-value", 
              "induce", "classic-value", "max-value", "value-targeting", "bluff-catcher", "triple-barrel"]
}

# Standardvärden för handstyrka-mappning till intentioner
DEFAULT_STRENGTH_MAPPINGS = {
    "low": {
        "small": "bluff-missed-draws",
        "medium": "semi-bluff",
        "large": "all-in-bluff"
    },
    "medium": {
        "small": "thin-value",
        "medium": "merge",
        "large": "polarised-bluff-or-value"
    },
    "high": {
        "small": "induce",
        "medium": "classic-value",
        "large": "max-value"
    }
}

class IntentionClassifier:
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialiserar IntentionClassifier med konfiguration.
        
        Args:
            config_file: Sökväg till konfiguration (JSON). Om None används standardvärden.
        """
        self.config = self._load_config(config_file)
        
    def _load_config(self, config_file: Optional[str]) -> Dict:
        """Laddar konfiguration från fil eller använder standardvärden."""
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config
            except Exception as e:
                print(f"Fel vid läsning av konfigurationsfil: {e}")
                
        # Använd standardvärden
        return {
            "intentions_by_street": DEFAULT_INTENTIONS_BY_STREET,
            "strength_mappings": DEFAULT_STRENGTH_MAPPINGS
        }
    
    def _map_strength_to_category(self, strength: int) -> str:
        """
        Mappar numeriskt handstyrka-värde (1-100) till kategori (low/medium/high).
        
        Args:
            strength: Handstyrka (1-100 där 100 är bäst)
            
        Returns:
            Styrkekategori ("low", "medium", "high")
        """
        if strength < 33:
            return "low"
        elif strength < 66:
            return "medium"
        else:
            return "high"
    
    def _map_bet_size_to_category(self, size_category: str) -> str:
        """
        Mappning av betsstorlek till kategori för intention-klassificering.
        
        Args:
            size_category: Betsstorlek kategori (tiny, small, medium, etc.)
            
        Returns:
            Förenklad betsstorlek ("small", "medium", "large")
        """
        size_map = {
            "tiny": "small",
            "small": "small",
            "medium": "medium", 
            "big": "medium",
            "pot": "large",
            "over": "large",
            "huge": "large"
        }
        
        return size_map.get(size_category, "medium")
    
    def get_intention_label(self, strength: int, size_category: str, street: str = "flop") -> str:
        """
        Bestämmer intentionen baserat på handstyrka och betsstorlek.
        
        Args:
            strength: Handstyrka (1-100)
            size_category: Betsstorlekskategori (t.ex. 'small', 'medium', 'big')
            street: Gatan (preflop, flop, turn, river)
            
        Returns:
            Intentionsord (t.ex. 'thin-value', 'semi-bluff')
        """
        # Mappa handstyrka till kategori (low/medium/high)
        strength_category = self._map_strength_to_category(strength)
        
        # Mappa betsstorlek till förenklad storlek (small/medium/large)
        size_simplified = self._map_bet_size_to_category(size_category)
        
        # Hämta mappning från config
        strength_mappings = self.config.get("strength_mappings", DEFAULT_STRENGTH_MAPPINGS)
        
        # Hämta intentionen baserat på styrka och storlek
        intention = strength_mappings.get(strength_category, {}).get(size_simplified, "...")
        
        # Kontrollera att intentionen är tillåten på denna gata
        street_lower = street.lower()
        allowed_intentions = self.config.get("intentions_by_street", {}).get(street_lower, [])
        
        if allowed_intentions and intention not in allowed_intentions:
            # Om intentionen inte är tillåten på denna gata, välj den närmaste
            return "..."
            
        return intention
    
    def build_classification(self, street: str, ip_flag: str, size_cat: str,
                             bet_type: str, action_word: str, intention: str) -> str:
        """
        Bygger den kompletta klassificeringssträngen.
        
        Args:
            street: Gatan (preflop, flop, turn, river)
            ip_flag: "IP" eller "OOP"
            size_cat: Betsstorlekskategori (tiny, small, medium, etc.)
            bet_type: Typ av bet (cbet, raise, etc.)
            action_word: Handlingsord (bet, raise, check-raise, etc.)
            intention: Intentionen (thin-value, semi-bluff, etc.)
            
        Returns:
            Komplett klassificering (t.ex. "flop IP small cbet bet thin-value")
        """
        components = [street, ip_flag, size_cat]
        
        # Lägg bara till bet_type om det inte är tomt
        if bet_type:
            components.append(bet_type)
            
        # Lägg till action_word och intention
        components.append(action_word)
        components.append(intention)
        
        # Bygg den slutliga strängen
        return " ".join(components)
    
    def get_valid_intentions(self, street: str) -> List[str]:
        """Returnerar alla giltiga intentioner för en viss gata."""
        street_lower = street.lower()
        return self.config.get("intentions_by_street", {}).get(street_lower, [])
    
    def get_preflop_specific_intention(self, street: str, action_str: str, position: str, 
                                       strength: int, size_cat: str) -> str:
        """
        Speciell hantering för preflop-intentioner som kan kräva mer kontext.
        
        Args:
            street: Gatan ('preflop')
            action_str: Handlingssträng (t.ex. 'r3500000', 'c', 'f')
            position: Spelarens position (SB, BB, etc.)
            strength: Handstyrka (1-100)
            size_cat: Betsstorlekskategori
            
        Returns:
            Preflop-specifik intention
        """
        if street.lower() != "preflop":
            return self.get_intention_label(strength, size_cat, street)
            
        # Preflop-specifika regler
        if action_str and action_str[0] == "r":
            # För raises, se om det är 3bet eller 4bet situation
            if position in ["BB", "SB"] and size_cat in ["medium", "big"]:
                return "3bet"
            elif position in ["BTN", "CO"] and strength > 70:
                return "value"
            elif position in ["BTN", "CO"] and strength < 40:
                return "steal-attempt"
            elif size_cat in ["big", "pot", "over"]:
                return "4bet"
                
        # Fallback till standard intention
        return self.get_intention_label(strength, size_cat, street)


# Fristående funktion för enkel användning utan att instansiera klassen
def classify_intention(strength: int, size_category: str, street: str = "flop", 
                       ip_flag: str = "IP", bet_type: str = "", 
                       action_word: str = "bet", action_str: str = "", 
                       position: str = "", config_file: Optional[str] = None) -> str:
    """
    Fristående funktion för att klassificera en spelare-intention.
    
    Args:
        strength: Handstyrka (1-100)
        size_category: Betsstorlek (tiny, small, medium, etc.)
        street: Gatan (preflop, flop, turn, river)
        ip_flag: "IP" eller "OOP"
        bet_type: Typ av bet (cbet, raise, etc.)
        action_word: Handlingsord (bet, raise, check-raise, etc.)
        action_str: Rå handlingssträng (t.ex. 'r3500000')
        position: Spelarens position (SB, BB, etc.)
        config_file: Sökväg till konfigurationsfil (optional)
        
    Returns:
        Komplett klassificeringssträng
    """
    classifier = IntentionClassifier(config_file)
    
    # Om det är preflop, använd preflop-specifik intent
    if street.lower() == "preflop" and position:
        intention = classifier.get_preflop_specific_intention(
            street, action_str, position, strength, size_category
        )
    else:
        intention = classifier.get_intention_label(strength, size_category, street)
    
    # Bygg den kompletta klassificeringen
    return classifier.build_classification(
        street, ip_flag, size_category, bet_type, action_word, intention
    )


if __name__ == "__main__":
    # Exempel på användning
    
    # Skapa en klassificerare
    classifier = IntentionClassifier()
    
    # Exempel på flop-scenarier
    print("=== Flop intentioner ===")
    flop_examples = [
        (25, "small", "flop", "IP", "cbet", "bet", "", ""),  # Svag hand, litet bet
        (50, "medium", "flop", "IP", "cbet", "bet", "", ""), # Medel hand, medium bet
        (85, "big", "flop", "OOP", "lead", "bet", "", ""),   # Stark hand, stort bet
        (30, "pot", "flop", "OOP", "donk", "bet", "", "")    # Svag hand, pot bet
    ]
    
    for strength, size, street, ip, bet_type, action_word, action_str, position in flop_examples:
        classification = classify_intention(
            strength, size, street, ip, bet_type, action_word, action_str, position
        )
        print(f"Handstyrka: {strength}, Storlek: {size} → {classification}")
    
    # Exempel på preflop-scenarier
    print("\n=== Preflop intentioner ===")
    preflop_examples = [
        (90, "big", "preflop", "IP", "", "raise", "r3500000", "BTN"),  # AA från BTN
        (40, "medium", "preflop", "IP", "", "raise", "r2500000", "CO"), # Medel hand från CO
        (75, "over", "preflop", "OOP", "3bet", "raise", "r8000000", "BB"), # Bra hand 3bet från BB
        (20, "small", "preflop", "IP", "", "raise", "r2000000", "BTN")  # Svag hand steal från BTN
    ]
    
    for strength, size, street, ip, bet_type, action_word, action_str, position in preflop_examples:
        classification = classify_intention(
            strength, size, street, ip, bet_type, action_word, action_str, position
        )
        print(f"Handstyrka: {strength}, Storlek: {size}, Position: {position} → {classification}")
    
    # Visa giltiga intentioner per gata
    print("\n=== Giltiga intentioner per gata ===")
    for street in ["preflop", "flop", "turn", "river"]:
        valid_intents = classifier.get_valid_intentions(street)
        print(f"{street}: {', '.join(valid_intents)}")