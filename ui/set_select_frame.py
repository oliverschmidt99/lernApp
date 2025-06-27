import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import uuid
import time
from functools import partial

# Relative Importe aus dem ui-Paket
from .base_frames import BasePage
from .edit_set_frame import EditSetFrame
from .quiz_frame import QuizFrame
from .statistics_frame import StatisticsFrame
from . import custom_dialogs

# Absolute Importe
import utils
import constants

class SetSelectFrame(BasePage):
    """Zeigt die Lernsets als Kacheln links und die Statistiken rechts an."""
    def __init__(self, parent, controller, subject_id):
        self.init_args = {"subject_id": subject_id}
        super().__init__(parent, controller)
        
        self.subject_id = subject_id
        if subject_id not in self.controller.data:
            from .start_frame import StartFrame
            controller.show_frame(StartFrame)
            return
            
        self.subject_data = self.controller.data[subject_id]
        self.set_nav_title(f"Lernsets in: {self.subject_data['name']}")
        self.add_nav_button("← Zurück zu den Fächern", self.go_to_start_frame)
        self.add_nav_button("Neues Lernset", self.create_set_popup)
        
        # Geteilte Ansicht
        paned_window = ttk.PanedWindow(self.content_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # --- Linke Spalte (Kachelansicht der Lernsets) ---
        left_frame = ttk.Frame(paned_window, width=350)
        paned_window.add(left_frame, weight=1)
        
        # Canvas für scrollbare Kacheln
        self.canvas = tk.Canvas(left_frame, borderwidth=0, highlightthickness=0, bg=constants.THEMES[controller.current_theme.get()]["bg"])
        self.scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.canvas.yview)
        self.tiles_frame = ttk.Frame(self.canvas)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.canvas.create_window((0, 0), window=self.tiles_frame, anchor="nw")
        self.tiles_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        utils.bind_mouse_scroll(self, self.canvas)

        # --- Rechte Spalte (Container für Statistiken) ---
        self.statistics_container = ttk.Frame(paned_window)
        paned_window.add(self.statistics_container, weight=2)
        
        self.refresh_view()
        self.show_placeholder()

    def go_to_start_frame(self):
        from .start_frame import StartFrame
        self.controller.show_frame(StartFrame)

    def refresh_view(self):
        """Zeichnet die Lernset-Kacheln auf der linken Seite neu."""
        for widget in self.tiles_frame.winfo_children():
            widget.destroy()
        
        self.sets_data = sorted(
            self.subject_data.get("sets", {}).items(),
            key=lambda item: item[1].get('name', '').lower()
        )
        
        row, col = 0, 0 

        for set_id, sdata in self.sets_data:
            card_color = sdata.get("color", constants.DEFAULT_COLOR)
            text_color = utils.get_readable_text_color(card_color)
            
            card = tk.Frame(self.tiles_frame, relief="raised", borderwidth=1, bg=card_color)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
            self.tiles_frame.grid_columnconfigure(col, weight=1)

            title = ttk.Label(card, text=sdata.get("name"), style="CardTitle.TLabel", background=card_color, foreground=text_color)
            title.pack(anchor="w", padx=10, pady=(10, 0))
            
            stats = ttk.Label(card, text=f"{len(sdata.get('tasks',[]))} Karten", style="CardStats.TLabel", background=card_color, foreground=text_color)
            stats.pack(anchor="w", padx=10, pady=(0, 10))

            for widget in [card, title, stats]:
                widget.bind("<Button-1>", lambda e, sid=set_id: self.load_statistics_for_set(sid))
                widget.bind("<Button-3>", lambda e, sid=set_id: self.create_context_menu(e, sid))
            
            row += 1
        
        utils.bind_mouse_scroll(self.tiles_frame, self.canvas)

    def load_statistics_for_set(self, set_id):
        """Lädt die Statistik-Ansicht für das ausgewählte Set auf der rechten Seite."""
        for widget in self.statistics_container.winfo_children():
            widget.destroy()
        
        stats_frame = StatisticsFrame(self.statistics_container, self.controller, self.subject_id, set_id)
        stats_frame.pack(fill="both", expand=True)

    def show_placeholder(self):
        """Zeigt eine Nachricht an, wenn kein Set ausgewählt ist."""
        for widget in self.statistics_container.winfo_children():
            widget.destroy()
        ttk.Label(self.statistics_container, text="Wähle ein Lernset aus, um den Fortschritt zu sehen.",
                  font=("Helvetica", 12)).pack(pady=50)

    def create_context_menu(self, event, set_id):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Namen ändern", command=lambda: self.rename_item(set_id))
        color_menu = tk.Menu(menu, tearoff=0)
        for name, hex_code in constants.PASTEL_COLORS.items():
            color_menu.add_command(label=name, background=hex_code, command=lambda h=hex_code: self.change_item_color(set_id, h))
        menu.add_cascade(label="Farbe ändern", menu=color_menu)
        menu.add_separator()
        menu.add_command(label="Fortschritt zurücksetzen", command=lambda: self._reset_set_progress(set_id))
        menu.add_separator()
        menu.add_command(label="Löschen", command=lambda: self.delete_item(set_id), foreground="red")
        menu.tk_popup(event.x_root, event.y_root)

    def create_set_popup(self):
        name = custom_dialogs.ask_string_themed(self, "Neues Lernset", "Name für das neue Lernset:", self.controller)
        if name:
            new_id = str(uuid.uuid4())
            self.subject_data["sets"][new_id] = {"name": name, "color": constants.DEFAULT_COLOR, "tasks": []}
            self.controller.data_manager.save_data(self.controller.data)
            self.refresh_view()

    def _reset_set_progress(self, set_id):
        set_name = self.subject_data["sets"][set_id]["name"]
        message = f"Möchtest du wirklich den gesamten Lernfortschritt für das Set '{set_name}' zurücksetzen?"
        if messagebox.askyesno("Fortschritt zurücksetzen", message, icon='warning', default='no'):
            now = time.time()
            tasks_to_reset = self.subject_data["sets"][set_id].get("tasks", [])
            for task in tasks_to_reset:
                task['history'] = []
                task.setdefault('sm_data', {})['status'] = 'new'
                task['sm_data']['next_review_at'] = now
                task['sm_data']['consecutive_good'] = 0
            self.controller.data_manager.save_data(self.controller.data)
            messagebox.showinfo("Erfolg", f"Der Fortschritt für '{set_name}' wurde zurückgesetzt.")
            self.load_statistics_for_set(set_id)

    def rename_item(self, set_id):
        old_name = self.subject_data["sets"][set_id]["name"]
        new_name = custom_dialogs.ask_string_themed(self, "Umbenennen", f"Neuer Name für '{old_name}':", self.controller)
        if new_name:
            self.subject_data["sets"][set_id]["name"] = new_name
            self.controller.data_manager.save_data(self.controller.data)
            self.after(10, self.refresh_view) # KORREKTUR

    def change_item_color(self, set_id, hex_code):
        self.subject_data["sets"][set_id]["color"] = hex_code
        self.controller.data_manager.save_data(self.controller.data)
        self.after(10, self.refresh_view) # KORREKTUR

    def delete_item(self, set_id):
        name = self.subject_data["sets"][set_id]["name"]
        if messagebox.askyesno("Löschen", f"Soll das Lernset '{name}' wirklich gelöscht werden?", icon='warning', default='no'):
            del self.subject_data["sets"][set_id]
            self.controller.data_manager.save_data(self.controller.data)
            # KORREKTUR
            self.after(10, self.refresh_view)
            self.after(10, self.show_placeholder)
