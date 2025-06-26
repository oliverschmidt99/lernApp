import tkinter as tk
from tkinter import ttk, messagebox
import uuid
import time
from functools import partial

# Relative Importe aus dem ui-Paket
from .base_frames import BaseTileFrame
from .edit_set_frame import EditSetFrame
from .quiz_frame import QuizFrame
from .statistics_frame import StatisticsFrame
# NEU: Import des benutzerdefinierten Dialogs
from . import custom_dialogs

# Absolute Importe
import utils
import constants

class SetSelectFrame(BaseTileFrame):
    """Zeigt alle Lernsets eines ausgewählten Fachs an."""
    def __init__(self, parent, controller, subject_id):
        super().__init__(parent, controller, subject_id=subject_id)
        
        self.subject_id = subject_id
        if subject_id not in self.controller.data:
            from .start_frame import StartFrame
            controller.show_frame(StartFrame)
            return
            
        self.subject_data = self.controller.data[subject_id]
        self.set_nav_title(f"Lernsets in: {self.subject_data['name']}")
        self.add_nav_button("← Zurück zu den Fächern", self.go_to_start_frame)
        self.add_nav_button("Neues Lernset", self.create_set_popup)
        self.refresh_view()

    def go_to_start_frame(self):
        """Navigiert sicher zurück zum StartFrame."""
        from .start_frame import StartFrame
        self.controller.show_frame(StartFrame)

    def refresh_view(self):
        """Zeichnet die Lernset-Kacheln neu."""
        for widget in self.tiles_frame.winfo_children():
            widget.destroy()
        
        sets = self.subject_data.get("sets", {})
        row, col, max_cols = 0, 0, 3

        sorted_sets = sorted(
            sets.items(),
            key=lambda item: item[1].get('name', '').lower()
        )

        for set_id, sdata in sorted_sets:
            card_color = sdata.get("color", constants.DEFAULT_COLOR)
            text_color = utils.get_readable_text_color(card_color)
            
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
            if col == 0:
                row += 1
        
        utils.bind_mouse_scroll(self.tiles_frame, self.canvas)

    def create_context_menu(self, event, item_id, item_type):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Namen ändern", command=lambda: self.rename_item(item_id, item_type))
        color_menu = tk.Menu(menu, tearoff=0)
        for name, hex_code in constants.PASTEL_COLORS.items():
            color_menu.add_command(label=name, background=hex_code, command=lambda h=hex_code: self.change_item_color(item_id, item_type, h))
        menu.add_cascade(label="Farbe ändern", menu=color_menu)
        menu.add_separator()
        menu.add_command(label="Fortschritt zurücksetzen", command=lambda: self._reset_set_progress(item_id))
        menu.add_separator()
        menu.add_command(label="Löschen", command=lambda: self.delete_item(item_id, item_type), foreground="red")
        menu.tk_popup(event.x_root, event.y_root)

    def create_set_popup(self):
        """Öffnet einen Dialog, um ein neues Lernset zu erstellen."""
        # KORREKTUR: Verwendet jetzt den neuen, thematisierten Dialog
        name = custom_dialogs.ask_string_themed(self, "Neues Lernset", "Name für das neue Lernset:", self.controller)
        if name:
            new_id = str(uuid.uuid4())
            self.controller.data[self.subject_id]["sets"][new_id] = {"name": name, "color": constants.DEFAULT_COLOR, "tasks": []}
            self.controller.data_manager.save_data(self.controller.data)
            self.refresh_view()

    def _start_quiz(self, popup, set_id, mode, session_size=None):
        popup.destroy()
        callback = partial(self.controller.show_frame, QuizFrame, subject_id=self.subject_id, set_id=set_id, mode=mode, session_size=session_size)
        self.after(20, callback)

    def _edit_set(self, popup, set_id):
        popup.destroy()
        callback = partial(self.controller.show_frame, EditSetFrame, subject_id=self.subject_id, set_id=set_id)
        self.after(20, callback)

    def _show_stats(self, popup, set_id):
        popup.destroy()
        callback = partial(self.controller.show_frame, StatisticsFrame, subject_id=self.subject_id, set_id=set_id)
        self.after(20, callback)
        
    def _show_session_size_prompt(self, parent_popup, set_id):
        """Zeigt einen Dialog zur Auswahl der Sitzungsgröße."""
        prompt = tk.Toplevel(self)
        prompt.title("Sitzungsgröße")
        prompt.transient(parent_popup)
        
        bg_color = constants.THEMES[self.controller.current_theme.get()]["bg"]
        prompt.config(bg=bg_color)
        
        ttk.Label(prompt, text="Wie viele Karten möchtest du lernen?", padding=20).pack()
        
        btn_frame = ttk.Frame(prompt, padding=10)
        btn_frame.pack()
        
        def start(size):
            prompt.destroy()
            self._start_quiz(parent_popup, set_id, 'spaced_repetition', session_size=size)

        ttk.Button(btn_frame, text="Alle fälligen", command=lambda: start(None)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="5", command=lambda: start(5)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="10", command=lambda: start(10)).pack(side="left", padx=5)

        prompt.update_idletasks()
        x = parent_popup.winfo_x() + (parent_popup.winfo_width() // 2) - (prompt.winfo_width() // 2)
        y = parent_popup.winfo_y() + (parent_popup.winfo_height() // 2) - (prompt.winfo_height() // 2)
        prompt.geometry(f"+{x}+{y}")
        prompt.grab_set()

    def show_options_popup(self, event, set_id):
        """Zeigt ein Popup-Menü mit Aktionen für ein Lernset."""
        popup = tk.Toplevel(self)
        popup.title("Aktion wählen")
        popup.transient(self.controller)

        content_frame = ttk.Frame(popup, padding=20)
        content_frame.pack(expand=True, fill='both')

        tasks = self.subject_data["sets"][set_id].get("tasks", [])
        has_history = any(t.get('history') for t in tasks if t.get('history'))

        learn_frame = ttk.LabelFrame(content_frame, text="Lernmodus wählen")
        learn_frame.pack(pady=5, fill='x', padx=5)

        ttk.Button(learn_frame, text="Sequenziell lernen",
                   command=lambda: self._start_quiz(popup, set_id, 'sequential'),
                   state="normal" if tasks else "disabled").pack(pady=5, fill='x')

        ttk.Button(learn_frame, text="Spaced Repetition",
                   command=lambda: self._show_session_size_prompt(popup, set_id),
                   state="normal" if tasks else "disabled").pack(pady=5, fill='x')

        ttk.Separator(content_frame, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Button(content_frame, text="Lernset bearbeiten", command=lambda: self._edit_set(popup, set_id)).pack(pady=5, fill='x')
        ttk.Button(content_frame, text="Lernfortschritt", command=lambda: self._show_stats(popup, set_id), state="normal" if has_history else "disabled").pack(pady=5, fill='x')
        
        ttk.Separator(content_frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Button(content_frame, text="Schließen", command=popup.destroy).pack(pady=5)
        
        popup.update_idletasks()
        
        x = self.controller.winfo_x() + (self.controller.winfo_width() // 2) - (popup.winfo_width() // 2)
        y = self.controller.winfo_y() + (self.controller.winfo_height() // 2) - (popup.winfo_height() // 2)
        popup.geometry(f"+{x}+{y}")
        
        popup.grab_set()
        popup.wait_window()

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


    def rename_item(self, set_id, item_type):
        """Benennt ein Lernset um."""
        old_name = self.controller.data[self.subject_id]["sets"][set_id]["name"]
        # KORREKTUR: Verwendet jetzt den neuen, thematisierten Dialog
        new_name = custom_dialogs.ask_string_themed(self, "Umbenennen", f"Neuer Name für '{old_name}':", self.controller)
        if new_name:
            self.controller.data[self.subject_id]["sets"][set_id]["name"] = new_name
            self.controller.data_manager.save_data(self.controller.data)
            self.refresh_view()

    def change_item_color(self, set_id, item_type, hex_code):
        """Ändert die Farbe eines Lernsets."""
        self.controller.data[self.subject_id]["sets"][set_id]["color"] = hex_code
        self.controller.data_manager.save_data(self.controller.data)
        self.refresh_view()

    def delete_item(self, set_id, item_type):
        """Löscht ein Lernset."""
        name = self.controller.data[self.subject_id]["sets"][set_id]["name"]
        if messagebox.askyesno("Löschen", f"Soll das Lernset '{name}' wirklich gelöscht werden?", icon='warning', default='no'):
            del self.controller.data[self.subject_id]["sets"][set_id]
            self.controller.data_manager.save_data(self.controller.data)
            self.refresh_view()
