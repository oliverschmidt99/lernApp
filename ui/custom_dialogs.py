import tkinter as tk
from tkinter import simpledialog, ttk
import constants

class CustomAskString(simpledialog.Dialog):
    """
    Ein benutzerdefiniertes Dialogfeld, das das askstring-Verhalten nachahmt,
    aber das Anwendungs-Theme respektiert.
    """
    def __init__(self, parent, title, prompt, controller, **kwargs):
        self.controller = controller
        self.prompt_text = prompt
        super().__init__(parent, title=title)

    def body(self, master):
        """Erstellt den Hauptteil des Dialogs."""
        theme_name = self.controller.current_theme.get()
        colors = constants.THEMES[theme_name]
        
        # KORREKTUR: Stellt sicher, dass das gesamte Dialogfenster die Theme-Farbe erhält.
        self.config(bg=colors['bg'])
        master.config(bg=colors['bg'])

        self.label = ttk.Label(master, text=self.prompt_text, justify=tk.LEFT)
        self.label.pack(pady=(10, 5), padx=10)
        self.entry = ttk.Entry(master, width=40)
        self.entry.pack(pady=(0, 10), padx=10)
        
        return self.entry 

    def buttonbox(self):
        """Erstellt die OK- und Abbrechen-Buttons."""
        box = ttk.Frame(self)
        
        w = ttk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = ttk.Button(box, text="Abbrechen", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()

    def apply(self):
        """Wird aufgerufen, wenn der Benutzer OK klickt."""
        self.result = self.entry.get()

# Eine Hilfsfunktion, um den neuen Dialog einfacher aufzurufen
def ask_string_themed(parent, title, prompt, controller):
    dialog = CustomAskString(parent, title=title, prompt=prompt, controller=controller)
    return dialog.result
