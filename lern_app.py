import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
import json
import random
import time
import os
import uuid
from PIL import Image, ImageTk
from datetime import datetime
import io
import re
from collections import deque

# --- Imports für LaTeX und Plots ---
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

# --- Konstanten ---
DATA_FILE = 'lernkarten.json'
IMAGE_DIR = 'images'
DEFAULT_COLOR = "#E0E0E0"
PASTEL_COLORS = {
    "Rose": "#FFADAD", "Orange": "#FFD6A5", "Gelb": "#FDFFB6",
    "Grün": "#CAFFBF", "Blau": "#9BF6FF", "Lila": "#BDB2FF"
}

# --- THEME COLORS ---
THEMES = {
    "light": {
        "bg": "#F0F0F0", "fg": "#000000", "card_bg": "#FFFFFF",
        "header_fg": "#000000", "nav_bg": "#EAEAEA", "button_bg": "#D0D0D0",
        "text_bg": "#FFFFFF", "list_bg": "#FFFFFF", "list_fg": "#000000",
        "danger_bg": "#FF4C4C", "danger_fg": "#FFFFFF"
    },
    "dark": {
        "bg": "#2E2E2E", "fg": "#FFFFFF", "card_bg": "#3C3C3C",
        "header_fg": "#FFFFFF", "nav_bg": "#252525", "button_bg": "#505050",
        "text_bg": "#4A4A4A", "list_bg": "#3C3C3C", "list_fg": "#FFFFFF",
        "danger_bg": "#B30000", "danger_fg": "#FFFFFF"
    }
}


# --- HELFERFUNKTIONEN ---
def render_latex(formula, fontsize=12, dpi=300, fg='black', bg='white'):
    """Rendert eine LaTeX-Formel in ein Pillow-Bildobjekt."""
    try:
        # Ersetzungen für eine bessere Kompatibilität
        formula = formula.replace('\\le', '\\leq').replace('\\ge', '\\geq').replace('\\implies', '\\Rightarrow').replace('\\text', '\\mathrm')
        fig = Figure(figsize=(4, 1), dpi=dpi, facecolor=bg)
        # usetex=False, da es eine vollständige LaTeX-Installation erfordert
        fig.text(0, 0, f"${formula}$", usetex=False, fontsize=fontsize, color=fg)

        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=False, bbox_inches='tight', pad_inches=0.05, facecolor=bg)
        plt.close(fig) # Wichtig: Schließt die Figur, um Speicherlecks zu vermeiden
        buf.seek(0)
        img = Image.open(buf)
        return img
    except Exception as e:
        print(f"Fehler beim Rendern von LaTeX: {formula}\n{e}")
        return None

