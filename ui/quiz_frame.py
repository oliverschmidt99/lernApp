import tkinter as tk
from tkinter import ttk, messagebox
import os
import re
import time
import random
from collections import deque
from PIL import Image, ImageTk
import datetime

from .base_frames import BasePage
import utils
import constants # Importiert die zentrale Konstantendatei

class ProgressIndicator(ttk.Frame):
    """Ein visueller Fortschrittsbalken, der den Lernstatus der Karten als Kreise anzeigt."""
    def __init__(self, parent, display_tasks, theme_colors, current_task_id):
        super().__init__(parent, height=25)
        self.display_tasks = display_tasks
        self.theme_colors = theme_colors
        self.current_task_id = current_task_id

        self.canvas = tk.Canvas(self, height=25, bg=theme_colors['bg'], highlightthickness=0)
        self.canvas.pack(fill="x", expand=True, padx=5, pady=5)
        self.canvas.bind("<Configure>", self.update_progress)

    def update_progress(self, event=None):
        """Zeichnet den Fortschrittsbalken basierend auf dem aktuellen Zustand der Aufgaben."""
        self.canvas.delete("all")
        if not self.display_tasks: return

        # Trennt Karten in "gelernt" und "zu lernen"
        mastered_tasks = [t for t in self.display_tasks if t.get('sm_data', {}).get('status') in ['mastered', 'perfect']]
        learning_tasks = [t for t in self.display_tasks if t.get('sm_data', {}).get('status') not in ['mastered', 'perfect']]

        # Verschiebt die aktuelle Karte an den Anfang der "zu lernen"-Liste
        try:
            current_task_index = next(i for i, t in enumerate(learning_tasks) if t.get('id') == self.current_task_id)
            current_task_obj = learning_tasks.pop(current_task_index)
            learning_tasks.insert(0, current_task_obj)
        except StopIteration:
            pass # Aktuelle Karte nicht in der Lernliste (z.B. wenn sie die letzte war)

        ordered_tasks = mastered_tasks + learning_tasks

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        num_tasks = len(ordered_tasks)
        if num_tasks == 0: return

        # Berechnet die Größe und Position der Kreise
        diameter = min(canvas_height - 6, 18)
        padding = 6
        total_width_needed = num_tasks * (diameter + padding)

        start_x = padding
        if total_width_needed < canvas_width:
             start_x = (canvas_width - total_width_needed) / 2 # Zentriert die Kreise

        y0 = (canvas_height - diameter) / 2
        y1 = y0 + diameter

        for i, task in enumerate(ordered_tasks):
            status = task.get('sm_data', {}).get('status', 'new')
            color = constants.STATUS_COLORS.get(status, "grey")

            # Hebt die aktuelle Karte mit einem dickeren Rand hervor
            outline_color = color
            outline_width = 1
            if self.current_task_id and task.get('id') == self.current_task_id:
                outline_color = self.theme_colors['fg']
                outline_width = 3

            x0 = start_x + i * (diameter + padding)
            x1 = x0 + diameter
            self.canvas.create_oval(x0, y0, x1, y1, fill=color, outline=outline_color, width=outline_width)


