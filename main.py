import tkinter as tk
from tkinter import ttk, messagebox
import copy

# Import für Drag-and-Drop-Funktionalität
from tkinterdnd2 import TkinterDnD

# Importiert die zentralen Komponenten aus den neuen Modulen
import constants
from data_manager import DataManager
from ui.start_frame import StartFrame
import utils # Import für get_readable_text_color

class LernApp(TkinterDnD.Tk):
    """
    Hauptklasse der Anwendung. Dient als Controller, der die Frames verwaltet,
    die Daten hält und das Theme anwendet.
    """
    def __init__(self):
        super().__init__()
        self.title("Lern-Anwendung")
        self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.data_manager = DataManager(constants.DATA_FILE)
        self.data = self.data_manager.load_data()

        # Führt eine einmalige, sichere Datenmigration durch, falls nötig.
        self._migrate_data_to_v2()

        saved_theme = self.data.get("settings", {}).get("theme", "light")
        self.current_theme = tk.StringVar(value=saved_theme)
        self.current_theme.trace_add("write", self.apply_theme)

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.apply_theme()
        self.show_frame(StartFrame)

    def _migrate_data_to_v2(self):
        """
        Prüft, ob die Daten im alten Format sind und wandelt sie sicher in das neue
        Format mit Bilderlisten um. Fügt eine Versionsnummer hinzu, um eine
        erneute Ausführung zu verhindern.
        """
        settings = self.data.setdefault("settings", {})
        if settings.get("data_version") == 2:
            return

        print("Führe Datenmigration zu v2 durch...")
        migrated_data = copy.deepcopy(self.data)
        needs_saving = False

        for subject_id, subject_data in migrated_data.items():
            if subject_id == "settings" or not isinstance(subject_data, dict):
                continue
            for set_id, set_data in subject_data.get("sets", {}).items():
                if not isinstance(set_data, dict): continue
                for task in set_data.get("tasks", []):
                    if not isinstance(task, dict): continue

                    # Migriert Aufgabenbilder
                    if 'bilder_aufgabe' not in task and 'bild_aufgabe' in task:
                        single_image = task.pop('bild_aufgabe', None)
                        task['bilder_aufgabe'] = [single_image] if single_image else []
                        needs_saving = True

                    # Migriert Lösungsbilder in Unteraufgaben
                    for subtask in task.get("unteraufgaben", []):
                         if not isinstance(subtask, dict): continue
                         if 'bilder_loesung' not in subtask and 'bild_loesung' in subtask:
                            single_image = subtask.pop('bild_loesung')
                            subtask['bilder_loesung'] = [single_image] if single_image else []
                            needs_saving = True

        if needs_saving:
            migrated_data["settings"]["data_version"] = 2
            self.data = migrated_data
            self.data_manager.save_data(self.data)
            print("Datenmigration abgeschlossen und gespeichert.")


    def apply_theme(self, *args):
        """Wendet das ausgewählte Farbschema (Theme) auf die gesamte Anwendung an."""
        theme_name = self.current_theme.get()
        colors = constants.THEMES[theme_name]
        feedback_colors = constants.FEEDBACK_COLORS[theme_name]

        self.style = ttk.Style(self)
        self.style.theme_use('clam')

        self.configure(bg=colors["bg"])
        self.style.configure(".", background=colors["bg"], foreground=colors["fg"], fieldbackground=colors["text_bg"])
        self.style.configure("TFrame", background=colors["bg"])
        self.style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("TButton", padding=6, relief="flat", background=colors["button_bg"], foreground=colors["fg"])
        self.style.map("TButton", background=[("active", colors["fg"])], foreground=[("active", colors["bg"])])

        self.style.configure("TEntry", fieldbackground=colors["text_bg"], insertcolor=colors["fg"], foreground=colors["fg"])

        self.style.configure("Danger.TButton", background=colors["danger_bg"], foreground=colors["danger_fg"])
        self.style.map("Danger.TButton", background=[("active", colors["fg"])], foreground=[("active", colors["bg"])])

        self.style.configure("Header.TLabel", font=("Helvetica", 18, "bold"), background=colors["nav_bg"], foreground=colors["header_fg"])
        self.style.configure("CardTitle.TLabel", font=("Helvetica", 14, "bold"))
        self.style.configure("CardStats.TLabel", font=("Helvetica", 9))
        self.style.configure("TLabelframe", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("TLabelframe.Label", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("Nav.TFrame", background=colors["nav_bg"])

        # Globale Definition der Stile für Feedback-Buttons
        if theme_name == "dark":
            fg_color = feedback_colors['foreground']
            self.style.configure("Bad.TButton", background=feedback_colors['bad'], foreground=fg_color, padding=6, relief="flat")
            self.style.configure("OK.TButton", background=feedback_colors['ok'], foreground=fg_color, padding=6, relief="flat")
            self.style.configure("Good.TButton", background=feedback_colors['good'], foreground=fg_color, padding=6, relief="flat")
            self.style.configure("Perfect.TButton", background=feedback_colors['perfect'], foreground=fg_color, padding=6, relief="flat")
        else: # Light theme
            self.style.configure("Bad.TButton", background=feedback_colors['bad'], foreground=utils.get_readable_text_color(feedback_colors['bad']), padding=6, relief="flat")
            self.style.configure("OK.TButton", background=feedback_colors['ok'], foreground=utils.get_readable_text_color(feedback_colors['ok']), padding=6, relief="flat")
            self.style.configure("Good.TButton", background=feedback_colors['good'], foreground=utils.get_readable_text_color(feedback_colors['good']), padding=6, relief="flat")
            self.style.configure("Perfect.TButton", background=feedback_colors['perfect'], foreground=utils.get_readable_text_color(feedback_colors['perfect']), padding=6, relief="flat")


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

# --- Startpunkt der Anwendung ---
if __name__ == "__main__":
    app = LernApp()
    app.mainloop()
