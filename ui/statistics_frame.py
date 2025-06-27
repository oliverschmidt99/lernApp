import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator
import time
from collections import Counter
from functools import partial

# Relative Importe
from . import custom_dialogs
from .quiz_frame import QuizFrame
from .edit_set_frame import EditSetFrame

# Absolute Importe
import constants

class StatisticsFrame(ttk.Frame):
    """
    Zeigt die Statistiken und Aktionen für ein ausgewähltes Lernset an.
    """
    def __init__(self, parent, controller, subject_id, set_id):
        super().__init__(parent)
        self.controller = controller
        self.subject_id = subject_id
        self.set_id = set_id
        
        set_data = controller.data[subject_id]["sets"][set_id]
        set_name = set_data.get("name", "Unbenanntes Set")
        self.tasks = set_data.get("tasks", [])

        # --- Top-Frame für Aktionen ---
        action_frame = ttk.Frame(self, padding=10)
        action_frame.pack(fill="x")
        
        ttk.Label(action_frame, text=set_name, font=("Helvetica", 16, "bold")).pack(side="left", padx=(0, 20))
        
        # KORREKTUR: Der "Lernen"-Button öffnet jetzt das Auswahl-Popup
        ttk.Button(action_frame, text="Lernen", command=self._show_learning_options_popup).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Bearbeiten", command=self._edit_set).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Fortschritt zurücksetzen", style="Danger.TButton", command=self._reset_set_progress).pack(side="left", padx=5)

        ttk.Separator(self, orient='horizontal').pack(fill='x', pady=10)

        # --- Container für die Diagramme ---
        self.plot_container = ttk.Frame(self)
        self.plot_container.pack(fill='both', expand=True)

        self.update_plots()

    # --- KORREKTUR: Neue Helferfunktionen für die Modus-Auswahl ---
    def _start_quiz(self, popup, mode, session_size=None):
        """Schließt das Popup und startet das Quiz mit den gewählten Optionen."""
        if popup:
            popup.destroy()
        # Verzögerung, um Tkinter Zeit zum Aufräumen zu geben
        callback = partial(self.controller.show_frame, QuizFrame, subject_id=self.subject_id, set_id=self.set_id, mode=mode, session_size=session_size)
        self.after(20, callback)

    def _show_learning_options_popup(self):
        """Zeigt ein Popup zur Auswahl des Lernmodus."""
        popup = tk.Toplevel(self)
        popup.title("Lernmodus wählen")
        popup.transient(self)

        content_frame = ttk.Frame(popup, padding=20)
        content_frame.pack(expand=True, fill='both')

        ttk.Button(content_frame, text="Sequenziell lernen",
                   command=lambda: self._start_quiz(popup, 'sequential'),
                   state="normal" if self.tasks else "disabled").pack(pady=5, fill='x')

        ttk.Button(content_frame, text="Spaced Repetition",
                   command=lambda: self._show_session_size_prompt(popup),
                   state="normal" if self.tasks else "disabled").pack(pady=5, fill='x')
        
        popup.update_idletasks()
        x = self.winfo_toplevel().winfo_x() + (self.winfo_toplevel().winfo_width() // 2) - (popup.winfo_width() // 2)
        y = self.winfo_toplevel().winfo_y() + (self.winfo_toplevel().winfo_height() // 2) - (popup.winfo_height() // 2)
        popup.geometry(f"+{x}+{y}")
        popup.grab_set()

    def _edit_set(self):
        callback = partial(self.controller.show_frame, EditSetFrame, subject_id=self.subject_id, set_id=self.set_id)
        self.after(20, callback)
        
    def _show_session_size_prompt(self, parent_popup):
        """Zeigt einen Dialog zur Auswahl der Sitzungsgröße."""
        now = time.time()
        for task in self.tasks:
            task.setdefault('sm_data', {'status': 'new', 'next_review_at': now})
        
        due_tasks = [t for t in self.tasks if t['sm_data']['next_review_at'] <= now and t['sm_data']['status'] not in ['mastered', 'perfect']]
        num_due_tasks = len(due_tasks)

        if num_due_tasks == 0:
            messagebox.showinfo("Keine Karten fällig", "Super! Es stehen aktuell keine Karten zur Wiederholung an.")
            return
            
        prompt = tk.Toplevel(self)
        prompt.title("Sitzungsgröße")
        prompt.transient(parent_popup)
        
        bg_color = constants.THEMES[self.controller.current_theme.get()]["bg"]
        prompt.config(bg=bg_color)
        
        ttk.Label(prompt, text=f"Wie viele der {num_due_tasks} fälligen Karten möchtest du lernen?", padding=15).pack()
        
        slider_var = tk.IntVar(value=min(10, num_due_tasks))
        
        value_frame = ttk.Frame(prompt, padding=(0,0,0,10))
        value_frame.pack()
        
        value_label = ttk.Label(value_frame, text=f"{slider_var.get()}", font=("Helvetica", 14, "bold"))
        value_label.pack()

        def update_label(value):
            value_label.config(text=f"{int(float(value))}")

        slider = ttk.Scale(prompt, from_=1, to=num_due_tasks, variable=slider_var, command=update_label, orient='horizontal')
        slider.pack(fill='x', expand=True, padx=20)
        
        btn_frame = ttk.Frame(prompt, padding=10)
        btn_frame.pack()
        
        def start():
            session_size = slider_var.get()
            prompt.destroy()
            self._start_quiz(parent_popup, 'spaced_repetition', session_size=session_size)

        ttk.Button(btn_frame, text="Lernsitzung starten", command=start).pack(pady=5)

        prompt.update_idletasks()
        x = parent_popup.winfo_x() + (parent_popup.winfo_width() // 2) - (prompt.winfo_width() // 2)
        y = parent_popup.winfo_y() + (parent_popup.winfo_height() // 2) - (prompt.winfo_height() // 2)
        prompt.geometry(f"+{x}+{y}")
        prompt.grab_set()

    def update_plots(self):
        """Aktualisiert die Diagramme."""
        for widget in self.plot_container.winfo_children():
            widget.destroy()
        
        if not self.tasks:
            ttk.Label(self.plot_container, text="Dieses Lernset enthält noch keine Aufgaben.").pack(pady=20)
            return

        self.create_plots(self.plot_container, self.tasks)


    def _reset_set_progress(self):
        """Setzt den Fortschritt für das gesamte aktuell angezeigte Set zurück."""
        set_name = self.controller.data[self.subject_id]["sets"][self.set_id]["name"]
        message = f"Möchtest du wirklich den gesamten Lernfortschritt für das Set '{set_name}' zurücksetzen?"
        if messagebox.askyesno("Fortschritt zurücksetzen", message, icon='warning', default='no'):
            now = time.time()
            for task in self.tasks:
                task['history'] = []
                task.setdefault('sm_data', {})['status'] = 'new'
                task['sm_data']['next_review_at'] = now
                task['sm_data']['consecutive_good'] = 0
            self.controller.data_manager.save_data(self.controller.data)
            self.update_plots()

    def create_plots(self, parent, tasks):
        """Erstellt die Matplotlib-Diagramme und bettet sie in Tkinter ein."""
        theme = constants.THEMES[self.controller.current_theme.get()]
        text_color = theme['fg']
        plt.style.use('seaborn-v0_8-darkgrid' if self.controller.current_theme.get() == 'dark' else 'seaborn-v0_8-whitegrid')

        status_counts = Counter(t.get('sm_data', {}).get('status', 'new') for t in tasks)
        labels = list(status_counts.keys())
        sizes = list(status_counts.values())
        colors = [constants.STATUS_COLORS.get(status, 'grey') for status in labels]

        self.fig = plt.figure(figsize=(12, 6), facecolor=theme['bg'])
        
        # Aufteilung in 1 Reihe, 2 Spalten
        gs = self.fig.add_gridspec(1, 2, width_ratios=[1, 1.5])
        ax1 = self.fig.add_subplot(gs[0])
        ax2 = self.fig.add_subplot(gs[1])

        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                startangle=90, textprops={'color': text_color})
        ax1.axis('equal')
        ax1.set_title('Aktueller Lernstatus', color=text_color)
        
        # Liniendiagramm
        history_data = []
        for task in tasks:
            history_data.extend(task.get('history', []))
        history_data.sort(key=lambda x: x.get('timestamp', 0))

        if history_data:
            attempts = range(1, len(history_data) + 1)
            quality_map = {'bad': 0, 'ok': 1, 'good': 2, 'perfect': 3}
            quality_scores = [quality_map.get(d.get('quality'), 0) for d in history_data]
            
            ax2.set_facecolor(theme['card_bg'])
            ax2.plot(attempts, quality_scores, marker='o', linestyle='-', color='tab:green')
            ax2.set_xlabel('Lernsitzung (Versuch Nr.)', color=text_color)
            ax2.set_ylabel('Bewertungsqualität', color=text_color)
            ax2.tick_params(axis='y', colors=text_color)
            ax2.tick_params(axis='x', colors=text_color)
            for spine in ax2.spines.values():
                spine.set_color(text_color)
            ax2.set_yticks(list(quality_map.values()), labels=list(quality_map.keys()))
            ax2.xaxis.set_major_locator(MaxNLocator(integer=True))
        else:
            ax2.text(0.5, 0.5, 'Keine Verlaufsdaten für dieses Set.', ha='center', va='center', color=text_color)
            ax2.set_yticks([])
            ax2.set_xticks([])
            ax2.set_facecolor(theme['bg'])
            for spine in ax2.spines.values():
                spine.set_visible(False)
        
        ax2.set_title("Fortschritt über die Zeit", color=text_color)

        self.fig.tight_layout(pad=3.0)

        canvas = FigureCanvasTkAgg(self.fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

