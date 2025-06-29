import tkinter as tk
from tkinter import ttk

# Importiert Konstanten und Hilfsfunktionen aus dem Hauptverzeichnis
import constants
import utils

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
        bg_color = constants.THEMES[self.controller.current_theme.get()]["bg"]

        # Canvas für scrollbaren Inhalt
        self.canvas = tk.Canvas(self.content_frame, borderwidth=0, highlightthickness=0, bg=bg_color)
        self.scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=self.canvas.yview)
        self.tiles_frame = ttk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.create_window((0, 0), window=self.tiles_frame, anchor="nw")
        self.tiles_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Bindet das Scroll-Event an den gesamten Inhaltsbereich, nicht nur die Kacheln.
        utils.bind_mouse_scroll(self.content_frame, self.canvas)

    def create_context_menu(self, event, item_id, item_type):
        """Erstellt ein Kontextmenü für Kacheln (Rechtsklick)."""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Namen ändern", command=lambda: self.rename_item(item_id, item_type))
        color_menu = tk.Menu(menu, tearoff=0)
        for name, hex_code in constants.PASTEL_COLORS.items():
            color_menu.add_command(label=name, background=hex_code, command=lambda h=hex_code: self.change_item_color(item_id, item_type, h))
        menu.add_cascade(label="Farbe ändern", menu=color_menu)
        menu.add_separator()
        menu.add_command(label="Löschen", command=lambda: self.delete_item(item_id, item_type), foreground="red")
        menu.tk_popup(event.x_root, event.y_root)

    # Platzhalter-Methoden, die in den Unterklassen implementiert werden müssen
    def rename_item(self, item_id, item_type): pass
    def change_item_color(self, item_id, item_type, hex_code): pass
    def delete_item(self, item_id, item_type): pass
    def refresh_view(self): pass
