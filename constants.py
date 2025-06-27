# --- Konstanten ---
DATA_FILE = 'lernkarten.json'
IMAGE_DIR = 'images'
DEFAULT_COLOR = "#E0E0E0"
PASTEL_COLORS = {
    "Rose": "#FFADAD", "Orange": "#FFD6A5", "Gelb": "#FDFFB6",
    "Grün": "#CAFFBF", "Blau": "#9BF6FF", "Lila": "#BDB2FF"
}

# Farbpaletten für Feedback-Buttons und den Fortschrittsbalken
STATUS_COLORS = {
    "new": "grey",
    "bad": "#E57373",      # Hellrot
    "ok": "#FFD54F",       # Hellgelb
    "good": "#81C784",     # Hellgrün
    "mastered": "#2E7D32", # Dunkelgrün
    "perfect": "#64B5F6"   # Hellblau
}

FEEDBACK_COLORS = {
    "light": {
        "bad": STATUS_COLORS["bad"],
        "ok": STATUS_COLORS["ok"],
        "good": STATUS_COLORS["good"],
        "perfect": STATUS_COLORS["perfect"]
    },
    "dark": {
        "bad": "#C62828",      # Kräftiges Rot
        "ok": "#FF8F00",       # Kräftiges Orange/Gelb
        "good": "#2E7D32",     # Kräftiges Grün
        "perfect": "#1565C0",  # Kräftiges Blau
        "foreground": "#FFFFFF" # Textfarbe für alle dunklen Buttons
    }
}


# --- THEME COLORS ---
THEMES = {
    "light": {
        "bg": "#F0F0F0", "fg": "#000000", "card_bg": "#FFFFFF",
        "header_fg": "#000000", "nav_bg": "#EAEAEA", "button_bg": "#D0D0D0",
        "text_bg": "#FFFFFF", "list_bg": "#FFFFFF", "list_fg": "#000000",
        "danger_bg": "#FF4C4C", "danger_fg": "#FFFFFF",
        "subtask_bg": "#FAFAFA" # Heller Hintergrund für Teilaufgaben
    },
    "dark": {
        "bg": "#2E2E2E", "fg": "#E0E0E0", "card_bg": "#3C3C3C",
        "header_fg": "#FFFFFF", "nav_bg": "#252525", "button_bg": "#555555",
        "text_bg": "#4A4A4A", "list_bg": "#3C3C3C", "list_fg": "#E0E0E0",
        "danger_bg": "#992222", "danger_fg": "#E0E0E0",
        "subtask_bg": "#b28242" # Leicht abgesetzter Hintergrund für Teilaufgaben
    }
}