def get_readable_text_color(hex_bg_color):
    """Wählt Schwarz oder Weiß als Textfarbe für beste Lesbarkeit basierend auf der Luminanz der Hintergrundfarbe."""
    if not hex_bg_color or not hex_bg_color.startswith('#'):
        return "#000000"
    hex_bg_color = hex_bg_color[1:]
    try:
        r, g, b = (int(hex_bg_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#000000" if luminance > 0.5 else "#FFFFFF"
    except (ValueError, IndexError):
        return "#000000"

def bind_mouse_scroll(widget_to_bind, canvas_to_scroll):
    """Bindet das Mausrad-Event zuverlässig an ein Widget und alle seine Kinder, um einen bestimmten Canvas zu scrollen."""
    def _on_mousewheel(event):
        # Passt die Scroll-Geschwindigkeit und -Richtung für verschiedene Plattformen an
        if event.num == 5 or event.delta < 0:
            canvas_to_scroll.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            canvas_to_scroll.yview_scroll(-1, "units")

    # Bindet das Mausrad-Event (Windows, macOS) und die Tasten-Events (Linux)
    widget_to_bind.bind("<MouseWheel>", _on_mousewheel)
    widget_to_bind.bind("<Button-4>", _on_mousewheel)
    widget_to_bind.bind("<Button-5>", _on_mousewheel)

    # Rekursiv für alle Kind-Widgets binden
    for child in widget_to_bind.winfo_children():
        bind_mouse_scroll(child, canvas_to_scroll)

# --- DATENVERWALTUNG ---
class DataManager:
    """Verwaltet das Laden und Speichern der JSON-Daten sowie das Kopieren von Bildern."""
    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(IMAGE_DIR):
            os.makedirs(IMAGE_DIR)

    def load_data(self):
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_data(self, data):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def copy_image_to_datastore(self, image_path):
        if not image_path or not os.path.exists(image_path):
            return None
        # Verhindert das erneute Kopieren, wenn das Bild bereits im Datenspeicher ist
        if os.path.dirname(os.path.abspath(image_path)) == os.path.abspath(IMAGE_DIR):
            return image_path

        filename = os.path.basename(image_path)
        # Erzeugt einen einzigartigen Dateinamen, um Überschreibungen zu vermeiden
        unique_filename = f"{int(time.time())}_{random.randint(100,999)}_{filename}"
        destination_path = os.path.join(IMAGE_DIR, unique_filename)
        try:
            import shutil
            shutil.copy(image_path, destination_path)
            return destination_path
        except Exception as e:
            print(f"Fehler beim Kopieren des Bildes: {e}")
            return None

# --- HAUPTANWENDUNG ---
class LernApp(tk.Tk):
    """Hauptklasse der Anwendung. Verwaltet Frames, Daten und das Theme."""
    def __init__(self):
        super().__init__()
        self.title("Lern-Anwendung")
        self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.data_manager = DataManager(DATA_FILE)
        self.data = self.data_manager.load_data()

        # Lädt das gespeicherte Theme oder verwendet "light" als Standard
        saved_theme = self.data.get("settings", {}).get("theme", "light")
        self.current_theme = tk.StringVar(value=saved_theme)
        self.current_theme.trace_add("write", self.apply_theme)

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.apply_theme()
        self.show_frame(StartFrame)

    def apply_theme(self, *args):
        """Wendet das ausgewählte Farbschema (Theme) auf die gesamte Anwendung an."""
        theme_name = self.current_theme.get()
        colors = THEMES[theme_name]

        self.style = ttk.Style(self)
        self.style.theme_use('clam')

        self.configure(bg=colors["bg"])
        self.style.configure(".", background=colors["bg"], foreground=colors["fg"], fieldbackground=colors["text_bg"])
        self.style.configure("TFrame", background=colors["bg"])
        self.style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("TButton", padding=6, relief="flat", background=colors["button_bg"], foreground=colors["fg"])
        self.style.map("TButton", background=[("active", colors["fg"])], foreground=[("active", colors["bg"])])

        # BUGFIX: Stil für ttk.Entry-Widgets, um die Cursorfarbe zu setzen.
        self.style.configure("TEntry", fieldbackground=colors["text_bg"], insertcolor=colors["fg"], foreground=colors["fg"])

        # Spezieller Stil für Löschen-Buttons
        self.style.configure("Danger.TButton", background=colors["danger_bg"], foreground=colors["danger_fg"])
        self.style.map("Danger.TButton", background=[("active", colors["fg"])], foreground=[("active", colors["bg"])])

        self.style.configure("Header.TLabel", font=("Helvetica", 18, "bold"), background=colors["nav_bg"], foreground=colors["header_fg"])
        self.style.configure("CardTitle.TLabel", font=("Helvetica", 14, "bold"))
        self.style.configure("CardStats.TLabel", font=("Helvetica", 9))
        self.style.configure("TLabelframe", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("TLabelframe.Label", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("Nav.TFrame", background=colors["nav_bg"])

    def _on_close(self):
        """Speichert Daten robust und beendet die Anwendung sauber."""
        try:
            print("Speichere Daten und beende Anwendung...")
            self.data.setdefault("settings", {})["theme"] = self.current_theme.get()
            self.data_manager.save_data(self.data)
        except Exception as e:
            print(f"Ein Fehler ist beim Speichern aufgetreten: {e}")
            messagebox.showwarning(
                "Speicherfehler",
                f"Die Daten konnten nicht gespeichert werden:\n{e}\n\nDie Anwendung wird trotzdem beendet."
            )
        finally:
            # Wichtige Reihenfolge: Zuerst das Fenster zerstören, dann die mainloop beenden.
            print("Anwendung wird beendet.")
            self.destroy()
            self.quit()

    def show_frame(self, FrameClass, *args, **kwargs):
        """Zerstört den aktuellen Frame und zeigt einen neuen an."""
        for widget in self.container.winfo_children():
            widget.destroy()
        frame = FrameClass(self.container, self, *args, **kwargs)
        frame.pack(fill="both", expand=True)
        return frame

# --- BASIS-KLASSEN FÜR SEITEN ---
class BasePage(ttk.Frame):
    """Eine Basis-Seite mit einer Navigationsleiste."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.nav_bar = ttk.Frame(self, padding=5, style="Nav.TFrame")
        self.nav_bar.pack(fill='x', side='top')

        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Navigations-Buttons
        ttk.Button(self.nav_bar, text="Beenden & Speichern", command=self.controller._on_close).pack(side='right', padx=5)
        theme_toggle_text = "Light Mode" if self.controller.current_theme.get() == "dark" else "Dark Mode"
        self.theme_button = ttk.Button(self.nav_bar, text=theme_toggle_text, command=self.toggle_theme)
        self.theme_button.pack(side='right', padx=5)

    def toggle_theme(self):
        """Wechselt zwischen Light- und Dark-Mode."""
        new_theme = "dark" if self.controller.current_theme.get() == "light" else "light"
        self.controller.current_theme.set(new_theme)

        # Speichert Argumente, um den Frame nach dem Theme-Wechsel neu zu erstellen
        current_frame_class = self.__class__
        current_args = getattr(self, "init_args", {})
        self.controller.show_frame(current_frame_class, **current_args)

    def add_nav_button(self, text, command, side='left'):
        ttk.Button(self.nav_bar, text=text, command=command).pack(side=side, padx=5)

    def set_nav_title(self, text):
        ttk.Label(self.nav_bar, text=text, style="Header.TLabel").pack(side='left', padx=20)


class BaseTileFrame(BasePage):
    """Eine Basis-Seite für Ansichten mit Kacheln (Fächer, Lernsets)."""
    def __init__(self, parent, controller, **kwargs):
        self.init_args = kwargs
        super().__init__(parent, controller)
        bg_color = THEMES[self.controller.current_theme.get()]["bg"]

        # Canvas für scrollbaren Inhalt
        self.canvas = tk.Canvas(self.content_frame, borderwidth=0, highlightthickness=0, bg=bg_color)
        self.scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=self.canvas.yview)
        self.tiles_frame = ttk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.create_window((0, 0), window=self.tiles_frame, anchor="nw")
        self.tiles_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def create_context_menu(self, event, item_id, item_type):
        """Erstellt ein Kontextmenü für Kacheln (Rechtsklick)."""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Namen ändern", command=lambda: self.rename_item(item_id, item_type))
        color_menu = tk.Menu(menu, tearoff=0)
        for name, hex_code in PASTEL_COLORS.items():
            color_menu.add_command(label=name, background=hex_code, command=lambda h=hex_code: self.change_item_color(item_id, item_type, h))
        menu.add_cascade(label="Farbe ändern", menu=color_menu)
        menu.add_separator()
        menu.add_command(label="Löschen", command=lambda: self.delete_item(item_id, item_type), foreground="red")
        menu.tk_popup(event.x_root, event.y_root)

    # Platzhalter-Methoden, die in den Unterklassen implementiert werden müssen
    def change_item_color(self, item_id, item_type, hex_code): pass
    def rename_item(self, item_id, item_type): pass
    def delete_item(self, item_id, item_type): pass
    def refresh_view(self): pass

# --- SPEZIFISCHE SEITEN-IMPLEMENTIERUNGEN ---
class StartFrame(BaseTileFrame):
    """Startseite, die alle Fächer als Kacheln anzeigt."""
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.set_nav_title("Meine Fächer")
        self.add_nav_button("Neues Fach", self.create_subject_popup)
        self.refresh_view()

    def refresh_view(self):
        """Zeichnet die Fächer-Kacheln neu."""
        for widget in self.tiles_frame.winfo_children(): widget.destroy()

        subjects = self.controller.data
        row, col, max_cols = 0, 0, 3

        # Sortiert die Fächer alphabetisch nach Namen
        sorted_subjects = sorted(
            [item for item in subjects.items() if item[0] != "settings"],
            key=lambda item: item[1].get('name', '').lower()
        )

        for sid, sdata in sorted_subjects:
            sets = sdata.get("sets", {})
            num_tasks = sum(len(s.get("tasks", [])) for s in sets.values())
            card_color = sdata.get("color", DEFAULT_COLOR)
            text_color = get_readable_text_color(card_color)

            # Erstellt eine Kachel für jedes Fach
            card = tk.Frame(self.tiles_frame, relief="raised", borderwidth=1, bg=card_color)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            title = ttk.Label(card, text=sdata.get("name"), style="CardTitle.TLabel", background=card_color, foreground=text_color)
            title.pack(anchor="w", padx=10, pady=(10, 0))

            stats = ttk.Label(card, text=f"{len(sets)} Lernsets • {num_tasks} Karten", style="CardStats.TLabel", background=card_color, foreground=text_color)
            stats.pack(anchor="w", padx=10, pady=(0, 10))

            # Bindet Klick-Events an alle Elemente der Kachel
            for widget in [card, title, stats]:
                widget.bind("<Button-1>", lambda e, subject_id=sid: self.controller.show_frame(SetSelectFrame, subject_id=subject_id))
                widget.bind("<Button-3>", lambda e, subject_id=sid: self.create_context_menu(e, subject_id, 'subject'))

            col = (col + 1) % max_cols
            if col == 0: row += 1

        # SCROLL-FIX: Binden, nachdem alle Kacheln erstellt wurden
        bind_mouse_scroll(self.tiles_frame, self.canvas)

    def create_subject_popup(self):
        """Öffnet ein Dialogfenster, um ein neues Fach zu erstellen."""
        name = simpledialog.askstring("Neues Fach", "Wie soll das neue Fach heißen?", parent=self)
        if name:
            new_id = str(uuid.uuid4())
            self.controller.data[new_id] = {"name": name, "color": DEFAULT_COLOR, "sets": {}}
            self.controller.data_manager.save_data(self.controller.data)
            self.refresh_view()

    def rename_item(self, sid, item_type):
        old_name = self.controller.data[sid]["name"]
        new_name = simpledialog.askstring("Umbenennen", f"Neuer Name für '{old_name}':", parent=self)
        if new_name:
            self.controller.data[sid]["name"] = new_name
            self.controller.data_manager.save_data(self.controller.data)
            self.refresh_view()

    def change_item_color(self, sid, item_type, hex_code):
        self.controller.data[sid]["color"] = hex_code
        self.controller.data_manager.save_data(self.controller.data)
        self.refresh_view()

    def delete_item(self, sid, item_type):
        name = self.controller.data[sid]["name"]
        if messagebox.askyesno("Löschen", f"Soll das Fach '{name}' und alle zugehörigen Inhalte wirklich gelöscht werden?", icon='warning', default='no'):
            del self.controller.data[sid]
            self.controller.data_manager.save_data(self.controller.data)
            self.refresh_view()

class SetSelectFrame(BaseTileFrame):
    """Zeigt alle Lernsets eines ausgewählten Fachs an."""
    def __init__(self, parent, controller, subject_id):
        super().__init__(parent, controller, subject_id=subject_id)
        self.subject_id = subject_id
        if subject_id not in self.controller.data:
            controller.show_frame(StartFrame)
            return

        self.subject_data = self.controller.data[subject_id]
        self.set_nav_title(f"Lernsets in: {self.subject_data['name']}")
        self.add_nav_button("← Zurück zu den Fächern", lambda: controller.show_frame(StartFrame))
        self.add_nav_button("Neues Lernset", self.create_set_popup)
        self.refresh_view()

    def refresh_view(self):
        """Zeichnet die Lernset-Kacheln neu."""
        for widget in self.tiles_frame.winfo_children(): widget.destroy()

        sets = self.subject_data.get("sets", {})
        row, col, max_cols = 0, 0, 3

        sorted_sets = sorted(
            sets.items(),
            key=lambda item: item[1].get('name', '').lower()
        )

        for set_id, sdata in sorted_sets:
            card_color = sdata.get("color", DEFAULT_COLOR)
            text_color = get_readable_text_color(card_color)

            card = tk.Frame(self.tiles_frame, relief="raised", borderwidth=1, bg=card_color)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            title = ttk.Label(card, text=sdata.get("name"), style="CardTitle.TLabel", background=card_color, foreground=text_color)
            title.pack(anchor="w", padx=10, pady=(10, 0))

            stats = ttk.Label(card, text=f"{len(sdata.get('tasks',[]))} Karten", style="CardStats.TLabel", background=card_color, foreground=text_color)
            stats.pack(anchor="w", padx=10, pady=(0, 10))

            for widget in [card, title, stats]:
                widget.bind("<Button-1>", lambda e, sid=set_id: self.show_options_popup(e, sid))
                widget.bind("<Button-3>", lambda e, sid=set_id: self.create_context_menu(e, sid, 'set'))

            col = (col + 1) % max_cols
            if col == 0: row += 1

        # SCROLL-FIX: Binden, nachdem alle Kacheln erstellt wurden
        bind_mouse_scroll(self.tiles_frame, self.canvas)

    def create_set_popup(self):
        name = simpledialog.askstring("Neues Lernset", "Name für das neue Lernset:", parent=self)
        if name:
            new_id = str(uuid.uuid4())
            self.controller.data[self.subject_id]["sets"][new_id] = {"name": name, "color": DEFAULT_COLOR, "tasks": []}
            self.controller.data_manager.save_data(self.controller.data)
            self.refresh_view()

    def show_options_popup(self, event, set_id):
        """Zeigt ein Popup-Menü mit Aktionen für ein Lernset."""
        popup = tk.Toplevel(self)
        popup.title("Aktion wählen")
        popup.transient(self.controller)
        # HINWEIS: grab_set() wird erst später aufgerufen

        content_frame = ttk.Frame(popup, padding=20)
        content_frame.pack(expand=True, fill='both')

        tasks = self.subject_data["sets"][set_id].get("tasks", [])
        has_history = any(t.get('history') for t in tasks if t.get('history'))

        ttk.Button(content_frame, text="Lernen", command=lambda: [popup.destroy(), self.controller.show_frame(QuizFrame, subject_id=self.subject_id, set_id=set_id)], state="normal" if tasks else "disabled").pack(pady=5, fill='x')
        ttk.Button(content_frame, text="Lernset bearbeiten", command=lambda: [popup.destroy(), self.controller.show_frame(EditSetFrame, subject_id=self.subject_id, set_id=set_id)]).pack(pady=5, fill='x')
        ttk.Button(content_frame, text="Lernfortschritt", command=lambda: [popup.destroy(), self.controller.show_frame(StatisticsFrame, subject_id=self.subject_id, set_id=set_id)], state="normal" if has_history else "disabled").pack(pady=5, fill='x')
        ttk.Separator(content_frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Button(content_frame, text="Schließen", command=popup.destroy).pack(pady=5)

        # Stellt sicher, dass das Popup seine Größe kennt, bevor es positioniert wird
        popup.update_idletasks()

        # Positioniert das Popup in der Mitte des Hauptfensters
        x = self.controller.winfo_x() + (self.controller.winfo_width() // 2) - (popup.winfo_width() // 2)
        y = self.controller.winfo_y() + (self.controller.winfo_height() // 2) - (popup.winfo_height() // 2)
        popup.geometry(f"+{x}+{y}")

        # Jetzt, wo das Fenster sichtbar ist, kann der Fokus "gegrabbt" werden
        popup.grab_set()
        popup.wait_window()

    def rename_item(self, set_id, item_type):
        old_name = self.controller.data[self.subject_id]["sets"][set_id]["name"]
        new_name = simpledialog.askstring("Umbenennen", f"Neuer Name für '{old_name}':", parent=self)
        if new_name:
            self.controller.data[self.subject_id]["sets"][set_id]["name"] = new_name
            self.controller.data_manager.save_data(self.controller.data)
            self.refresh_view()

    def change_item_color(self, set_id, item_type, hex_code):
        self.controller.data[self.subject_id]["sets"][set_id]["color"] = hex_code
        self.controller.data_manager.save_data(self.controller.data)
        self.refresh_view()

    def delete_item(self, set_id, item_type):
        name = self.controller.data[self.subject_id]["sets"][set_id]["name"]
        if messagebox.askyesno("Löschen", f"Soll das Lernset '{name}' wirklich gelöscht werden?", icon='warning', default='no'):
            del self.controller.data[self.subject_id]["sets"][set_id]
            self.controller.data_manager.save_data(self.controller.data)
            self.refresh_view()

class BaseTaskEditor(ttk.Frame):
    """Eine Basisklasse, die gemeinsame UI-Elemente und Funktionen für den Aufgaben-Editor bereitstellt."""
    def __init__(self, parent, controller, subject_id, set_id):
        super().__init__(parent)
        self.controller = controller
        self.subject_id, self.set_id = subject_id, set_id
        self.subtask_widgets, self.task_image_path, self._task_image_full_path = [], tk.StringVar(), None

        self.build_editor_ui(self)
        self.setup_buttons(self)

    def build_editor_ui(self, parent):
        """Erstellt die Benutzeroberfläche des Editors."""
        colors = THEMES[self.controller.current_theme.get()]

        ttk.Label(parent, text=self.get_title(), font=("Helvetica", 16, "bold")).pack(pady=10)

        desc_frame = ttk.LabelFrame(parent, text="Aufgabenbeschreibung")
        desc_frame.pack(pady=10, padx=10, fill="x")
        self.task_desc_text = tk.Text(desc_frame, height=4, wrap=tk.WORD, bg=colors["text_bg"], fg=colors["fg"], insertbackground=colors['fg'])
        self.task_desc_text.pack(pady=5, padx=5, fill="x", expand=True)

        img_frame = ttk.Frame(desc_frame)
        img_frame.pack(fill="x", expand=True, padx=5)
        ttk.Button(img_frame, text="Bild für Aufgabe auswählen...", command=self.select_task_image).pack(side="left", pady=5)
        ttk.Label(img_frame, textvariable=self.task_image_path).pack(side="left", padx=10)

        tags_frame = ttk.LabelFrame(parent, text="Tags (mit Komma getrennt)")
        tags_frame.pack(pady=10, padx=10, fill="x")
        # BUGFIX: "insertbackground" entfernt. Farbe wird jetzt über den globalen Style gesetzt.
        self.tags_entry = ttk.Entry(tags_frame)
        self.tags_entry.pack(pady=5, padx=5, fill="x")

        # SCROLL-FIX: Die Unteraufgaben sind jetzt in einem einfachen LabelFrame.
        # Das Scrollen wird vom übergeordneten EditSetFrame gehandhabt.
        self.subtasks_frame = ttk.LabelFrame(parent, text="Unteraufgaben")
        self.subtasks_frame.pack(pady=10, padx=10, fill="x")

        ttk.Button(parent, text="+ Teilaufgabe hinzufügen", command=self.add_subtask_fields).pack(pady=5)

    def add_subtask_fields(self, subtask_data=None):
        """Fügt Felder für eine neue Unteraufgabe hinzu."""
        subtask_data = subtask_data or {}
        colors = THEMES[self.controller.current_theme.get()]

        # Der Frame für eine einzelne Teilaufgabe wird in self.subtasks_frame gepackt.
        frame = ttk.LabelFrame(self.subtasks_frame, text=f"Teilaufgabe {len(self.subtask_widgets) + 1}")
        frame.pack(pady=5, fill="x", padx=5)

        ttk.Label(frame, text="Frage:").pack(anchor="w", padx=5)
        q_text = tk.Text(frame, height=2, wrap=tk.WORD, bg=colors["text_bg"], fg=colors["fg"], insertbackground=colors['fg'])
        q_text.pack(fill="x", padx=5, pady=(0,5))
        q_text.insert("1.0", subtask_data.get("frage", ""))

        ttk.Label(frame, text="Lösung:").pack(anchor="w", padx=5)
        s_text = tk.Text(frame, height=2, wrap=tk.WORD, bg=colors["text_bg"], fg=colors["fg"], insertbackground=colors['fg'])
        s_text.pack(fill="x", padx=5, pady=(0,5))
        s_text.insert("1.0", subtask_data.get("loesung", ""))

        img_path_var = tk.StringVar(value=os.path.basename(subtask_data.get('bild_loesung', '') or ''))
        img_path_var._full_path = subtask_data.get('bild_loesung', None)

        img_frame = ttk.Frame(frame)
        img_frame.pack(fill="x", expand=True, padx=5, pady=5)
        ttk.Button(img_frame, text="Bild für Lösung...", command=lambda var=img_path_var: self.select_solution_image(var)).pack(side="left")
        ttk.Label(img_frame, textvariable=img_path_var).pack(side="left", padx=10)

        self.subtask_widgets.append({"question": q_text, "solution": s_text, "solution_image_path": img_path_var, "frame": frame})

    def select_task_image(self):
        path = filedialog.askopenfilename(title="Aufgaben-Bild auswählen", filetypes=[("Bilddateien", "*.png *.jpg *.jpeg *.gif"), ("Alle Dateien", "*.*")])
        if path:
            self.task_image_path.set(os.path.basename(path))
            self._task_image_full_path = path

    def select_solution_image(self, path_variable):
        path = filedialog.askopenfilename(title="Lösungs-Bild auswählen", filetypes=[("Bilddateien", "*.png *.jpg *.jpeg *.gif"), ("Alle Dateien", "*.*")])
        if path:
            path_variable.set(os.path.basename(path))
            path_variable._full_path = path

    def collect_data(self):
        """Sammelt alle Daten aus den Eingabefeldern und gibt sie als Dictionary zurück."""
        task_desc = self.task_desc_text.get("1.0", "end-1c").strip()
        if not task_desc:
            messagebox.showwarning("Fehler", "Die Aufgabenbeschreibung darf nicht leer sein.")
            return None

        tags = [tag.strip() for tag in self.tags_entry.get().split(',') if tag.strip()]
        task_image = self.controller.data_manager.copy_image_to_datastore(self._task_image_full_path)

        subtasks = []
        for widgets in self.subtask_widgets:
            q = widgets["question"].get("1.0", "end-1c").strip()
            if not q: continue
            s = widgets["solution"].get("1.0", "end-1c").strip()
            img_path = widgets["solution_image_path"]._full_path
            img = self.controller.data_manager.copy_image_to_datastore(img_path)
            subtasks.append({"frage": q, "loesung": s, "bild_loesung": img})

        return {"beschreibung": task_desc, "tags": tags, "bild_aufgabe": task_image, "unteraufgaben": subtasks}

    # Abstrakte Methoden
    def get_title(self): raise NotImplementedError
    def setup_buttons(self, parent): raise NotImplementedError

class EditSetFrame(BasePage):
    """Seite zum Bearbeiten eines Lernsets (Aufgaben hinzufügen, bearbeiten, löschen)."""
    def __init__(self, parent, controller, subject_id, set_id):
        self.init_args = {"subject_id": subject_id, "set_id": set_id}
        super().__init__(parent, controller)
        self.subject_id, self.set_id, self.current_task_id = subject_id, set_id, None

        self.set_nav_title(f"Bearbeite: {controller.data[subject_id]['sets'][set_id]['name']}")
        self.add_nav_button("← Zurück zu den Lernsets", lambda: controller.show_frame(SetSelectFrame, subject_id=subject_id))

        paned_window = ttk.PanedWindow(self.content_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # --- LINKE SPALTE (Aufgabenliste) ---
        left_frame = ttk.Frame(paned_window, width=300)
        paned_window.add(left_frame, weight=1)

        colors = THEMES[controller.current_theme.get()]
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill='both', expand=True, pady=5)
        ttk.Label(list_frame, text="Aufgaben", font=("Helvetica", 12, "bold")).pack()
        self.task_listbox = tk.Listbox(list_frame, bg=colors["list_bg"], fg=colors["list_fg"], selectbackground=colors["button_bg"], font=("Helvetica", 10), selectforeground=get_readable_text_color(colors["button_bg"]))
        self.task_listbox.pack(fill=tk.BOTH, expand=True)
        self.task_listbox.bind("<<ListboxSelect>>", self.on_task_select)
        ttk.Button(left_frame, text="+ Neue Aufgabe erstellen", command=self.create_new_task).pack(fill='x', pady=5)

        # --- RECHTE SPALTE (Scrollbarer Editor) ---
        editor_canvas_container = ttk.Frame(paned_window)
        paned_window.add(editor_canvas_container, weight=3)

        self.editor_canvas = tk.Canvas(editor_canvas_container, borderwidth=0, highlightthickness=0, bg=colors['bg'])
        editor_scrollbar = ttk.Scrollbar(editor_canvas_container, orient="vertical", command=self.editor_canvas.yview)
        # Dies ist der Frame, der den eigentlichen Editor-Inhalt aufnimmt
        self.editor_container = ttk.Frame(self.editor_canvas)

        self.editor_canvas.configure(yscrollcommand=editor_scrollbar.set)
        editor_scrollbar.pack(side="right", fill="y")
        self.editor_canvas.pack(side="left", fill="both", expand=True)

        canvas_window = self.editor_canvas.create_window((0, 0), window=self.editor_container, anchor="nw")

        self.editor_container.bind("<Configure>", lambda e: self.editor_canvas.configure(scrollregion=self.editor_canvas.bbox("all")))
        self.editor_canvas.bind("<Configure>", lambda e: self.editor_canvas.itemconfig(canvas_window, width=e.width))

        self.refresh_task_list()
        self.show_placeholder()

    def create_star_rating(self, rating):
        return "★" * rating + "☆" * (5 - rating)

    def show_placeholder(self):
        """Zeigt eine Nachricht an, wenn keine Aufgabe ausgewählt ist."""
        for widget in self.editor_container.winfo_children(): widget.destroy()
        ttk.Label(self.editor_container, text="Wähle eine Aufgabe aus oder erstelle eine neue.", font=("Helvetica", 12)).pack(pady=50)

    def refresh_task_list(self):
        """Aktualisiert die Liste der Aufgaben."""
        self.task_listbox.delete(0, tk.END)
        self.tasks = self.controller.data[self.subject_id]["sets"][self.set_id].get("tasks", [])
        for i, task in enumerate(self.tasks):
            preview = task.get('beschreibung', 'Unbenannte Aufgabe').split('\n')[0][:25]
            rating = task.get('rating', 0)
            stars = self.create_star_rating(rating)
            self.task_listbox.insert(tk.END, f"{stars} | {preview}...")
        self.show_placeholder()

    def on_task_select(self, event=None):
        indices = self.task_listbox.curselection()
        if not indices: return
        task_data = self.tasks[indices[0]]
        self.current_task_id = task_data.get('id')
        if not self.current_task_id:
            messagebox.showerror("Fehler", "Diese Aufgabe hat keine gültige ID und kann nicht bearbeitet werden.")
            return
        self.load_editor(task_data)

    def create_new_task(self):
        self.current_task_id = None
        self.task_listbox.selection_clear(0, tk.END)
        self.load_editor(None)

    def load_editor(self, task_data):
        """Lädt den Editor für eine neue oder bestehende Aufgabe."""
        for widget in self.editor_container.winfo_children(): widget.destroy()
        editor = self.TaskEditor(self.editor_container, self.controller, self.subject_id, self.set_id, task_data, self.refresh_task_list)
        editor.pack(fill="both", expand=True)

        # SCROLL-FIX: Binden, nachdem der Editor-Inhalt erstellt wurde.
        bind_mouse_scroll(self.editor_container, self.editor_canvas)

    # Innere Klasse für den Editor selbst
    class TaskEditor(BaseTaskEditor):
        def __init__(self, parent, controller, subject_id, set_id, task_data, refresh_callback):
            self.task_data, self.refresh_callback = task_data, refresh_callback
            super().__init__(parent, controller, subject_id, set_id)
            if self.task_data: self.load_data()
            else: self.add_subtask_fields()

        def get_title(self):
            return "Aufgabe bearbeiten" if self.task_data else "Neue Aufgabe erstellen"

        def setup_buttons(self, parent):
            btn_frame = ttk.Frame(parent)
            btn_frame.pack(side="bottom", fill="x", pady=10)
            ttk.Button(btn_frame, text="Speichern", command=self.save_changes).pack(side="left", padx=10)
            if self.task_data:
                ttk.Button(btn_frame, text="Löschen", style="Danger.TButton", command=self.delete_task).pack(side="right", padx=10)

        def load_data(self):
            """Füllt die Editor-Felder mit den Daten einer bestehenden Aufgabe."""
            self.task_desc_text.insert("1.0", self.task_data.get('beschreibung', ''))
            self.tags_entry.insert(0, ", ".join(self.task_data.get('tags', [])))
            self._task_image_full_path = self.task_data.get('bild_aufgabe')
            self.task_image_path.set(os.path.basename(self._task_image_full_path or ''))
            for subtask in self.task_data.get('unteraufgaben', []):
                self.add_subtask_fields(subtask)

        def save_changes(self):
            """Speichert die Änderungen an der Aufgabe."""
            updated_data = self.collect_data()
            if updated_data is None: return

            task_list = self.controller.data[self.subject_id]["sets"][self.set_id].setdefault("tasks", [])
            if self.task_data: # Bearbeiten einer bestehenden Aufgabe
                for i, task in enumerate(task_list):
                    if task.get('id') == self.task_data['id']:
                        updated_data['id'] = self.task_data['id']
                        updated_data['history'] = self.task_data.get('history', [])
                        updated_data['rating'] = self.task_data.get('rating', 0)
                        task_list[i] = updated_data
                        break
            else: # Erstellen einer neuen Aufgabe
                updated_data['id'] = str(uuid.uuid4())
                updated_data['history'] = []
                updated_data['rating'] = 0
                task_list.append(updated_data)

            self.controller.data_manager.save_data(self.controller.data)
            messagebox.showinfo("Gespeichert", "Änderungen wurden erfolgreich gespeichert.")
            self.refresh_callback()

        def delete_task(self):
            if messagebox.askyesno("Löschen", "Soll diese Aufgabe wirklich endgültig gelöscht werden?", icon='warning', default='no'):
                task_list = self.controller.data[self.subject_id]["sets"][self.set_id]["tasks"]
                task_list[:] = [t for t in task_list if t.get('id') != self.task_data['id']]
                self.controller.data_manager.save_data(self.controller.data)
                self.refresh_callback()

class QuizFrame(BasePage):
    """Der Lernmodus. Zeigt Aufgaben an, stoppt die Zeit und wertet aus."""
    def __init__(self, parent, controller, subject_id, set_id):
        self.init_args = {"subject_id": subject_id, "set_id": set_id}
        super().__init__(parent, controller)
        self.subject_id, self.set_id = subject_id, set_id
        self.photo_references, self.current_task, self.timer_running = [], None, False
        self.recently_shown_tasks = deque(maxlen=3) # Verhindert, dass die gleiche Aufgabe direkt wieder kommt

        self.set_nav_title("Lernmodus")
        self.add_nav_button("← Beenden & Speichern", self.finish_quiz)

        self.load_new_question()
        if self.current_task: self.start_timer()

    def _display_content(self, parent, text, image_path=None):
        """Rendert Text, LaTeX und Bilder in einem Frame."""
        colors = THEMES[self.controller.current_theme.get()]

        # Regex, um LaTeX-Formeln ($...$) zu finden
        parts = re.split(r'(\$.*?\$)', text)

        # Widgets werden in Zeilen angeordnet
        current_line_frame = ttk.Frame(parent)
        current_line_frame.pack(fill="x", anchor='nw')

        for part in parts:
            if part.startswith('$') and part.endswith('$'):
                formula = part[1:-1]
                latex_img = render_latex(formula, fg=colors['fg'], bg=parent.cget('bg'))
                if latex_img:
                    photo = ImageTk.PhotoImage(latex_img)
                    self.photo_references.append(photo) # Wichtig: Referenz behalten
                    ttk.Label(current_line_frame, image=photo, background=parent.cget('bg')).pack(side="left", anchor='nw', pady=2)
            elif part:
                # Behandelt Text mit Zeilenumbrüchen
                sub_parts = part.split('\n')
                for i, sub_part in enumerate(sub_parts):
                    if sub_part:
                        ttk.Label(current_line_frame, text=sub_part, wraplength=750, justify=tk.LEFT).pack(side="left", anchor='nw')
                    if i < len(sub_parts) - 1:
                        current_line_frame = ttk.Frame(parent)
                        current_line_frame.pack(fill="x", anchor='nw')

        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img.thumbnail((400, 400))
                photo = ImageTk.PhotoImage(img)
                self.photo_references.append(photo)
                img_label = ttk.Label(parent, image=photo)
                img_label.pack(pady=5)
            except Exception as e:
                print(f"Fehler beim Bildladen: {e}")

    def load_new_question(self):
        """Wählt eine neue Aufgabe aus und baut die UI dafür auf."""
        self.photo_references.clear()
        self.correct_answers = 0
        tasks = self.controller.data[self.subject_id]["sets"][self.set_id].get("tasks", [])
        if not tasks:
            messagebox.showinfo("Fertig", "In diesem Lernset sind keine Aufgaben vorhanden.")
            self.finish_quiz()
            return

        # Filtert Aufgaben, die kürzlich gezeigt wurden, heraus
        available_tasks = [t for t in tasks if t.get('id') not in self.recently_shown_tasks]
        if not available_tasks: available_tasks = tasks

        # Gewichtete Auswahl: Aufgaben mit schlechterer Bewertung kommen wahrscheinlicher dran
        weights = [(6 - task.get('rating', 0))**2 for task in available_tasks]
        self.current_task = random.choices(available_tasks, weights=weights, k=1)[0]
        self.recently_shown_tasks.append(self.current_task.get('id'))

        self.build_ui_for_current_question()

    def build_ui_for_current_question(self):
        """Erstellt die Benutzeroberfläche für die aktuell geladene Frage."""
        for widget in self.content_frame.winfo_children(): widget.destroy()
        if not self.current_task: return

        self.total_subtasks = len(self.current_task.get("unteraufgaben", []))
        colors = THEMES[self.controller.current_theme.get()]

        top_frame = ttk.Frame(self.content_frame)
        top_frame.pack(fill="x", pady=10)
        self.timer_label = ttk.Label(top_frame, text="00:00", font=("Helvetica", 14))
        self.timer_label.pack(side="left", padx=10)
        self.score_label = ttk.Label(top_frame, text=f"Score: 0 / {self.total_subtasks}", font=("Helvetica", 14))
        self.score_label.pack(side="left", padx=20)
        ttk.Button(top_frame, text="Nächste Aufgabe", command=self.next_question).pack(side="right")

        main_canvas = tk.Canvas(self.content_frame, borderwidth=0, highlightthickness=0, bg=colors['bg'])
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=main_canvas.yview)
        main_frame = ttk.Frame(main_canvas)
        main_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        main_canvas.pack(side="left", fill="both", expand=True)
        canvas_window = main_canvas.create_window((0, 0), window=main_frame, anchor="nw")

        # Passt die Breite des Frames im Canvas an die Canvas-Größe an
        main_frame.bind("<Configure>", lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))
        main_canvas.bind("<Configure>", lambda e: main_canvas.itemconfig(canvas_window, width=e.width))

        task_frame = ttk.LabelFrame(main_frame, text="Aufgabe")
        task_frame.pack(fill="x", pady=10, padx=5)
        self._display_content(task_frame, self.current_task['beschreibung'], self.current_task.get('bild_aufgabe'))

        # Zeigt Tags und Bewertung an
        info_frame = ttk.Frame(task_frame)
        info_frame.pack(fill='x', anchor='w', padx=5, pady=5)
        tags = self.current_task.get('tags', [])
        if tags: ttk.Label(info_frame, text=f"Tags: {', '.join(tags)}", font=("Helvetica", 9, "italic")).pack(side='left')
        rating = self.current_task.get('rating', 0)
        stars = "★" * rating + "☆" * (5 - rating)
        ttk.Label(info_frame, text=f"  Bewertung: {stars}", font=("Helvetica", 9, "italic")).pack(side='left', padx=10)

        for i, subtask in enumerate(self.current_task.get("unteraufgaben", [])):
            sub_frame = ttk.LabelFrame(main_frame, text=f"Teilaufgabe {chr(97 + i)}")
            sub_frame.pack(fill="x", padx=10, pady=5)
            self._display_content(sub_frame, subtask["frage"])

            action_frame = ttk.Frame(sub_frame)
            action_frame.pack(fill="x", padx=10, pady=5)
            solution_widgets = {"container": None}
            ttk.Button(action_frame, text="Lösung anzeigen", command=lambda s=subtask, sf=sub_frame, sw=solution_widgets: self.show_solution(s, sf, sw)).pack(side="left")

            feedback_frame = ttk.Frame(sub_frame)
            feedback_frame.pack(fill="x", padx=10, pady=5)
            b_correct = ttk.Button(feedback_frame, text="Korrekt", command=lambda ff=feedback_frame: self.mark_answer(ff, True))
            b_correct.pack(side="left", padx=5)
            b_false = ttk.Button(feedback_frame, text="Falsch", command=lambda ff=feedback_frame: self.mark_answer(ff, False))
            b_false.pack(side="left", padx=5)

        # SCROLL-FIX: Binden, nachdem der gesamte Inhalt des Quiz-Frames erstellt wurde
        bind_mouse_scroll(main_frame, main_canvas)


    def show_solution(self, subtask, parent_frame, solution_widgets):
        """Zeigt die Lösung für eine Teilaufgabe an oder verbirgt sie."""
        if solution_widgets.get("container") and solution_widgets["container"].winfo_exists():
            solution_widgets["container"].destroy()
            solution_widgets["container"] = None
        else:
            container = ttk.LabelFrame(parent_frame, text="Lösung")
            container.pack(fill="x", pady=5)
            self._display_content(container, subtask['loesung'], subtask.get('bild_loesung'))
            solution_widgets["container"] = container

    def mark_answer(self, button_frame, is_correct):
        """Markiert eine Antwort als korrekt oder falsch und aktualisiert den Score."""
        if is_correct:
            self.correct_answers += 1
            ttk.Label(button_frame, text="✓ Korrekt", foreground="green", font=("Helvetica", 10, "bold")).pack(side="left", padx=10)
        else:
            ttk.Label(button_frame, text="✗ Falsch", foreground="red", font=("Helvetica", 10, "bold")).pack(side="left", padx=10)

        # Deaktiviert die Feedback-Buttons nach der Eingabe
        for widget in button_frame.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.config(state="disabled")

        self.score_label.config(text=f"Score: {self.correct_answers} / {self.total_subtasks}")

    # --- Timer-Funktionen ---
    def start_timer(self):
        self.start_time = time.time()
        self.timer_running = True
        self.update_timer()

    def update_timer(self):
        if not self.timer_running: return
        elapsed = time.time() - self.start_time
        m, s = divmod(int(elapsed), 60)
        self.timer_label.config(text=f"{m:02d}:{s:02d}")
        self.after(1000, self.update_timer)

    def stop_timer(self):
        self.timer_running = False

    def save_performance(self):
        """Speichert die Leistung (Zeit, Korrektheit) und aktualisiert die Bewertung der Aufgabe."""
        if not self.current_task or not hasattr(self, 'start_time') or not self.current_task.get('id'):
            return

        elapsed = time.time() - self.start_time
        task_list = self.controller.data[self.subject_id]["sets"][self.set_id]["tasks"]

        for i, task in enumerate(task_list):
            if task.get('id') == self.current_task.get('id'):
                performance = (self.correct_answers / self.total_subtasks) * 100 if self.total_subtasks > 0 else 0

                # Aktualisiert die 5-Sterne-Bewertung basierend auf der Leistung
                if performance >= 81: new_rating = 5
                elif performance >= 61: new_rating = 4
                elif performance >= 41: new_rating = 3
                elif performance >= 21: new_rating = 2
                elif performance > 0: new_rating = 1
                else: new_rating = 0
                task['rating'] = new_rating

                # Fügt einen Eintrag zur Lernhistorie hinzu
                history_entry = {
                    "timestamp": time.time(),
                    "time_taken": elapsed,
                    "correct": self.correct_answers,
                    "total": self.total_subtasks
                }
                task.setdefault('history', []).append(history_entry)

                # Speichert die Daten sofort
                self.controller.data_manager.save_data(self.controller.data)
                break

    def next_question(self):
        self.save_performance()
        self.stop_timer()
        self.load_new_question()
        if self.current_task:
            self.start_timer()

    def finish_quiz(self):
        self.save_performance()
        self.stop_timer()
        self.current_task = None
        self.controller.show_frame(SetSelectFrame, subject_id=self.subject_id)

class StatisticsFrame(BasePage):
    """Zeigt den Lernfortschritt als Diagramm an."""
    def __init__(self, parent, controller, subject_id, set_id):
        self.init_args = {"subject_id": subject_id, "set_id": set_id}
        super().__init__(parent, controller)
        self.subject_id = subject_id
        self.set_id = set_id
        set_name = controller.data[subject_id]["sets"][set_id]["name"]

        self.fig = None
        self.canvas = None

        self.set_nav_title(f"Fortschritt für: {set_name}")
        self.add_nav_button("← Zurück zu den Lernsets", lambda: self.controller.show_frame(SetSelectFrame, subject_id=subject_id))

        control_frame = ttk.Frame(self.content_frame)
        control_frame.pack(fill='x', pady=5)

        self.tasks = controller.data[subject_id]["sets"][set_id].get("tasks", [])
        task_names = ["Gesamtübersicht"] + [f"{task.get('beschreibung', 'Unbenannte Aufgabe').splitlines()[0][:40]}..." for task in self.tasks]
        self.task_var = tk.StringVar(value=task_names[0])

        ttk.Label(control_frame, text="Anzeigen für:").pack(side='left', padx=(0, 5))
        self.task_selector = ttk.Combobox(control_frame, textvariable=self.task_var, values=task_names, state='readonly', width=45)
        self.task_selector.pack(side='left', padx=5)
        self.task_selector.bind("<<ComboboxSelected>>", self.on_task_selected)

        ttk.Button(control_frame, text="Fortschritt zurücksetzen", command=self.reset_progress, style="Danger.TButton").pack(side='right', padx=5)

        self.plot_container = ttk.Frame(self.content_frame)
        self.plot_container.pack(fill='both', expand=True)

        self.on_task_selected()

    def on_task_selected(self, event=None):
        """Wird aufgerufen, wenn eine andere Aufgabe im Dropdown-Menü ausgewählt wird."""
        selected_index = self.task_selector.current()
        if selected_index == -1: return # Nichts ausgewählt
        if selected_index == 0: # Gesamtübersicht
            self.update_plots()
        else:
            task = self.tasks[selected_index - 1]
            self.update_plots(task_id=task.get('id'))

    def update_plots(self, task_id=None):
        """Aktualisiert die Diagramme basierend auf der Auswahl."""
        # Zerstört alte Widgets im Plot-Container
        for widget in self.plot_container.winfo_children():
            widget.destroy()
        if self.fig:
            plt.close(self.fig)

        history_data = []
        if task_id: # Daten für eine einzelne Aufgabe sammeln
            for task in self.tasks:
                if task.get('id') == task_id:
                    history_data = task.get('history', [])
                    break
        else: # Daten für alle Aufgaben sammeln
            for task in self.tasks:
                history_data.extend(task.get('history', []))

        # Sortiert die Daten nach Zeitstempel
        history_data.sort(key=lambda x: x['timestamp'])

        if not history_data:
            ttk.Label(self.plot_container, text="Noch keine Lerndaten für diese Auswahl vorhanden.").pack(pady=20)
        else:
            self.create_plots(history_data)

    def reset_progress(self):
        """Setzt den Lernfortschritt für die ausgewählte Aufgabe oder das gesamte Set zurück."""
        selected_index = self.task_selector.current()
        if selected_index == -1: return # Nichts ausgewählt

        if selected_index == 0: # Gesamtübersicht
            if messagebox.askyesno("Fortschritt zurücksetzen", "Möchtest du wirklich den gesamten Lernfortschritt für dieses Set löschen?", icon='warning', default='no'):
                for task in self.tasks:
                    task['history'] = []
                    task['rating'] = 0
        else: # Einzelne Aufgabe
            task = self.tasks[selected_index - 1]
            task_name = task.get('beschreibung', 'diese Aufgabe').splitlines()[0][:30]
            if messagebox.askyesno("Fortschritt zurücksetzen", f"Möchtest du wirklich den Lernfortschritt für die Aufgabe '{task_name}...' löschen?", icon='warning', default='no'):
                task['history'] = []
                task['rating'] = 0

        self.controller.data_manager.save_data(self.controller.data)
        self.on_task_selected() # Aktualisiert die Ansicht

    def create_plots(self, data):
        """Erstellt die Matplotlib-Diagramme und bettet sie in Tkinter ein."""
        theme = THEMES[self.controller.current_theme.get()]
        plt.style.use('seaborn-v0_8-darkgrid' if self.controller.current_theme.get() == 'dark' else 'seaborn-v0_8-whitegrid')

        attempts = range(1, len(data) + 1)
        times_taken = [d['time_taken'] for d in data]
        percentages = [(d['correct'] / d.get('total', 1)) * 100 if d.get('total', 0) > 0 else 0 for d in data]

        self.fig, ax1 = plt.subplots(figsize=(10, 6), tight_layout=True)
        self.fig.patch.set_facecolor(theme['bg'])

        # Erste Y-Achse (Zeit)
        ax1.set_facecolor(theme['card_bg'])
        ax1.set_xlabel('Lernsitzung (Versuch Nr.)', color=theme['fg'])
        ax1.set_ylabel('Benötigte Zeit (Sekunden)', color='tab:blue')
        ax1.plot(attempts, times_taken, marker='o', linestyle='-', color='tab:blue', label='Zeit')
        ax1.tick_params(axis='y', labelcolor='tab:blue')
        ax1.tick_params(axis='x', colors=theme['fg'])
        ax1.spines['bottom'].set_color(theme['fg'])
        ax1.spines['left'].set_color(theme['fg'])
        ax1.spines['top'].set_color(theme['fg'])
        ax1.spines['right'].set_color(theme['fg'])
        ax1.xaxis.label.set_color(theme['fg'])

        # Zweite Y-Achse (Erfolgsquote)
        ax2 = ax1.twinx()
        ax2.set_ylabel('Erfolgsquote (%)', color='tab:green')
        ax2.plot(attempts, percentages, marker='s', linestyle='--', color='tab:green', label='Erfolg')
        ax2.tick_params(axis='y', labelcolor='tab:green')
        ax2.set_ylim(0, 105)

        ax1.set_title("Lernfortschritt über die Zeit", color=theme['fg'])
        ax1.xaxis.set_major_locator(MaxNLocator(integer=True))
        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, self.plot_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)


# --- Startpunkt der Anwendung ---
if __name__ == "__main__":
    app = LernApp()
    app.mainloop()
