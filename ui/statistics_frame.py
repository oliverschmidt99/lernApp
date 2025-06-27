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
        
        ttk.Button(action_frame, text="Lernen", command=self._show_session_size_prompt).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Bearbeiten", command=self._edit_set).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Fortschritt zurücksetzen", style="Danger.TButton", command=self._reset_set_progress).pack(side="left", padx=5)

        ttk.Separator(self, orient='horizontal').pack(fill='x', pady=10)

        # --- Container für die Diagramme ---
        self.plot_container = ttk.Frame(self)
        self.plot_container.pack(fill='both', expand=True)

        self.update_plots()


    def _start_quiz(self, popup, mode, session_size=None):
        popup.destroy()
        callback = partial(self.controller.show_frame, QuizFrame, subject_id=self.subject_id, set_id=self.set_id, mode=mode, session_size=session_size)
        self.after(20, callback)

    def _edit_set(self):
        callback = partial(self.controller.show_frame, EditSetFrame, subject_id=self.subject_id, set_id=self.set_id)
        self.after(20, callback)
        
    def _show_session_size_prompt(self):
        """Zeigt einen Dialog zur Auswahl der Sitzungsgröße."""
        prompt = tk.Toplevel(self)
        prompt.title("Sitzungsgröße")
        prompt.transient(self)
        
        bg_color = constants.THEMES[self.controller.current_theme.get()]["bg"]
        prompt.config(bg=bg_color)
        
        ttk.Label(prompt, text="Wie viele Karten möchtest du lernen?", padding=20).pack()
        
        btn_frame = ttk.Frame(prompt, padding=10)
        btn_frame.pack()
        
        def start(size):
            self._start_quiz(prompt, 'spaced_repetition', session_size=size)

        ttk.Button(btn_frame, text="Alle fälligen", command=lambda: start(None)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="5", command=lambda: start(5)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="10", command=lambda: start(10)).pack(side="left", padx=5)

        prompt.update_idletasks()
        x = self.winfo_toplevel().winfo_x() + (self.winfo_toplevel().winfo_width() // 2) - (prompt.winfo_width() // 2)
        y = self.winfo_toplevel().winfo_y() + (self.winfo_toplevel().winfo_height() // 2) - (prompt.winfo_height() // 2)
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

        # --- Kuchendiagramm ---
        status_counts = Counter(t.get('sm_data', {}).get('status', 'new') for t in tasks)
        pie_labels = list(status_counts.keys())
        pie_sizes = list(status_counts.values())
        pie_colors = [constants.STATUS_COLORS.get(status, 'grey') for status in pie_labels]

        # KORREKTUR: Layout auf 2 Reihen, 1 Spalte geändert
        self.fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [1, 1]})
        self.fig.patch.set_facecolor(theme['bg'])

        ax1.pie(pie_sizes, labels=pie_labels, colors=pie_colors, autopct='%1.1f%%',
                startangle=90, textprops={'color': text_color})
        ax1.axis('equal')
        ax1.set_title('Aktueller Lernstatus', color=text_color)
        
        # --- Liniendiagramm Container ---
        line_chart_container = ttk.Frame(parent)
        line_chart_container.pack(fill='both', expand=True)
        
        # --- Dropdown für Liniendiagramm ---
        control_frame = ttk.Frame(line_chart_container)
        control_frame.pack(fill='x', pady=5)
        task_names = ["Gesamtübersicht"] + [task.get('name', 'Unbenannte Aufgabe') for task in self.tasks]
        task_var = tk.StringVar(value=task_names[0])
        ttk.Label(control_frame, text="Verlauf anzeigen für:").pack(side='left', padx=(0, 5))
        task_selector = ttk.Combobox(control_frame, textvariable=task_var, values=task_names, state='readonly', width=45)
        task_selector.pack(side='left', padx=5)

        def on_line_chart_select(event=None):
            selected_index = task_selector.current()
            if selected_index == -1: return
            
            history_data = []
            if selected_index == 0:
                 for task in self.tasks: history_data.extend(task.get('history', []))
            else:
                task = self.tasks[selected_index - 1]
                history_data = task.get('history', [])
            
            history_data.sort(key=lambda x: x.get('timestamp', 0))
            self._update_line_chart(ax2, history_data, theme)
            self.canvas.draw()

        task_selector.bind("<<ComboboxSelected>>", on_line_chart_select)

        # Initiales Zeichnen des Liniendiagramms
        initial_history = []
        for task in self.tasks: initial_history.extend(task.get('history', []))
        initial_history.sort(key=lambda x: x.get('timestamp', 0))
        self._update_line_chart(ax2, initial_history, theme)
        
        self.fig.tight_layout(pad=3.0)

        self.canvas = FigureCanvasTkAgg(self.fig, line_chart_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _update_line_chart(self, ax, history_data, theme):
        """Zeichnet nur das Liniendiagramm neu."""
        ax.clear()
        text_color = theme['fg']

        if history_data:
            attempts = range(1, len(history_data) + 1)
            quality_map = {'bad': 0, 'ok': 1, 'good': 2, 'perfect': 3}
            quality_scores = [quality_map.get(d.get('quality'), 0) for d in history_data]
            
            ax.set_facecolor(theme['card_bg'])
            ax.plot(attempts, quality_scores, marker='o', linestyle='-', color='tab:green')
            ax.set_xlabel('Lernsitzung (Versuch Nr.)', color=text_color)
            ax.set_ylabel('Bewertungsqualität', color=text_color)
            ax.tick_params(axis='y', colors=text_color)
            ax.tick_params(axis='x', colors=text_color)
            ax.spines['bottom'].set_color(text_color)
            ax.spines['left'].set_color(text_color)
            ax.spines['top'].set_color(text_color)
            ax.spines['right'].set_color(text_color)
            ax.set_yticks(list(quality_map.values()), labels=list(quality_map.keys()))
            ax.set_title("Fortschritt über die Zeit", color=text_color)
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        else:
            ax.set_title("Fortschritt über die Zeit", color=text_color)
            ax.text(0.5, 0.5, 'Keine Verlaufsdaten für diese Auswahl.', ha='center', va='center', color=text_color)
            ax.set_yticks([])
            ax.set_xticks([])
