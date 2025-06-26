import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator
import time

# Relative Importe
from .base_frames import BasePage

# Absolute Importe
import constants

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
        self.add_nav_button("← Zurück zu den Lernsets", self.go_to_set_select_frame)

        control_frame = ttk.Frame(self.content_frame)
        control_frame.pack(fill='x', pady=5)

        self.tasks = controller.data[subject_id]["sets"][set_id].get("tasks", [])
        
        task_names = ["Gesamtübersicht"] + [task.get('name', 'Unbenannte Aufgabe') for task in self.tasks]
        self.task_var = tk.StringVar(value=task_names[0])

        ttk.Label(control_frame, text="Anzeigen für:").pack(side='left', padx=(0, 5))
        self.task_selector = ttk.Combobox(control_frame, textvariable=self.task_var, values=task_names, state='readonly', width=45)
        self.task_selector.pack(side='left', padx=5)
        self.task_selector.bind("<<ComboboxSelected>>", self.on_task_selected)
        
        ttk.Button(control_frame, text="Fortschritt zurücksetzen", command=self.reset_progress, style="Danger.TButton").pack(side='right', padx=5)

        self.plot_container = ttk.Frame(self.content_frame)
        self.plot_container.pack(fill='both', expand=True)

        self.on_task_selected()

    def go_to_set_select_frame(self):
        """Navigiert sicher zurück zum SetSelectFrame."""
        from .set_select_frame import SetSelectFrame
        self.controller.show_frame(SetSelectFrame, subject_id=self.subject_id)

    def on_task_selected(self, event=None):
        """Wird aufgerufen, wenn eine andere Aufgabe im Dropdown-Menü ausgewählt wird."""
        selected_index = self.task_selector.current()
        if selected_index == -1: return 
        if selected_index == 0:
            self.update_plots()
        else:
            task = self.tasks[selected_index - 1]
            self.update_plots(task_id=task.get('id'))

    def update_plots(self, task_id=None):
        """Aktualisiert die Diagramme basierend auf der Auswahl."""
        for widget in self.plot_container.winfo_children():
            widget.destroy()
        if self.fig:
            plt.close(self.fig)

        history_data = []
        if task_id:
            for task in self.tasks:
                if task.get('id') == task_id:
                    history_data = task.get('history', [])
                    break
        else:
            for task in self.tasks:
                history_data.extend(task.get('history', []))
        
        history_data.sort(key=lambda x: x.get('timestamp', 0))

        if not history_data:
            ttk.Label(self.plot_container, text="Noch keine Lerndaten für diese Auswahl vorhanden.").pack(pady=20)
        else:
            self.create_plots(history_data)

    def reset_progress(self):
        """Setzt den Lernfortschritt für die ausgewählte Aufgabe oder das gesamte Set zurück."""
        selected_index = self.task_selector.current()
        if selected_index == -1: return
        
        tasks_to_reset = []
        message = ""

        if selected_index == 0:
            message = "Möchtest du wirklich den gesamten Lernfortschritt für dieses Set zurücksetzen?"
            tasks_to_reset = self.tasks
        else:
            task = self.tasks[selected_index - 1]
            task_name = task.get('name', 'diese Aufgabe')
            message = f"Möchtest du wirklich den Lernfortschritt für die Aufgabe '{task_name}' löschen?"
            tasks_to_reset = [task]

        if messagebox.askyesno("Fortschritt zurücksetzen", message, icon='warning', default='no'):
            now = time.time()
            for task in tasks_to_reset:
                # Setzt die Lernhistorie und den Spaced-Repetition-Status zurück
                task['history'] = []
                task.setdefault('sm_data', {})['status'] = 'new'
                task['sm_data']['next_review_at'] = now
                task['sm_data']['consecutive_good'] = 0

            self.controller.data_manager.save_data(self.controller.data)
            self.on_task_selected() # Aktualisiert die Diagramm-Ansicht

    def create_plots(self, data):
        """Erstellt die Matplotlib-Diagramme und bettet sie in Tkinter ein."""
        theme = constants.THEMES[self.controller.current_theme.get()]
        plt.style.use('seaborn-v0_8-darkgrid' if self.controller.current_theme.get() == 'dark' else 'seaborn-v0_8-whitegrid')

        attempts = range(1, len(data) + 1)
        quality_map = {'bad': 0, 'ok': 1, 'good': 2, 'perfect': 3}
        quality_scores = [quality_map.get(d.get('quality', 'bad'), 0) for d in data]

        self.fig, ax1 = plt.subplots(figsize=(10, 6), tight_layout=True)
        self.fig.patch.set_facecolor(theme['bg'])

        ax1.set_facecolor(theme['card_bg'])
        ax1.set_xlabel('Lernsitzung (Versuch Nr.)', color=theme['fg'])
        ax1.set_ylabel('Bewertungsqualität', color=theme['fg'])
        ax1.plot(attempts, quality_scores, marker='o', linestyle='-', color='tab:green', label='Qualität')
        ax1.tick_params(axis='y', colors=theme['fg'])
        ax1.tick_params(axis='x', colors=theme['fg'])
        ax1.spines['bottom'].set_color(theme['fg'])
        ax1.spines['left'].set_color(theme['fg'])
        ax1.spines['top'].set_color(theme['fg'])
        ax1.spines['right'].set_color(theme['fg'])
        ax1.xaxis.label.set_color(theme['fg'])
        ax1.set_yticks(list(quality_map.values()), labels=list(quality_map.keys()))

        ax1.set_title("Lernfortschritt über die Zeit", color=theme['fg'])
        ax1.xaxis.set_major_locator(MaxNLocator(integer=True))
        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, self.plot_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
