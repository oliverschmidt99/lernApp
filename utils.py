import io
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from PIL import Image

# Ein Set, um bereits gebundene Widgets zu speichern und Doppelungen zu vermeiden.
_already_bound = set()

def render_latex(formula, fontsize=12, dpi=300, fg='black', bg='white'):
    """Rendert eine LaTeX-Formel in ein Pillow-Bildobjekt."""
    try:
        # Ersetzungen für eine bessere Kompatibilität
        formula = formula.replace('\\le', '\\leq').replace('\\ge', '\\geq').replace('\\implies', '\\Rightarrow').replace('\\text', '\\mathrm')
        fig = Figure(figsize=(4, 1), dpi=dpi, facecolor=bg)
        fig.text(0, 0, f"${formula}$", usetex=False, fontsize=fontsize, color=fg)

        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=False, bbox_inches='tight', pad_inches=0.05, facecolor=bg)
        plt.close(fig) # Wichtig: Schließt die Figur, um Speicherlecks zu vermeiden
        buf.seek(0)
        img = Image.open(buf)
        return img
    except Exception as e:
        print(f"Fehler beim Rendern von LaTeX: {formula}\n{e}")
        return None

def get_readable_text_color(hex_bg_color):
    """Wählt Schwarz oder Weiß als Textfarbe für beste Lesbarkeit."""
    if not hex_bg_color or not hex_bg_color.startswith('#'):
        return "#000000"
    hex_bg_color = hex_bg_color[1:]
    try:
        r, g, b = (int(hex_bg_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#000000" if luminance > 0.5 else "#FFFFFF"
    except (ValueError, IndexError):
        return "#000000"

def bind_mouse_scroll(widget_to_bind, canvas_to_scroll):
    """
    Bindet das Mausrad-Event zuverlässig an ein Widget und alle seine Kinder,
    um einen bestimmten Canvas zu scrollen. Verhindert doppelte Bindungen.
    """
    def _on_mousewheel(event):
        # Passt die Scroll-Geschwindigkeit und -Richtung für verschiedene Plattformen an
        if event.num == 5 or event.delta < 0:
            canvas_to_scroll.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            canvas_to_scroll.yview_scroll(-1, "units")

    # Prüft, ob das Widget bereits gebunden wurde.
    if widget_to_bind not in _already_bound:
        widget_to_bind.bind("<MouseWheel>", _on_mousewheel)
        widget_to_bind.bind("<Button-4>", _on_mousewheel)
        widget_to_bind.bind("<Button-5>", _on_mousewheel)
        _already_bound.add(widget_to_bind)

    for child in widget_to_bind.winfo_children():
        # Rekursiver Aufruf bleibt, aber die innere Logik verhindert Doppelungen.
        bind_mouse_scroll(child, canvas_to_scroll)
