import tkinter as tk
from tkinter import ttk, messagebox
import uuid

# Relative Importe aus dem ui-Paket
from .base_frames import BaseTileFrame
# KORREKTUR: Der direkte Import von SetSelectFrame wird entfernt, um den Zirkel zu durchbrechen.
# from .set_select_frame import SetSelectFrame 
from . import custom_dialogs

# Absolute Importe für Dateien außerhalb des ui-Pakets
import utils
import constants

class StartFrame(BaseTileFrame):
    """Startseite, die alle Fächer als Kacheln anzeigt."""
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.set_nav_title("Meine Fächer")
        self.add_nav_button("Neues Fach", self.create_subject_popup)
        self.refresh_view()

    def _go_to_set_select(self, subject_id):
        """Navigiert sicher zum SetSelectFrame, um zirkuläre Imports zu vermeiden."""
        # Der Import geschieht erst hier, wenn er wirklich benötigt wird.
        from .set_select_frame import SetSelectFrame
        self.controller.show_frame(SetSelectFrame, subject_id=subject_id)

    def refresh_view(self):
        """Zeichnet die Fächer-Kacheln neu."""
        for widget in self.tiles_frame.winfo_children():
            widget.destroy()
        
        subjects = self.controller.data
        row, col, max_cols = 0, 0, 3
        
        sorted_subjects = sorted(
            [item for item in subjects.items() if item[0] != "settings"],
            key=lambda item: item[1].get('name', '').lower()
        )

        for sid, sdata in sorted_subjects:
            sets = sdata.get("sets", {})
            num_tasks = sum(len(s.get("tasks", [])) for s in sets.values())
            card_color = sdata.get("color", constants.DEFAULT_COLOR)
            text_color = utils.get_readable_text_color(card_color)

            card = tk.Frame(self.tiles_frame, relief="raised", borderwidth=1, bg=card_color)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
            self.tiles_frame.grid_columnconfigure(col, weight=1)
            
            title = ttk.Label(card, text=sdata.get("name"), style="CardTitle.TLabel", background=card_color, foreground=text_color)
            title.pack(anchor="w", padx=10, pady=(10, 0))
            
            stats = ttk.Label(card, text=f"{len(sets)} Lernsets • {num_tasks} Karten", style="CardStats.TLabel", background=card_color, foreground=text_color)
            stats.pack(anchor="w", padx=10, pady=(0, 10))

            # KORREKTUR: Verwendet jetzt die neue Helfermethode
            for widget in [card, title, stats]:
                widget.bind("<Button-1>", lambda e, subject_id=sid: self._go_to_set_select(subject_id))
                widget.bind("<Button-3>", lambda e, subject_id=sid: self.create_context_menu(e, subject_id, 'subject'))
            
            col = (col + 1) % max_cols
            if col == 0:
                row += 1
            
        utils.bind_mouse_scroll(self.tiles_frame, self.canvas)

    def create_subject_popup(self):
        """Öffnet ein Dialogfenster, um ein neues Fach zu erstellen."""
        name = custom_dialogs.ask_string_themed(self, "Neues Fach", "Wie soll das neue Fach heißen?", self.controller)
        if name:
            new_id = str(uuid.uuid4())
            self.controller.data[new_id] = {"name": name, "color": constants.DEFAULT_COLOR, "sets": {}}
            self.controller.data_manager.save_data(self.controller.data)
            self.refresh_view()
            
    def rename_item(self, sid, item_type):
        """Benennt ein Fach um."""
        old_name = self.controller.data[sid]["name"]
        new_name = custom_dialogs.ask_string_themed(self, "Umbenennen", f"Neuer Name für '{old_name}':", self.controller)
        if new_name:
            self.controller.data[sid]["name"] = new_name
            self.controller.data_manager.save_data(self.controller.data)
            self.after(10, self.refresh_view)
            
    def change_item_color(self, sid, item_type, hex_code):
        """Ändert die Farbe eines Faches."""
        self.controller.data[sid]["color"] = hex_code
        self.controller.data_manager.save_data(self.controller.data)
        self.after(10, self.refresh_view)
        
    def delete_item(self, sid, item_type):
        """Löscht ein Fach und alle zugehörigen Inhalte."""
        name = self.controller.data[sid]["name"]
        if messagebox.askyesno("Löschen", f"Soll das Fach '{name}' und alle zugehörigen Inhalte wirklich gelöscht werden?", icon='warning', default='no'):
            del self.controller.data[sid]
            self.controller.data_manager.save_data(self.controller.data)
            self.after(10, self.refresh_view)
