#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Grafiskt gränssnitt för att redigera JSON-filer med intention-mappningar
i different_actions-mapparna.
"""
import json
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, font
from tkinter.colorchooser import askcolor

# Konstanter för utseendet
BG_COLOR = "#f6f2ff"  # soft lilac background
HEADER_BG = "#2c3e50"
HEADER_FG = "white"
CELL_BG_LOW = "#ff9999"       # Rödare för låg handstyrka
CELL_BG_MEDIUM = "#ffffaa"    # Gult för medium
CELL_BG_HIGH = "#99ff99"      # Grönare för hög handstyrka
BUTTON_BG = "#3498db"
BUTTON_FG = "white"

# Bettstorlekar
SIZE_CATEGORIES = ["tiny", "small", "medium", "big", "pot", "over", "huge"]
SIZE_DISPLAY_NAMES = {
    "tiny": "TINY (<20%)",
    "small": "SMALL (20-35%)",
    "medium": "MEDIUM (35-55%)",
    "big": "BIG (55-85%)",
    "pot": "POT (85-110%)",
    "over": "OVER (110-175%)",
    "huge": "HUGE (>175%)"
}

# Standardvärden för betsstorlekar
DEFAULT_SIZING_RANGES = {
    "tiny":   [0.00, 0.20],
    "small":  [0.20, 0.35],
    "medium": [0.35, 0.55],
    "big":    [0.55, 0.85],
    "pot":    [0.85, 1.10],
    "over":   [1.10, 1.75],
    "huge":   [1.75, 999.00]
}

# Mappning mellan detaljerade kategorier och de tre huvudgrupperna
SIZE_GROUP_MAPPING = {
    "tiny": "small", 
    "small": "small",
    "medium": "medium",
    "big": "large", 
    "pot": "large", 
    "over": "large", 
    "huge": "large"
}

class IntentionEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Intention Editor")
        self.geometry("1400x800")  # Större fönster för den sammansatta layouten
        self.configure(bg=BG_COLOR)
        
        # Lägg till styling för enhetlig design av widgets
        style = ttk.Style(self)
        style.theme_use('clam')
        # Bakgrund för ramar och etiketter
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR, font=("Helvetica", 12))
        # LabelFrame bakgrund och etikett
        style.configure("TLabelframe", background=BG_COLOR)
        style.configure("TLabelframe.Label", background=BG_COLOR, font=("Helvetica", 12, "bold"))
        # Notebook-flikar
        style.configure("TNotebook.Tab", font=("Helvetica", 12, "bold"), padding=(10, 5))
        # Knappar
        style.configure("TButton", font=("Helvetica", 12), padding=5)
        # Komboboxar
        style.configure("TCombobox", font=("Helvetica", 12), padding=5)
        # Stil för legend-etiketterna
        style.configure("Legend.TLabel", background=BG_COLOR, font=("Helvetica", 10), foreground="#4b0082")
        
        # Sökvägar
        self.base_dir = Path(__file__).parent
        
        # Data för aktuell fil
        self.current_file = None
        self.json_data = None
        
        # Mappning från combo-boxar till JSON-sökvägar
        self.combo_to_json_path = {}
        
        # Förklaring av vad som händer
        explanation = """
        Denna editor låter dig ändra vilken 'intention' som tilldelas när en spelare gör en viss åtgärd.
        
        1. Välj gata (pre, flop, turn, river) och actions-typ (bet, call, etc.)
        2. Matrisen visar handstyrka (låg-medel-hög) vs. satsningsstorlek (liten-mellan-stor)
        3. Ändra intentionstaggarna i varje cell och spara ändringarna
        """
        
        # Skapa UI
        self.setup_ui()
        
        # Ladda JSON-filerna
        self.load_json_files()

    def setup_ui(self):
        # Skapa en huvudram för allt innehåll
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Titelrubrik
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(
            title_frame, 
            text="POKER INTENTIONS EDITOR", 
            font=font.Font(family="Helvetica", size=18, weight="bold")
        )
        title_label.pack()
        
        # Väljare för JSON-filer
        selector_frame = ttk.LabelFrame(main_frame, text="Select configuration file", padding=10)
        selector_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Street-väljare (pre, flop, turn, river)
        street_frame = ttk.Frame(selector_frame)
        street_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(street_frame, text="Street:", width=10).pack(side=tk.LEFT)
        self.street_combo = ttk.Combobox(street_frame, values=["pre", "flop", "turn", "river"], state="readonly", width=15, style="TCombobox")
        self.street_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.street_combo.bind("<<ComboboxSelected>>", self.on_street_change)
        
        # Action-väljare (bet, call, etc.)
        action_frame = ttk.Frame(selector_frame)
        action_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(action_frame, text="Action:", width=10).pack(side=tk.LEFT)
        self.action_combo = ttk.Combobox(action_frame, state="readonly", width=15, style="TCombobox")
        self.action_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.action_combo.bind("<<ComboboxSelected>>", self.on_action_change)
        
        # Skapa en paned window för att dela skärmen i två delar
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Vänstra panelen för bettstorlekar
        bet_sizes_frame = ttk.LabelFrame(paned, text="Bet Sizes and Groupings", padding=10)
        paned.add(bet_sizes_frame, weight=1)
        
        # Headers för bettstorlekar
        headers_frame = ttk.Frame(bet_sizes_frame)
        headers_frame.pack(fill=tk.X, pady=(0, 10))
        
        headers = ["Key", "Display name", "Group", "Min % pot", "Max % pot"]
        for col, text in enumerate(headers):
            ttk.Label(headers_frame, text=text,
                     background=HEADER_BG, foreground=HEADER_FG,
                     padding=5).grid(row=0, column=col, padx=2, sticky="ew")
        # Gör kolumnerna skalbara för rubriker
        for col in range(len(headers)):
            headers_frame.columnconfigure(col, weight=1)
        
        self.size_rows = {}
        container = ttk.Frame(bet_sizes_frame)
        container.pack(fill=tk.BOTH, expand=True)
        # Gör kolumnerna skalbara för fälten
        for col in range(len(headers)):
            container.columnconfigure(col, weight=1)
        
        for i, size in enumerate(SIZE_CATEGORIES):
            ttk.Label(container, text=size, padding=5).grid(row=i, column=0, padx=2, sticky="w")

            display_entry = ttk.Entry(container, width=18, style="TEntry")
            display_entry.insert(0, SIZE_DISPLAY_NAMES.get(size, ""))
            display_entry.grid(row=i, column=1, padx=2, sticky="ew")

            group_combo = ttk.Combobox(container, values=["small","medium","large"],
                                      width=18, style="TCombobox")
            group_combo.set(SIZE_GROUP_MAPPING.get(size, ""))
            group_combo.grid(row=i, column=2, padx=2, sticky="ew")

            min_entry = ttk.Entry(container, width=18, style="TEntry")
            min_entry.grid(row=i, column=3, padx=2, sticky="ew")
            max_entry = ttk.Entry(container, width=18, style="TEntry")
            max_entry.grid(row=i, column=4, padx=2, sticky="ew")

            self.size_rows[size] = (display_entry, group_combo, min_entry, max_entry)
        
        # Knappar för att spara/återställa bettstorlekar
        bet_button_frame = ttk.Frame(bet_sizes_frame)
        bet_button_frame.pack(fill=tk.X, pady=10)
        
        save_bet_button = ttk.Button(
            bet_button_frame, 
            text="SAVE BET SIZES", 
            command=self.save_sizing_changes,
            style="Save.TButton",
            padding=5
        )
        save_bet_button.pack(side=tk.RIGHT, padx=5)
        
        reset_sizing_button = ttk.Button(
            bet_button_frame, 
            text="RESET SIZES", 
            command=self.reset_sizing_defaults,
            padding=5
        )
        reset_sizing_button.pack(side=tk.RIGHT, padx=5)
        
        # Högra sidan med intention-matrisen
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)  # Ge den högra sidan mer vikt
        
        # Legend showing size→group mapping
        legend_frame = ttk.Frame(right_frame)
        legend_frame.pack(fill=tk.X, pady=(0, 10))
        
        legend_text = (
            "Groups:  Small: tiny, small   |   "
            "Medium: medium   |   Large: big, pot, over, huge"
        )
        ttk.Label(
            legend_frame,
            text=legend_text,
            style="Legend.TLabel"
        ).pack()
        
        # Matrisram för intention-mappning med scrollbar
        matrix_outer_frame = ttk.Frame(right_frame)
        matrix_outer_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Scrollbar
        h_scrollbar = ttk.Scrollbar(matrix_outer_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Canvas för scrolling
        canvas = tk.Canvas(matrix_outer_frame, bg=BG_COLOR)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.configure(xscrollcommand=h_scrollbar.set)
        h_scrollbar.configure(command=canvas.xview)
        
        # Frame inom canvas för matrisinnehåll
        matrix_frame = ttk.LabelFrame(canvas, text="Intention Matrix (7 bet sizes × 3 hand-strength levels)", padding=10)
        canvas.create_window((0, 0), window=matrix_frame, anchor=tk.NW)
        
        # Skapa matrixhuvud
        header_frame = ttk.Frame(matrix_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Tomma utrymme
        ttk.Label(header_frame, text="", width=12).grid(row=0, column=0)
        
        # Vi sparar header-etiketter för att kunna uppdatera dem
        self.size_header_labels = {}
        
        # Storleksrubriker - nu 7 stycken
        for i, size in enumerate(SIZE_CATEGORIES):
            label = ttk.Label(
                header_frame, 
                text=SIZE_DISPLAY_NAMES[size], 
                background=HEADER_BG, 
                foreground=HEADER_FG,
                padding=5,
                anchor=tk.CENTER,
                width=15
            )
            label.grid(row=0, column=i+1, sticky="ew", padx=2)
            self.size_header_labels[size] = label
        
        # Skapa cellmatrisen - nu med 7 kolumner
        self.matrix_frame = ttk.Frame(matrix_frame)
        self.matrix_frame.pack(fill=tk.BOTH, expand=True)
        
        # Styrkerubriker och komboceller
        self.combos = {}
        bg_colors = {
            "low": CELL_BG_LOW,
            "medium": CELL_BG_MEDIUM,
            "high": CELL_BG_HIGH
        }
        
        strength_labels = {
            "low": "LOW STRENGTH\n(0-24)",
            "medium": "MEDIUM STRENGTH\n(25-74)",
            "high": "HIGH STRENGTH\n(75-100)"
        }
        
        for row, strength in enumerate(["low", "medium", "high"]):
            # Styrkerubrik
            strength_label = ttk.Label(
                self.matrix_frame, 
                text=strength_labels[strength],
                background=bg_colors[strength],
                padding=5,
                anchor=tk.CENTER,
                width=15
            )
            strength_label.grid(row=row, column=0, sticky="nsew", padx=2, pady=2)
            
            # Intentioner för varje storlekskategori - nu alla 7
            for col, size in enumerate(SIZE_CATEGORIES):
                frame = ttk.Frame(self.matrix_frame, padding=5)
                frame.grid(row=row, column=col+1, sticky="nsew", padx=2, pady=2)
                frame.configure(style=f"{strength}.TFrame")
                
                # Skapa stil för bakgrundsfärg
                style_name = f"{strength}.TFrame"
                style = ttk.Style()
                style.configure(style_name, background=bg_colors[strength])
                
                # Ändra här: sätt state till normal (redigerbart, inte readonly)
                combo = ttk.Combobox(frame, width=15, state="normal", style="TCombobox")
                combo.pack(fill=tk.BOTH, expand=True)
                
                # Bind Enter-tangenten för att lägga till nya intentioner globalt
                combo.bind("<Return>", self.on_new_intention_entered)
                
                # Spara komboboxen för senare åtkomst
                self.combos[(strength, size)] = combo
                
                # Koppla JSON-path till den detaljerade JSON-strukturen
                key_path = ["detailed_mappings", strength, size]
                self.combo_to_json_path[combo] = key_path
        
        # Tillåt att cellerna utvidgas
        for i in range(8):  # 0 + 7 kolumner
            self.matrix_frame.columnconfigure(i, weight=1)
        for i in range(3):  # 3 rader
            self.matrix_frame.rowconfigure(i, weight=1)
            
        # Konfigurera canvas för scrolling
        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.configure(width=event.width, height=event.height)
            # Ställ in minsta bredd baserat på innehållet
            matrix_width = matrix_frame.winfo_reqwidth()
            canvas.itemconfigure(1, width=max(matrix_width, event.width))
            
        matrix_frame.bind("<Configure>", on_configure)
        
        # Förhandsgranskning och knappar
        preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding=10)
        preview_frame.pack(fill=tk.X, pady=(10, 10))
        
        self.preview_label = ttk.Label(
            preview_frame, 
            text="Select a street and action to see preview",
            font=font.Font(family="Helvetica", size=12),
            padding=10
        )
        self.preview_label.pack(fill=tk.X)
        
        # Knappar
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Custom style för knappar
        style = ttk.Style()
        style.configure("Save.TButton", background=BUTTON_BG, foreground=BUTTON_FG)
        
        # Lägg till en återställ-allt-knapp
        reset_all_button = ttk.Button(
            button_frame, 
            text="RESET ALL VALUES", 
            command=self.reset_all_to_defaults,
            padding=10
        )
        reset_all_button.pack(side=tk.LEFT, padx=5)
        
        save_button = ttk.Button(
            button_frame, 
            text="SAVE CHANGES", 
            command=self.save_changes,
            style="Save.TButton",
            padding=10
        )
        save_button.pack(side=tk.RIGHT, padx=5)
        
        load_button = ttk.Button(
            button_frame, 
            text="RELOAD FILE", 
            command=self.load_current_file,
            padding=10
        )
        load_button.pack(side=tk.RIGHT, padx=5)

    def load_json_files(self):
        """Läser in tillgängliga gatumappar och JSON-filer"""
        if self.street_combo.get():
            return  # Om redan vald, behåll valet
            
        streets = []
        for street in ["pre", "flop", "turn", "river"]:
            if (self.base_dir / street).exists():
                streets.append(street)
        
        if streets:
            self.street_combo["values"] = streets
            self.street_combo.current(0)
            self.on_street_change()
        else:
            messagebox.showerror("Fel", "Inga gator hittades i different_actions-katalogen!")

    def on_street_change(self, event=None):
        """När användaren väljer en annan gata"""
        street = self.street_combo.get()
        if not street:
            return
            
        # Hitta alla JSON-filer i denna gata
        street_dir = self.base_dir / street
        json_files = [f.stem for f in street_dir.glob("*.json")]
        
        self.action_combo["values"] = json_files
        if json_files:
            self.action_combo.current(0)
            self.on_action_change()
        else:
            self.action_combo.set("")
            messagebox.showinfo("Info", f"Inga JSON-filer hittades för {street}")

    def on_action_change(self, event=None):
        """När användaren väljer en annan action-fil"""
        street = self.street_combo.get()
        action = self.action_combo.get()
        
        if not street or not action:
            return
            
        # Konstruera filsökväg
        self.current_file = self.base_dir / street / f"{action}.json"
        
        # Läs in filen
        self.load_current_file()

    def load_current_file(self):
        """Läser in aktuell JSON-fil och uppdaterar gränssnittet"""
        if not self.current_file or not self.current_file.exists():
            return
            
        try:
            with open(self.current_file, "r", encoding="utf-8") as f:
                self.json_data = json.load(f)
                
            # Lägg till "detailed_mappings" om det saknas
            if "detailed_mappings" not in self.json_data:
                # Skapa detailed_mappings struktur om den saknas
                self.json_data["detailed_mappings"] = {
                    "low": {},
                    "medium": {},
                    "high": {}
                }

            # Lägg till "size_display_names" om det saknas
            if "size_display_names" not in self.json_data:
                self.json_data["size_display_names"] = SIZE_DISPLAY_NAMES.copy()

            # Lägg till "size_group_mapping" om det saknas
            if "size_group_mapping" not in self.json_data:
                self.json_data["size_group_mapping"] = SIZE_GROUP_MAPPING.copy()

            # Lägg till "sizing_ranges" om det saknas
            if "sizing_ranges" not in self.json_data:
                self.json_data["sizing_ranges"] = DEFAULT_SIZING_RANGES.copy()

            # Hitta möjliga intentioner från alla filer för auto-complete
            all_intentions = self.get_all_intentions()
            self.all_intentions = list(all_intentions)  # spara
            for combo in self.combos.values():
                combo["values"] = self.all_intentions
                
            # Konvertera om filen använder gamla strength_mappings-formatet till detailed_mappings
            if "strength_mappings" in self.json_data and not any(self.json_data["detailed_mappings"].values()):
                self.convert_mappings_to_detailed()
            
            # Fyll i kombinationerna från JSON-data
            for combo, key_path in self.combo_to_json_path.items():
                # Navigera djupt
                value = self.json_data
                for key in key_path:
                    if key in value:
                        value = value[key]
                    else:
                        value = ""
                        break
                combo.set(value if value else "")
            
            # Ladda sizing ranges
            self.load_sizing_entries()
            
            # Ladda display names och grupper om de finns
            self.load_size_names()
                
            self.update_preview()
                
        except Exception as e:
            messagebox.showerror("Fel", f"Kunde inte läsa {self.current_file.name}: {e}")

    def convert_mappings_to_detailed(self):
        """Konverterar traditionell strength_mappings (3x3) till detailed_mappings (3x7)"""
        if "strength_mappings" not in self.json_data:
            return
            
        # Skapa detailed_mappings struktur om den saknas
        if "detailed_mappings" not in self.json_data:
            self.json_data["detailed_mappings"] = {
                "low": {},
                "medium": {},
                "high": {}
            }
            
        # För varje styrkenivå (low, medium, high)
        for strength in ["low", "medium", "high"]:
            # Om denna styrkenivå finns i strength_mappings
            if strength in self.json_data["strength_mappings"]:
                # För varje storlek (small, medium, large)
                for group, intention in self.json_data["strength_mappings"][strength].items():
                    # Mappa gruppen till alla relaterade detaljerade storlekar
                    for size, mapped_group in SIZE_GROUP_MAPPING.items():
                        if mapped_group == group:
                            self.json_data["detailed_mappings"][strength][size] = intention

    def load_sizing_entries(self):
        """Laddar bettstorlekar från JSON-data"""
        if not self.json_data:
            return
            
        # Hämta sizing ranges från JSON eller använd default
        sizing_ranges = self.json_data.get("sizing_ranges", DEFAULT_SIZING_RANGES)
        
        # Uppdatera entries
        for size, (display_entry, group_combo, min_entry, max_entry) in self.size_rows.items():
            if size in sizing_ranges:
                min_val, max_val = sizing_ranges[size]
                min_entry.delete(0, tk.END)
                min_entry.insert(0, str(min_val))
                max_entry.delete(0, tk.END)
                max_entry.insert(0, str(max_val))

    def load_size_names(self):
        """Laddar display names och grupper från JSON-data"""
        if not self.json_data:
            return
        
        # Hämta data från JSON eller använd standardvärden
        display_names = self.json_data.get("size_display_names", SIZE_DISPLAY_NAMES)
        group_mapping = self.json_data.get("size_group_mapping", SIZE_GROUP_MAPPING)
        
        # Uppdatera visningsnamn och grupp för varje storlek
        for size, (display_entry, group_combo, min_entry, max_entry) in self.size_rows.items():
            display_entry.delete(0, tk.END)
            display_entry.insert(0, display_names.get(size, SIZE_DISPLAY_NAMES.get(size, "")))
            group_combo.set(group_mapping.get(size, SIZE_GROUP_MAPPING.get(size, "")))
        
        # Uppdatera rubrikerna i intention-matrisen
        self.update_size_headers(display_names)

    def reset_sizing_defaults(self):
        """Återställer bettstorlekar till standardvärden"""
        if not self.current_file:
            return
        
        # Återställ bettstorlekar till standardvärden
        for size, (_, _, min_entry, max_entry) in self.size_rows.items():
            min_val, max_val = DEFAULT_SIZING_RANGES[size]
            min_entry.delete(0, tk.END)
            min_entry.insert(0, str(min_val))
            max_entry.delete(0, tk.END)
            max_entry.insert(0, str(max_val))
        
        # Återställ visningsnamn och grupperingar
        for size, (display_entry, group_combo, _, _) in self.size_rows.items():
            display_entry.delete(0, tk.END)
            display_entry.insert(0, SIZE_DISPLAY_NAMES.get(size, ""))
            group_combo.set(SIZE_GROUP_MAPPING.get(size, ""))
        
        messagebox.showinfo("Reset", "Bet sizes and display names reset to default values")

    def reset_all_to_defaults(self):
        """Återställer alla värden till standardinställningar"""
        if not self.current_file:
            return
            
        confirm = messagebox.askyesno("Confirm Reset", "Are you sure you want to reset ALL values to defaults? This will affect both bet sizes and all intention assignments.")
        if not confirm:
            return
        
        # Återställ bettstorlekarna
        self.reset_sizing_defaults()
        
        # Skapa standard-mappning för intentioner
        default_intentions = {
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
        
        # Konvertera till detailed mapping
        detailed_intentions = {
            "low": {},
            "medium": {},
            "high": {}
        }
        
        # Fyll i från default_intentions baserat på grupper
        for strength in ["low", "medium", "high"]:
            for size in SIZE_CATEGORIES:
                group = SIZE_GROUP_MAPPING[size]
                detailed_intentions[strength][size] = default_intentions[strength][group]
        
        # Uppdatera intentions i UI
        for (strength, size), combo in self.combos.items():
            value = detailed_intentions[strength][size]
            combo.set(value)
        
        # Uppdatera JSON-data också
        if "detailed_mappings" not in self.json_data:
            self.json_data["detailed_mappings"] = {}
        self.json_data["detailed_mappings"] = detailed_intentions
        
        # Uppdatera preview
        self.update_preview()
        
        messagebox.showinfo("Reset Complete", "All values have been reset to defaults")

    def update_size_headers(self, display_names):
        """Uppdaterar rubrikerna i intention-matrisen"""
        for size, label in self.size_header_labels.items():
            label.configure(text=display_names.get(size, SIZE_DISPLAY_NAMES.get(size, "")))

    def get_all_intentions(self):
        """Samlar alla unika intentions-strängar från alla JSON-filer"""
        intentions = set()
        
        for street_dir in self.base_dir.iterdir():
            if street_dir.is_dir():
                for json_file in street_dir.glob("*.json"):
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            
                            # Kolla båda formaten för att samla intentioner
                            for mapping_key in ["strength_mappings", "detailed_mappings"]:
                                if mapping_key in data:
                                    strength_map = data[mapping_key]
                                    for strength in strength_map.values():
                                        for intention in strength.values():
                                            if intention:
                                                intentions.add(intention)
                    except:
                        pass
                        
        return sorted(list(intentions))

    def update_preview(self):
        """Uppdaterar förhandsgranskningen"""
        if not self.current_file:
            return
            
        street = self.street_combo.get()
        action = self.action_combo.get()
        
        # Hämta display names från JSON eller använd standard
        display_names = self.json_data.get("size_display_names", SIZE_DISPLAY_NAMES)
        
        # Formatera en mening
        preview = f"For {street}, action '{action}' will use these intentions:\n\n"
        
        # Visa alla 21 kombinationer i förhandsgranskningen
        for strength, label in [("low", "Låg handstyrka"), 
                                ("medium", "Medel handstyrka"), 
                                ("high", "Hög handstyrka")]:
            preview += f"\n{strength.upper()} STRENGTH:\n"
            for size in SIZE_CATEGORIES:
                combo = self.combos.get((strength, size))
                if combo:
                    intention = combo.get()
                    if intention:
                        preview += f"• {display_names.get(size, SIZE_DISPLAY_NAMES[size])}: {intention}\n"
        
        self.preview_label.configure(text=preview)

    def save_sizing_changes(self):
        """Sparar ändringar till bettstorlekar"""
        # Kombinera allt till save_changes istället
        self.save_changes(save_sizing=True)

    def save_changes(self, save_sizing=False):
        """Sparar alla ändringar till JSON-filen (intentions, bettstorlekar, och grupperingar)"""
        if not self.current_file or not self.json_data:
            return
        
        # 1. Samla ihop intentioner från matrisen
        for combo, key_path in self.combo_to_json_path.items():
            value = combo.get()
            
            # Navigera till rätt plats och uppdatera
            target = self.json_data
            for i, key in enumerate(key_path):
                if i == len(key_path) - 1:
                    target[key] = value
                else:
                    if key not in target:
                        target[key] = {}
                    target = target[key]
                    
        # 2. Samla ihop bettstorlekar
        sizing_ranges = {}
        for size, (display_entry, group_combo, min_entry, max_entry) in self.size_rows.items():
            try:
                min_val = float(min_entry.get())
                max_val = float(max_entry.get())
                sizing_ranges[size] = [min_val, max_val]
            except ValueError:
                messagebox.showerror("Fel", f"Ogiltigt tal för {size}. Använd decimaltal (t.ex. 0.55)")
                return
            
        # 3. Samla ihop visningsnamn
        display_names = {}
        group_mapping = {}
        for size, (display_entry, group_combo, min_entry, max_entry) in self.size_rows.items():
            display_names[size] = display_entry.get()
            group_mapping[size] = group_combo.get()
            
        # Uppdatera JSON-data
        self.json_data["sizing_ranges"] = sizing_ranges
        self.json_data["size_display_names"] = display_names
        self.json_data["size_group_mapping"] = group_mapping

        # Uppdatera även strength_mappings för bakåtkompatibilitet
        self.update_strength_mappings_from_detailed()
        
        # Uppdatera rubrikerna i intention-matrisen
        self.update_size_headers(display_names)
        
        self.save_to_file()

    def update_strength_mappings_from_detailed(self):
        """Uppdaterar strength_mappings baserat på detailed_mappings för bakåtkompatibilitet"""
        if "detailed_mappings" not in self.json_data:
            return
            
        # Skapa/rensa strength_mappings
        if "strength_mappings" not in self.json_data:
            self.json_data["strength_mappings"] = {}
            
        for strength in ["low", "medium", "high"]:
            if strength not in self.json_data["strength_mappings"]:
                self.json_data["strength_mappings"][strength] = {}
                
            # Rensa existerande värden
            self.json_data["strength_mappings"][strength] = {
                "small": "",
                "medium": "",
                "large": ""
            }
            
            # För varje storlek i detailed_mappings
            if strength in self.json_data["detailed_mappings"]:
                # Samla intentioner per grupp
                group_intentions = {
                    "small": set(),
                    "medium": set(),
                    "large": set()
                }
                
                # Hämta uppdaterad gruppmappning från size_rows
                group_mapping = {}
                for size, (_, group_combo, _, _) in self.size_rows.items():
                    group = group_combo.get()
                    if group:
                        group_mapping[size] = group
                
                # Använd uppdaterad gruppmappning när vi skapar strength_mappings
                for size, intention in self.json_data["detailed_mappings"][strength].items():
                    if intention and size in group_mapping:
                        group = group_mapping[size]
                        group_intentions[group].add(intention)
                
                # Sätt den vanligaste intentionen för varje grupp
                for group, intentions in group_intentions.items():
                    if intentions:
                        # Välj en intention (första i alfabetisk ordning för konsistens)
                        self.json_data["strength_mappings"][strength][group] = sorted(list(intentions))[0]

    def save_to_file(self):
        """Gemensam funktion för att spara till fil"""
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                json.dump(self.json_data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Saved", f"Changes saved to {self.current_file.name}")
            self.update_preview()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save {self.current_file.name}: {e}")

    def on_new_intention_entered(self, event):
        """När användaren trycker Enter i en combobox läggs intentionen till i alla listor"""
        widget = event.widget
        new_val = widget.get().strip()
        if not new_val:
            return
        # Håll en egen lista över alla intentioner
        if not hasattr(self, "all_intentions"):
            self.all_intentions = []
        if new_val not in self.all_intentions:
            self.all_intentions.append(new_val)
            # Uppdatera values för alla comboboxar
            for combo in self.combos.values():
                combo["values"] = tuple(sorted(self.all_intentions))
        # Se till att current widget behåller sitt värde
        widget.setvar(widget.cget("textvariable"), new_val)

if __name__ == "__main__":
    app = IntentionEditor()
    app.mainloop() 