class ImageGallery(ttk.Frame):
    """Ein Widget zur Anzeige einer Bildergalerie mit Navigationsbuttons."""
    def __init__(self, parent, image_paths, theme_colors):
        super().__init__(parent)
        self.image_paths = [path for path in image_paths if path and os.path.exists(path)]
        self.theme_colors = theme_colors
        self.current_image_index = 0
        self._photo_references = [] # Wichtig, um Referenzen auf die Bilder zu halten

        if not self.image_paths: return

        self.image_label = ttk.Label(self, cursor="hand2")
        self.image_label.pack(pady=5)
        self.image_label.bind("<Button-1>", self.open_fullscreen_view)

        nav_frame = ttk.Frame(self)
        self.nav_frame = nav_frame
        nav_frame.pack()

        self.prev_button = ttk.Button(nav_frame, text="< Vor", command=self.show_previous_image)
        self.prev_button.pack(side="left", padx=5)
        self.status_label = ttk.Label(nav_frame, text="")
        self.status_label.pack(side="left", padx=5)
        self.next_button = ttk.Button(nav_frame, text="Nächstes >", command=self.show_next_image)
        self.next_button.pack(side="left", padx=5)

        self.show_image()

    def open_fullscreen_view(self, event=None):
        """Öffnet das aktuell angezeigte Bild in einem großen Popup-Fenster."""
        if not self.image_paths: return
        path = self.image_paths[self.current_image_index]

        popup = tk.Toplevel(self)
        popup.title(os.path.basename(path))
        popup.configure(bg=self.theme_colors['bg'])
        popup.bind("<Escape>", lambda e: popup.destroy())

        close_button = ttk.Button(popup, text="X", command=popup.destroy, style="Danger.TButton")
        close_button.pack(anchor="ne", padx=10, pady=10)

        try:
            img = Image.open(path)
            screen_width = self.winfo_screenwidth() * 0.8
            screen_height = self.winfo_screenheight() * 0.8
            img.thumbnail((screen_width, screen_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            img_label_popup = ttk.Label(popup, image=photo)
            img_label_popup.image = photo # Referenz behalten
            img_label_popup.pack(padx=20, pady=(0, 20), expand=True, fill="both")

            popup.update_idletasks()
            x = self.winfo_toplevel().winfo_x() + (self.winfo_toplevel().winfo_width() // 2) - (popup.winfo_width() // 2)
            y = self.winfo_toplevel().winfo_y() + (self.winfo_toplevel().winfo_height() // 2) - (popup.winfo_height() // 2)
            popup.geometry(f"+{int(x)}+{int(y)}")
        except Exception as e:
            popup.destroy()
            messagebox.showerror("Fehler", f"Bild konnte nicht geladen werden:\n{e}")

        popup.transient(self.winfo_toplevel())
        popup.grab_set()

    def show_image(self):
        """Zeigt das Bild am aktuellen Index in der Galerie an."""
        if not self.image_paths: return
        path = self.image_paths[self.current_image_index]
        try:
            img = Image.open(path)
            img.thumbnail((450, 450), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._photo_references.append(photo)
            self.image_label.config(image=photo)
            self.update_status()
        except Exception as e:
            print(f"Fehler beim Laden des Bildes {path}: {e}")
            self.image_label.config(text="Bild konnte nicht geladen werden.")

    def update_status(self):
        """Aktualisiert die Statusanzeige (z.B. 'Bild 1 / 3') und die Navigationsbuttons."""
        total_images = len(self.image_paths)
        if total_images > 1:
            self.status_label.config(text=f"Bild {self.current_image_index + 1} / {total_images}")
            self.nav_frame.pack() # Zeigt Navigation nur bei mehreren Bildern
        else:
            self.nav_frame.pack_forget()

        self.prev_button.config(state="normal" if self.current_image_index > 0 else "disabled")
        self.next_button.config(state="normal" if self.current_image_index < len(self.image_paths) - 1 else "disabled")

    def show_previous_image(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.show_image()

    def show_next_image(self):
        if self.current_image_index < len(self.image_paths) - 1:
            self.current_image_index += 1
            self.show_image()


class QuizFrame(BasePage):
    """
    Der Lernmodus. Implementiert einen sequenziellen Modus und
    einen Modus mit Spaced Repetition.
    """
    def __init__(self, parent, controller, subject_id, set_id, mode, session_size=None):
        self.init_args = {"subject_id": subject_id, "set_id": set_id, "mode": mode, "session_size": session_size}
        super().__init__(parent, controller)
        self.subject_id, self.set_id, self.mode = subject_id, set_id, mode
        self._photo_references, self.current_task = [], None

        self.all_tasks = self.controller.data[subject_id]["sets"][set_id].get("tasks", [])

        # Wählt die Lernstrategie basierend auf dem 'mode' Parameter
        if self.mode == 'sequential':
            self.task_queue = deque(self.all_tasks)
            self.set_nav_title("Lernmodus: Sequenziell")
        else: # 'spaced_repetition'
            self.task_queue = self._build_spaced_repetition_queue(session_size)
            self.set_nav_title("Lernmodus: Spaced Repetition")

        self.add_nav_button("← Beenden & Speichern", self.finish_quiz)
        self.load_next_question()

    def _build_spaced_repetition_queue(self, session_size=None):
        """Erstellt eine priorisierte Warteschlange nur mit zu lernenden Karten."""
        now = time.time()
        # Stellt sicher, dass alle Karten die notwendigen Lerndaten haben
        for task in self.all_tasks:
            task.setdefault('sm_data', {'status': 'new', 'next_review_at': now, 'consecutive_good': 0})

        # Filtert Karten, die fällig und noch nicht gemeistert sind
        due_tasks = [t for t in self.all_tasks if t['sm_data']['next_review_at'] <= now and t['sm_data']['status'] not in ['mastered', 'perfect']]

        if not due_tasks: return deque()

        # Sortiert fällige Karten nach ihrem Status (neue/schlechte zuerst)
        due_tasks.sort(key=lambda t: constants.STATUS_INTERVALS.get(t['sm_data']['status'], 0))

        # Begrenzt die Sitzungsgröße, falls angegeben
        return deque(due_tasks[:session_size] if session_size else due_tasks)

    def _display_content(self, parent, text_content, image_paths):
        """Rendert Text, LaTeX-Formeln und Bilder in einem Frame."""
        colors = constants.THEMES[self.controller.current_theme.get()]
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill="x", anchor='nw', padx=5, pady=5)
        # Teilt den Text in regulären Text und LaTeX-Teile ($...$)
        parts = re.split(r'(\$.*?\$)', text_content)
        current_line_frame = ttk.Frame(text_frame)
        current_line_frame.pack(fill="x", anchor='nw')

        for part in parts:
            if part.startswith('$') and part.endswith('$'): # LaTeX-Formel
                formula = part[1:-1]
                bg_color = text_frame.cget('bg')
                latex_img = utils.render_latex(formula, fg=colors['fg'], bg=bg_color)
                if latex_img:
                    photo = ImageTk.PhotoImage(latex_img)
                    self._photo_references.append(photo)
                    ttk.Label(current_line_frame, image=photo, background=bg_color).pack(side="left", anchor='nw', pady=2)
            elif part: # Regulärer Text
                sub_parts = part.split('\n')
                for i, sub_part in enumerate(sub_parts):
                    if sub_part:
                        ttk.Label(current_line_frame, text=sub_part, wraplength=750, justify=tk.LEFT).pack(side="left", anchor='nw')
                    if i < len(sub_parts) - 1: # Nach einem Zeilenumbruch eine neue Zeile beginnen
                        current_line_frame = ttk.Frame(text_frame)
                        current_line_frame.pack(fill="x", anchor='w')
        if image_paths:
            gallery = ImageGallery(parent, image_paths, colors)
            gallery.pack(pady=5)

    def load_next_question(self):
        """Lädt die nächste Frage aus der Warteschlange."""
        self._photo_references.clear()
        if not self.task_queue:
            messagebox.showinfo("Fertig!", "Alle Aufgaben für diese Lernsitzung gemeistert!")
            self.finish_quiz()
            return
        self.current_task = self.task_queue.popleft()
        self.build_ui_for_current_question()

    def build_ui_for_current_question(self):
        """Baut die Benutzeroberfläche für die aktuell geladene Frage."""
        for widget in self.content_frame.winfo_children(): widget.destroy()
        if not self.current_task: return

        colors = constants.THEMES[self.controller.current_theme.get()]

        # Erstellt die Liste der Aufgaben für den Fortschrittsbalken
        mastered_tasks = [t for t in self.all_tasks if t.get('sm_data', {}).get('status') in ['mastered', 'perfect']]
        learning_tasks = [self.current_task] + list(self.task_queue)
        display_tasks = mastered_tasks + learning_tasks

        self.progress_indicator = ProgressIndicator(self.content_frame, display_tasks, colors, current_task_id=self.current_task.get('id'))
        self.progress_indicator.pack(fill="x", pady=(0, 10))

        # Haupt-Canvas für scrollbaren Inhalt
        self.main_canvas = tk.Canvas(self.content_frame, borderwidth=0, highlightthickness=0, bg=colors['bg'])
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=self.main_canvas.yview)
        main_frame = ttk.Frame(self.main_canvas)
        self.main_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.main_canvas.pack(side="left", fill="both", expand=True)
        canvas_window = self.main_canvas.create_window((0, 0), window=main_frame, anchor="nw")

        main_frame.bind("<Configure>", lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))
        self.main_canvas.bind("<Configure>", lambda e: self.main_canvas.itemconfig(canvas_window, width=e.width))
        utils.bind_mouse_scroll(self, self.main_canvas)

        # Zeigt die Hauptaufgabe an
        task_frame = ttk.LabelFrame(main_frame, text=self.current_task.get('name', 'Aufgabe'))
        task_frame.pack(fill="x", pady=10, padx=5)
        image_paths_task = self.current_task.get('bilder_aufgabe', [])
        self._display_content(task_frame, self.current_task['beschreibung'], image_paths_task)

        # Zeigt Tags und Status an
        info_frame = ttk.Frame(task_frame)
        info_frame.pack(fill='x', anchor='w', padx=5, pady=5)
        tags = self.current_task.get('tags', [])
        if tags: ttk.Label(info_frame, text=f"Tags: {', '.join(tags)}", font=("Helvetica", 9, "italic")).pack(side='left')
        if self.mode == 'spaced_repetition':
            status = self.current_task.get('sm_data', {}).get('status', 'new')
            ttk.Label(info_frame, text=f"  Status: {status.capitalize()}", font=("Helvetica", 9, "italic")).pack(side='left', padx=10)

        self.subtask_solution_widgets = {}

        # Zeigt die Teilaufgaben an
        for i, subtask in enumerate(self.current_task.get("unteraufgaben", [])):
            sub_frame = ttk.LabelFrame(main_frame, text=f"Teilaufgabe {chr(97 + i)}")
            sub_frame.pack(fill="x", padx=10, pady=5)
            self._display_content(sub_frame, subtask["frage"], [])

            action_frame = ttk.Frame(sub_frame)
            action_frame.pack(fill="x", padx=10, pady=5)

            self.subtask_solution_widgets[i] = {"container": None}
            ttk.Button(action_frame, text="Lösung anzeigen", command=lambda s=subtask, sf=sub_frame, i=i: self.toggle_solution(s, sf, i)).pack(side="left")

        self.feedback_frame = ttk.Frame(main_frame)
        self.feedback_frame.pack(pady=10)
        self.show_feedback_buttons()

    def show_feedback_buttons(self):
        """Zeigt die finalen Feedback-Buttons an."""
        for widget in self.feedback_frame.winfo_children(): widget.destroy()

        self.bad_button = ttk.Button(self.feedback_frame, text="😥 Schlecht", style="Bad.TButton", command=lambda: self.process_answer('bad'))
        self.bad_button.pack(side="left", padx=5)
        self.ok_button = ttk.Button(self.feedback_frame, text="🤔 OK", style="OK.TButton", command=lambda: self.process_answer('ok'))
        self.ok_button.pack(side="left", padx=5)
        self.good_button = ttk.Button(self.feedback_frame, text="😊 Gut", style="Good.TButton", command=lambda: self.process_answer('good'))
        self.good_button.pack(side="left", padx=5)
        self.perfect_button = ttk.Button(self.feedback_frame, text="😎 Perfekt", style="Perfect.TButton", command=lambda: self.process_answer('perfect'))
        self.perfect_button.pack(side="left", padx=5)

    def toggle_solution(self, subtask, parent_frame, subtask_index):
        """Zeigt die Lösung für eine Teilaufgabe an oder verbirgt sie."""
        widgets = self.subtask_solution_widgets[subtask_index]

        if widgets.get("container") and widgets["container"].winfo_exists():
            widgets["container"].destroy()
            widgets["container"] = None
        else:
            container = ttk.LabelFrame(parent_frame, text="Lösung")
            container.pack(fill="x", pady=5)
            image_paths_solution = subtask.get('bilder_loesung', [])
            self._display_content(container, subtask['loesung'], image_paths_solution)

            utils.bind_mouse_scroll(container, self.main_canvas)
            widgets["container"] = container

        self.update() # Wichtig, damit die Scrollregion korrekt berechnet wird
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

    def process_answer(self, quality):
        """Verarbeitet die Antwort des Benutzers."""
        self.save_performance(quality)
        if self.mode == 'spaced_repetition':
            self.update_task_spaced_repetition(quality)
        self.load_next_question()

    def update_task_spaced_repetition(self, quality):
        """Aktualisiert den Status und das nächste Review-Datum für eine Karte."""
        task_id = self.current_task.get('id')
        if not task_id: return

        for task in self.all_tasks:
            if task.get('id') == task_id:
                sm_data = task.setdefault('sm_data', {'status': 'new', 'consecutive_good': 0})
                current_status = sm_data.get('status', 'new')

                if quality == 'bad':
                    sm_data['status'] = 'bad'
                    sm_data['consecutive_good'] = 0
                    # Fügt die Karte zur Wiederholung weiter hinten in die Warteschlange ein
                    if len(self.task_queue) >= 2:
                        self.task_queue.insert(2, self.current_task)
                    else:
                        self.task_queue.append(self.current_task)
                elif quality == 'ok':
                    sm_data['status'] = 'ok'
                    sm_data['consecutive_good'] = 0
                    self.task_queue.append(self.current_task) # Wiederholt die Karte am Ende der Session
                elif quality == 'good':
                    if current_status == 'good':
                        sm_data['status'] = 'mastered'
                    else:
                        sm_data['status'] = 'good'
                        self.task_queue.append(self.current_task)
                elif quality == 'perfect':
                    sm_data['status'] = 'perfect'

                # Berechnet das nächste Fälligkeitsdatum
                interval_days = constants.STATUS_INTERVALS.get(sm_data['status'], 30)
                next_review_date = datetime.datetime.now() + datetime.timedelta(days=interval_days)
                sm_data['next_review_at'] = next_review_date.timestamp()
                break

    def save_performance(self, quality):
        """Speichert die Leistung für die allgemeine Statistik."""
        if not self.current_task or not self.current_task.get('id'): return

        for task in self.all_tasks:
            if task.get('id') == self.current_task.get('id'):
                history_entry = { "timestamp": time.time(), "quality": quality }
                task.setdefault('history', []).append(history_entry)
                break

    def finish_quiz(self):
        """Beendet den Lernmodus und kehrt zur Lernset-Auswahl zurück."""
        self.controller.data_manager.save_data(self.controller.data)
        self.current_task = None
        from .set_select_frame import SetSelectFrame
        self.controller.show_frame(SetSelectFrame, subject_id=self.subject_id)
