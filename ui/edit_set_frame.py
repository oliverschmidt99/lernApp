import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import uuid
import os
import shutil
import copy
from collections import deque

from tkinterdnd2 import DND_FILES
from PIL import Image, ImageTk, ImageGrab

from .base_frames import BasePage
import utils
import constants

# Prüft, ob ein Tool zum Zugriff auf die Zwischenablage für Bilder verfügbar ist
CLIPBOARD_TOOL_AVAILABLE = shutil.which('xclip') or shutil.which('wl-paste')

def _clean_dnd_path(path_string):
    """Bereinigt den Pfad, der von der Drag-and-Drop-Bibliothek übergeben wird."""
    if isinstance(path_string, tuple):
        path_string = path_string[0]
    # Entfernt überflüssige geschweifte Klammern, die manchmal auftreten
    if path_string.startswith('{') and path_string.endswith('}'):
        return path_string[1:-1]
    return path_string

def _save_pasted_image(image):
    """Speichert ein aus der Zwischenablage eingefügtes Bild temporär."""
    if image:
        temp_path = os.path.join(constants.IMAGE_DIR, f"paste_{uuid.uuid4()}.png")
        image.save(temp_path, 'PNG')
        return temp_path
    return None


class BaseTaskEditor(ttk.Frame):
    """
    Eine Basisklasse für den Editor, der das Erstellen und Bearbeiten
    von Aufgaben (Lernkarten) ermöglicht.
    """
    def __init__(self, parent, controller, subject_id, set_id):
        super().__init__(parent)
        self.controller = controller
        self.subject_id, self.set_id = subject_id, set_id

        # Initialisiert Listen für Bildpfade und Widgets
        self._task_image_full_paths = []
        self.subtask_widgets = []

        self._autosave_timer_id = None

        self.build_editor_ui(self)
        self.setup_buttons(self)

    def _select_all(self, event):
        """Helferfunktion, um den gesamten Text in einem Text-Widget mit Strg+A auszuwählen."""
        event.widget.tag_add('sel', '1.0', 'end')
        event.widget.mark_set('insert', '1.0')
        event.widget.see('insert')
        return 'break' # Verhindert, dass das Event weiter verarbeitet wird

    def build_editor_ui(self, parent):
        """Erstellt die Benutzeroberfläche des Editors."""
        colors = constants.THEMES[self.controller.current_theme.get()]

        ttk.Label(parent, text=self.get_title(), font=("Helvetica", 16, "bold")).pack(pady=10)

        # Eingabefeld für den Aufgabennamen
        name_frame = ttk.LabelFrame(parent, text="Aufgabenname")
        name_frame.pack(pady=(10, 0), padx=10, fill="x")
        self.task_name_entry = ttk.Entry(name_frame)
        self.task_name_entry.pack(pady=5, padx=5, fill="x")
        self.task_name_entry.bind("<KeyRelease>", self._schedule_autosave)

        # Textfeld für die Aufgabenbeschreibung
        desc_frame = ttk.LabelFrame(parent, text="Aufgabenbeschreibung")
        desc_frame.pack(pady=10, padx=10, fill="x")
        self.task_desc_text = tk.Text(desc_frame, height=4, wrap=tk.WORD, bg=colors["text_bg"], fg=colors["fg"], insertbackground=colors['fg'])
        self.task_desc_text.pack(pady=5, padx=5, fill="x", expand=True)
        self.task_desc_text.bind('<Control-v>', self._handle_paste_main) # Einfügen aus Zwischenablage
        self.task_desc_text.bind('<Control-a>', self._select_all) # Alles auswählen
        self.task_desc_text.bind("<KeyRelease>", self._schedule_autosave)

        # Bereich für Aufgabenbilder (inkl. Drag-and-Drop)
        task_images_container = ttk.LabelFrame(parent, text="Aufgabenbilder")
        task_images_container.pack(pady=10, padx=10, fill="x")
        self.task_images_frame = ttk.Frame(task_images_container)
        self.task_images_frame.pack(fill="x", padx=5, pady=5)

        img_drop_frame_task = ttk.Frame(task_images_container)
        img_drop_frame_task.pack(fill="x", expand=True, padx=5, pady=5)
        drop_zone_task = tk.Label(img_drop_frame_task, text="Bilder hierher ziehen oder auswählen...", relief="groove", borderwidth=2, padx=10, pady=10, background=colors["bg"], foreground=colors["fg"])
        drop_zone_task.pack(side="left", fill="x", expand=True)
        drop_zone_task.drop_target_register(DND_FILES)
        drop_zone_task.dnd_bind('<<Drop>>', self._on_drop_task_image)
        ttk.Button(img_drop_frame_task, text="...", command=self.select_task_image, width=4).pack(side="left", padx=10)

        # Eingabefeld für Tags
        tags_frame = ttk.LabelFrame(parent, text="Tags (mit Komma getrennt)")
        tags_frame.pack(pady=10, padx=10, fill="x")
        self.tags_entry = ttk.Entry(tags_frame)
        self.tags_entry.pack(pady=5, padx=5, fill="x")
        self.tags_entry.bind("<KeyRelease>", self._schedule_autosave)

        # Container für Unteraufgaben
        self.subtasks_frame = ttk.LabelFrame(parent, text="Unteraufgaben")
        self.subtasks_frame.pack(pady=10, padx=10, fill="x")

        ttk.Button(parent, text="+ Teilaufgabe hinzufügen", command=self.add_subtask_fields).pack(pady=5)

    def add_subtask_fields(self, subtask_data=None):
        """Fügt dynamisch Felder für eine neue Unteraufgabe hinzu."""
        subtask_data = subtask_data or {}
        colors = constants.THEMES[self.controller.current_theme.get()]

        # Container für eine einzelne Teilaufgabe
        container = tk.Frame(self.subtasks_frame, bg=colors.get("subtask_bg", colors["bg"]), bd=1, relief="sunken")
        container.pack(pady=5, fill="x", padx=5)

        label_text = f"Teilaufgabe {chr(97 + len(self.subtask_widgets))})"
        frame = ttk.LabelFrame(container, text=label_text)
        frame.pack(pady=5, fill="x", padx=5)

        # Löschen-Button für die Teilaufgabe
        delete_subtask_button = ttk.Button(frame, text="X", style="Danger.TButton", width=2)
        delete_subtask_button.place(relx=1.0, x=-5, y=-8, anchor="ne")

        # Eingabefelder für Frage und Lösung
        q_text = tk.Text(frame, height=2, wrap=tk.WORD, bg=colors["text_bg"], fg=colors["fg"], insertbackground=colors['fg'])
        q_text.pack(fill="x", padx=5, pady=5)
        q_text.insert("1.0", subtask_data.get("frage", ""))

        s_text = tk.Text(frame, height=2, wrap=tk.WORD, bg=colors["text_bg"], fg=colors["fg"], insertbackground=colors['fg'])
        s_text.pack(fill="x", padx=5, pady=5)
        s_text.insert("1.0", subtask_data.get("loesung", ""))

        # Bereich für Lösungsbilder
        solution_images_container = ttk.LabelFrame(frame, text="Lösungsbilder")
        solution_images_container.pack(pady=5, fill="x", padx=5)
        solution_images_frame = ttk.Frame(solution_images_container)
        solution_images_frame.pack(fill="x", padx=5, pady=5)

        # Sammelt alle Widgets einer Teilaufgabe in einem Dictionary
        widgets = { "question": q_text, "solution": s_text, "frame": container,
                    "image_paths": [p for p in subtask_data.get('bilder_loesung', []) if p],
                    "image_frame": solution_images_frame }

        # Bindet Events für Einfügen, Auswählen und Autosave
        paste_handler = lambda e, w=widgets: self._handle_paste_solution(e, w)
        q_text.bind('<Control-v>', paste_handler)
        s_text.bind('<Control-v>', paste_handler)
        q_text.bind('<Control-a>', self._select_all)
        s_text.bind('<Control-a>', self._select_all)
        q_text.bind("<KeyRelease>", self._schedule_autosave)
        s_text.bind("<KeyRelease>", self._schedule_autosave)

        # Drag-and-Drop für Lösungsbilder
        img_drop_frame_solution = ttk.Frame(solution_images_container)
        img_drop_frame_solution.pack(fill="x", expand=True, padx=5, pady=5)
        drop_zone_solution = tk.Label(img_drop_frame_solution, text="Lösungsbilder hierher ziehen...", relief="groove", borderwidth=2, padx=10, pady=10, background=colors["bg"], foreground=colors["fg"])
        drop_zone_solution.pack(side="left", fill="x", expand=True)
        drop_zone_solution.drop_target_register(DND_FILES)
        drop_zone_solution.dnd_bind('<<Drop>>', lambda e, w=widgets: self._on_drop_solution_image(e, w))
        ttk.Button(img_drop_frame_solution, text="...", command=lambda w=widgets: self.select_solution_image(w), width=4).pack(side="left", padx=10)


        delete_subtask_button.config(command=lambda w=widgets: self._delete_subtask(w))
        self.subtask_widgets.append(widgets)

        self._redraw_solution_images_ui(widgets)

    def _show_image_popup(self, path):
        """Öffnet ein Popup-Fenster, um ein Bild in voller Größe anzuzeigen."""
        if not path or not os.path.exists(path):
            messagebox.showwarning("Fehler", "Bildpfad ist ungültig oder die Datei existiert nicht.")
            return

        popup = tk.Toplevel(self)
        popup.title(os.path.basename(path))
        colors = constants.THEMES[self.controller.current_theme.get()]
        popup.configure(bg=colors['bg'])

        popup.bind("<Escape>", lambda e: popup.destroy())

        close_button = ttk.Button(popup, text="X", command=popup.destroy, style="Danger.TButton")
        close_button.pack(anchor="ne", padx=10, pady=10)

        try:
            img = Image.open(path)
            # Skaliert das Bild auf 80% der Bildschirmgröße
            screen_width = self.winfo_screenwidth() * 0.8
            screen_height = self.winfo_screenheight() * 0.8
            img.thumbnail((screen_width, screen_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            img_label_popup = ttk.Label(popup, image=photo)
            img_label_popup.image = photo
            img_label_popup.pack(padx=20, pady=(0, 20), expand=True, fill="both")

            # Zentriert das Popup auf dem Hauptfenster
            popup.update_idletasks()
            x = self.winfo_toplevel().winfo_x() + (self.winfo_toplevel().winfo_width() // 2) - (popup.winfo_width() // 2)
            y = self.winfo_toplevel().winfo_y() + (self.winfo_toplevel().winfo_height() // 2) - (popup.winfo_height() // 2)
            popup.geometry(f"+{int(x)}+{int(y)}")

        except Exception as e:
            popup.destroy()
            messagebox.showerror("Fehler", f"Bild konnte nicht geladen werden:\n{e}")

        popup.transient(self.winfo_toplevel())
        popup.grab_set()

    def _redraw_task_images_ui(self):
        """Zeichnet die Liste der Aufgabenbilder neu."""
        for widget in self.task_images_frame.winfo_children(): widget.destroy()
        for i, path in enumerate(p for p in self._task_image_full_paths if p):
            f = ttk.Frame(self.task_images_frame)
            f.pack(fill='x', pady=2)
            ttk.Button(f, text="X", width=2, style="Danger.TButton", command=lambda p=path: self._remove_task_image(p)).pack(side='right')
            label = ttk.Label(f, text=f"{i+1}: {os.path.basename(path)}", cursor="hand2")
            label.pack(side='left')
            label.bind("<Button-1>", lambda e, p=path: self._show_image_popup(p))

    def _redraw_solution_images_ui(self, widget_dict):
        """Zeichnet die Liste der Lösungsbilder für eine Teilaufgabe neu."""
        frame = widget_dict['image_frame']
        for widget in frame.winfo_children(): widget.destroy()
        for i, path in enumerate(p for p in widget_dict['image_paths'] if p):
            f = ttk.Frame(frame)
            f.pack(fill='x', pady=2)
            ttk.Button(f, text="X", width=2, style="Danger.TButton", command=lambda p=path, w=widget_dict: self._remove_solution_image(p, w)).pack(side='right')
            label = ttk.Label(f, text=f"{i+1}: {os.path.basename(path)}", cursor="hand2")
            label.pack(side='left')
            label.bind("<Button-1>", lambda e, p=path: self._show_image_popup(p))

    def _delete_subtask(self, widget_dict_to_delete):
        """Löscht eine Teilaufgabe aus der UI und der Datenstruktur."""
        widget_dict_to_delete['frame'].destroy()
        self.subtask_widgets.remove(widget_dict_to_delete)
        self._renumber_subtasks()
        self.autosave()

    def _renumber_subtasks(self):
        """Nummeriert die Teilaufgaben neu, nachdem eine gelöscht wurde."""
        for i, widget_dict in enumerate(self.subtask_widgets):
            # Greift auf das LabelFrame innerhalb des Containers zu
             label_frame = widget_dict['frame'].winfo_children()[0]
             label_frame.config(text=f"Teilaufgabe {chr(97 + i)})")


    def _add_task_image(self, path):
        """Fügt ein Bild zur Aufgabenbilderliste hinzu."""
        if path and path not in self._task_image_full_paths:
            self._task_image_full_paths.append(path)
            self._redraw_task_images_ui()
            self.autosave()

    def _remove_task_image(self, path_to_remove):
        """Entfernt ein Bild aus der Aufgabenbilderliste."""
        if path_to_remove in self._task_image_full_paths:
            self._task_image_full_paths.remove(path_to_remove)
            self._redraw_task_images_ui()
            self.autosave()

    def _add_solution_image(self, path, widget_dict):
        """Fügt ein Bild zur Lösungsbilderliste einer Teilaufgabe hinzu."""
        if path and path not in widget_dict['image_paths']:
            widget_dict['image_paths'].append(path)
            self._redraw_solution_images_ui(widget_dict)
            self.autosave()

    def _remove_solution_image(self, path_to_remove, widget_dict):
        """Entfernt ein Bild aus der Lösungsbilderliste einer Teilaufgabe."""
        if path_to_remove in widget_dict['image_paths']:
            widget_dict['image_paths'].remove(path_to_remove)
            self._redraw_solution_images_ui(widget_dict)
            self.autosave()

    def select_task_image(self):
        """Öffnet einen Dialog zur Auswahl von Aufgabenbildern."""
        paths = filedialog.askopenfilenames(title="Aufgaben-Bilder auswählen", filetypes=[("Bilddateien", "*.png *.jpg *.jpeg *.gif"), ("Alle Dateien", "*.*")])
        for path in paths: self._add_task_image(path)

    def select_solution_image(self, widget_dict):
        """Öffnet einen Dialog zur Auswahl von Lösungsbildern."""
        paths = filedialog.askopenfilenames(title="Lösungs-Bilder auswählen", filetypes=[("Bilddateien", "*.png *.jpg *.jpeg *.gif"), ("Alle Dateien", "*.*")])
        for path in paths: self._add_solution_image(path, widget_dict)

    def _on_drop_task_image(self, event):
        """Verarbeitet das Ablegen von Dateien auf der Aufgaben-Drop-Zone."""
        paths = self.tk.splitlist(event.data)
        for path in paths: self._add_task_image(_clean_dnd_path(path))

    def _on_drop_solution_image(self, event, widget_dict):
        """Verarbeitet das Ablegen von Dateien auf der Lösungs-Drop-Zone."""
        paths = self.tk.splitlist(event.data)
        for path in paths: self._add_solution_image(_clean_dnd_path(path), widget_dict)

    def _handle_paste_main(self, event):
        """Verarbeitet das Einfügen von Bildern in das Haupt-Beschreibungsfeld."""
        if not CLIPBOARD_TOOL_AVAILABLE: return
        try:
            clipboard_content = ImageGrab.grabclipboard()
            if isinstance(clipboard_content, Image.Image): # Bild in der Zwischenablage
                path = _save_pasted_image(clipboard_content)
                self._add_task_image(path)
                return "break"
            elif isinstance(clipboard_content, list) and clipboard_content: # Dateipfad in der Zwischenablage
                path = clipboard_content[0]
                if os.path.exists(path):
                    self._add_task_image(path)
                    return "break"
        except: pass # Fehler ignorieren, wenn kein Bild in der Zwischenablage ist

    def _handle_paste_solution(self, event, widget_dict):
        """Verarbeitet das Einfügen von Bildern in die Felder der Teilaufgaben."""
        if not CLIPBOARD_TOOL_AVAILABLE: return
        try:
            clipboard_content = ImageGrab.grabclipboard()
            if isinstance(clipboard_content, Image.Image):
                path = _save_pasted_image(clipboard_content)
                self._add_solution_image(path, widget_dict)
                return "break"
            elif isinstance(clipboard_content, list) and clipboard_content:
                path = clipboard_content[0]
                if os.path.exists(path):
                    self._add_solution_image(path, widget_dict)
                    return "break"
        except: pass

    def collect_data(self):
        """Sammelt alle Daten aus den Eingabefeldern und gibt sie als Dictionary zurück."""
        task_name = self.task_name_entry.get().strip()
        task_desc = self.task_desc_text.get("1.0", "end-1c").strip()

        if not task_name:
             # messagebox.showwarning("Fehler", "Der Aufgabenname darf nicht leer sein.")
             return None

        tags = [tag.strip() for tag in self.tags_entry.get().split(',') if tag.strip()]

        # Kopiert Bilder in den internen Speicher und speichert die neuen Pfade
        task_images = [self.controller.data_manager.copy_image_to_datastore(p) for p in self._task_image_full_paths]

        subtasks = []
        for widgets in self.subtask_widgets:
            q = widgets["question"].get("1.0", "end-1c").strip()
            if not q: continue # Überspringt leere Teilaufgaben
            s = widgets["solution"].get("1.0", "end-1c").strip()
            imgs = [self.controller.data_manager.copy_image_to_datastore(p) for p in widgets['image_paths']]
            subtasks.append({"frage": q, "loesung": s, "bilder_loesung": imgs})

        return { "name": task_name, "beschreibung": task_desc, "tags": tags,
                 "bilder_aufgabe": task_images, "unteraufgaben": subtasks }

    # Abstrakte Methoden, die in der Unterklasse implementiert werden müssen
    def get_title(self): raise NotImplementedError
    def setup_buttons(self, parent): raise NotImplementedError


class EditSetFrame(BasePage):
    """
    Seite zum Bearbeiten eines Lernsets. Zeigt eine Liste aller Aufgaben
    links und den Editor für die ausgewählte Aufgabe rechts.
    """
    def __init__(self, parent, controller, subject_id, set_id):
        self.init_args = {"subject_id": subject_id, "set_id": set_id}
        super().__init__(parent, controller)
        self.subject_id, self.set_id, self.current_task_id = subject_id, set_id, None

        self.set_nav_title(f"Bearbeite: {controller.data[subject_id]['sets'][set_id]['name']}")
        self.add_nav_button("← Zurück zu den Lernsets", self.go_to_set_select_frame)

        # Geteilte Ansicht (PanedWindow) für Liste und Editor
        paned_window = ttk.PanedWindow(self.content_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # --- LINKE SPALTE (Aufgabenliste) ---
        left_frame = ttk.Frame(paned_window, width=300)
        paned_window.add(left_frame, weight=1)

        colors = constants.THEMES[controller.current_theme.get()]
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill='both', expand=True, pady=5)
        ttk.Label(list_frame, text="Aufgaben", font=("Helvetica", 12, "bold")).pack()
        self.task_listbox = tk.Listbox(list_frame, bg=colors["list_bg"], fg=colors["list_fg"], selectbackground=colors["button_bg"], font=("Helvetica", 10), selectforeground=utils.get_readable_text_color(colors["button_bg"]))
        self.task_listbox.pack(fill=tk.BOTH, expand=True)
        self.task_listbox.bind("<<ListboxSelect>>", self.on_task_select)
        ttk.Button(left_frame, text="+ Neue Aufgabe erstellen", command=self.create_new_task).pack(fill='x', pady=5)

        # --- RECHTE SPALTE (Scrollbarer Editor) ---
        editor_canvas_container = ttk.Frame(paned_window)
        paned_window.add(editor_canvas_container, weight=3)

        self.editor_canvas = tk.Canvas(editor_canvas_container, borderwidth=0, highlightthickness=0, bg=colors['bg'])
        editor_scrollbar = ttk.Scrollbar(editor_canvas_container, orient="vertical", command=self.editor_canvas.yview)
        self.editor_container = ttk.Frame(self.editor_canvas) # Frame für den eigentlichen Editor-Inhalt

        self.editor_canvas.configure(yscrollcommand=editor_scrollbar.set)
        editor_scrollbar.pack(side="right", fill="y")
        self.editor_canvas.pack(side="left", fill="both", expand=True)

        canvas_window = self.editor_canvas.create_window((0, 0), window=self.editor_container, anchor="nw")

        # Konfiguration für das Scrollen
        self.editor_container.bind("<Configure>", lambda e: self.editor_canvas.configure(scrollregion=self.editor_canvas.bbox("all")))
        self.editor_canvas.bind("<Configure>", lambda e: self.editor_canvas.itemconfig(canvas_window, width=e.width))

        self.refresh_task_list()
        self.show_placeholder()

    def go_to_set_select_frame(self):
        """Navigiert zurück zur Lernset-Auswahl."""
        from .set_select_frame import SetSelectFrame
        self.controller.show_frame(SetSelectFrame, subject_id=self.subject_id)

    def show_placeholder(self):
        """Zeigt eine Nachricht an, wenn keine Aufgabe ausgewählt ist."""
        for widget in self.editor_container.winfo_children(): widget.destroy()
        ttk.Label(self.editor_container, text="Wähle eine Aufgabe aus oder erstelle eine neue.", font=("Helvetica", 12)).pack(pady=50)

    def refresh_task_list(self, keep_selection=False):
        """Aktualisiert die Liste der Aufgaben in der Listbox."""
        original_selection_index = self.task_listbox.curselection()

        self.task_listbox.delete(0, tk.END)
        self.tasks = self.controller.data[self.subject_id]["sets"][self.set_id].get("tasks", [])
        for i, task in enumerate(self.tasks):
            preview = task.get('name', 'Unbenannte Aufgabe')
            self.task_listbox.insert(tk.END, f" {preview}")

        if keep_selection and original_selection_index:
            self.task_listbox.selection_set(original_selection_index)

    def on_task_select(self, event=None):
        """Wird aufgerufen, wenn eine Aufgabe in der Liste ausgewählt wird."""
        indices = self.task_listbox.curselection()
        if not indices: return
        task_data = self.tasks[indices[0]]
        self.current_task_id = task_data.get('id')
        if not self.current_task_id:
            messagebox.showerror("Fehler", "Diese Aufgabe hat keine gültige ID.")
            return
        self.load_editor(task_data)

    def create_new_task(self):
        """Erstellt eine neue, leere Aufgabe und lädt sie im Editor."""
        new_task = {
            "id": str(uuid.uuid4()), "name": "Neue Aufgabe", "beschreibung": "",
            "tags": [], "bilder_aufgabe": [], "unteraufgaben": [],
            "history": [], "sm_data": {} # Initialisiert leere Lerndaten
        }
        self.controller.data[self.subject_id]["sets"][self.set_id]["tasks"].append(new_task)
        self.controller.data_manager.save_data(self.controller.data)
        self.refresh_task_list()

        self.task_listbox.selection_clear(0, tk.END)
        self.task_listbox.selection_set(tk.END) # Wählt die neue Aufgabe aus
        self.load_editor(new_task)

    def load_editor(self, task_data):
        """Lädt den Editor für eine neue oder bestehende Aufgabe."""
        for widget in self.editor_container.winfo_children(): widget.destroy()
        editor = self.TaskEditor(self.editor_container, self.controller, self.subject_id, self.set_id, task_data, self)
        editor.pack(fill="both", expand=True)
        # Binden des Mausrad-Scrollens für den neuen Editor-Inhalt
        utils.bind_mouse_scroll(editor, self.editor_canvas)

    class TaskEditor(BaseTaskEditor):
        """
        Innere Klasse für den eigentlichen Editor. Erbt von BaseTaskEditor
        und implementiert die Speicher-, Lade- und Löschlogik.
        """
        def __init__(self, parent, controller, subject_id, set_id, task_data, edit_set_frame):
            self.task_data = copy.deepcopy(task_data) # Arbeitet auf einer Kopie
            self.edit_set_frame = edit_set_frame # Referenz auf den übergeordneten Frame

            # Stacks für Undo/Redo Funktionalität
            self.undo_stack = deque(maxlen=21)
            self.redo_stack = deque(maxlen=20)
            self._is_undo_redo_action = False

            super().__init__(parent, controller, subject_id, set_id)
            if self.task_data:
                self._load_data_into_widgets(self.task_data)
                # Speichert den initialen Zustand für die Undo-Funktion
                initial_state = self.collect_data()
                if initial_state:
                    self._push_undo_state(initial_state)
            else:
                self.add_subtask_fields()

        def _load_data_into_widgets(self, data):
            """Befüllt die Editor-Felder mit den Daten einer Aufgabe."""
            self.task_name_entry.delete(0, tk.END)
            self.task_name_entry.insert(0, data.get('name', ''))

            self.task_desc_text.delete("1.0", tk.END)
            self.task_desc_text.insert("1.0", data.get('beschreibung', ''))

            self.tags_entry.delete(0, tk.END)
            self.tags_entry.insert(0, ", ".join(data.get('tags', [])))

            self._task_image_full_paths = list(data.get('bilder_aufgabe', []))
            self._redraw_task_images_ui()

            # Löscht alte Teilaufgaben-Widgets und erstellt sie neu
            for w in self.subtask_widgets: w['frame'].destroy()
            self.subtask_widgets.clear()
            for subtask_data in data.get('unteraufgaben', []):
                self.add_subtask_fields(subtask_data)

        def get_title(self):
            return "Aufgabe bearbeiten"

        def setup_buttons(self, parent):
            """Richtet die Buttons (Speichern, Löschen, Undo, Redo) und die Statusanzeige ein."""
            btn_frame = ttk.Frame(parent)
            btn_frame.pack(side="bottom", fill="x", pady=10, padx=10)

            self.undo_button = ttk.Button(btn_frame, text="Rückgängig", command=self.undo, state="disabled")
            self.undo_button.pack(side="left")
            self.redo_button = ttk.Button(btn_frame, text="Wiederholen", command=self.redo, state="disabled")
            self.redo_button.pack(side="left", padx=5)

            ttk.Button(btn_frame, text="Speichern", command=self.autosave).pack(side="left", padx=5)

            self.status_label = ttk.Label(btn_frame, text="")
            self.status_label.pack(side="left", padx=5)

            ttk.Button(btn_frame, text="Löschen", style="Danger.TButton", command=self.delete_task).pack(side="right")

        def _update_undo_redo_state(self):
            """Aktiviert oder deaktiviert die Undo/Redo-Buttons je nach Stack-Größe."""
            self.undo_button.config(state="normal" if len(self.undo_stack) > 1 else "disabled")
            self.redo_button.config(state="normal" if self.redo_stack else "disabled")

        def _push_undo_state(self, state_data):
            """Fügt den aktuellen Zustand zum Undo-Stack hinzu."""
            if not self._is_undo_redo_action:
                # Fügt nur hinzu, wenn sich der Zustand geändert hat
                if not self.undo_stack or self.undo_stack[-1] != state_data:
                    self.undo_stack.append(copy.deepcopy(state_data))
                    self.redo_stack.clear() # Neue Änderung löscht den Redo-Stack
            self._update_undo_redo_state()

        def undo(self):
            """Macht die letzte Änderung rückgängig."""
            if len(self.undo_stack) > 1:
                self._is_undo_redo_action = True
                self.redo_stack.append(self.undo_stack.pop())
                previous_state = self.undo_stack[-1]
                self._load_data_into_widgets(previous_state)
                self.save_changes(is_autosave=True, from_undo_redo=True)
                self._is_undo_redo_action = False
                self._update_undo_redo_state()

        def redo(self):
            """Wiederholt die letzte rückgängig gemachte Änderung."""
            if self.redo_stack:
                self._is_undo_redo_action = True
                state_to_restore = self.redo_stack.pop()
                self.undo_stack.append(state_to_restore)
                self._load_data_into_widgets(state_to_restore)
                self.save_changes(is_autosave=True, from_undo_redo=True)
                self._is_undo_redo_action = False
                self._update_undo_redo_state()

        def _schedule_autosave(self, event=None):
            """Plant das automatische Speichern nach einer kurzen Verzögerung."""
            if self._autosave_timer_id:
                self.after_cancel(self._autosave_timer_id)
            self._autosave_timer_id = self.after(1500, self.autosave) # 1.5 Sekunden

        def autosave(self):
            """Wrapper für das Speichern, der als "automatisch" gekennzeichnet ist."""
            self.save_changes(is_autosave=True)

        def save_changes(self, is_autosave=False, from_undo_redo=False):
            """Speichert die Änderungen an der Aufgabe in der Haupt-Datenstruktur."""
            updated_data = self.collect_data()
            if updated_data is None: return

            if not from_undo_redo:
                self._push_undo_state(updated_data)

            task_list = self.controller.data[self.subject_id]["sets"][self.set_id].setdefault("tasks", [])

            for i, task in enumerate(task_list):
                if task.get('id') == self.task_data['id']:
                    # Behält wichtige Metadaten der Original-Aufgabe bei
                    updated_data['id'] = self.task_data['id']
                    updated_data['history'] = task.get('history', [])
                    updated_data['sm_data'] = task.get('sm_data', {})
                    task_list[i] = updated_data
                    self.task_data = updated_data # Aktualisiert die lokale Kopie
                    break

            self.controller.data_manager.save_data(self.controller.data)

            if is_autosave:
                self.status_label.config(text="Gespeichert!")
                self.after(2000, lambda: self.status_label.config(text=""))

            self.edit_set_frame.refresh_task_list(keep_selection=True)
            self._update_undo_redo_state()

        def delete_task(self):
            """Löscht die aktuell bearbeitete Aufgabe."""
            if messagebox.askyesno("Löschen", "Soll diese Aufgabe wirklich endgültig gelöscht werden?", icon='warning', default='no'):
                self.edit_set_frame.show_placeholder() # Zeigt Platzhalter im Editor-Bereich an

                task_list = self.controller.data[self.subject_id]["sets"][self.set_id]["tasks"]
                task_list[:] = [t for t in task_list if t.get('id') != self.task_data['id']]
                self.controller.data_manager.save_data(self.controller.data)

                self.edit_set_frame.refresh_task_list()
