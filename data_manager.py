import json
import os
import time
import random
import shutil

# Importiert die Konstante IMAGE_DIR aus unserer neuen constants.py Datei
from constants import IMAGE_DIR

class DataManager:
    """Verwaltet das Laden und Speichern der JSON-Daten sowie das Kopieren von Bildern."""
    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(IMAGE_DIR):
            os.makedirs(IMAGE_DIR)

    def load_data(self):
        """Lädt die Daten aus der JSON-Datei."""
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Gibt ein leeres Dictionary zurück, wenn die Datei nicht existiert oder fehlerhaft ist.
            return {}

    def save_data(self, data):
        """Speichert die übergebenen Daten in die JSON-Datei."""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def copy_image_to_datastore(self, image_path):
        """
        Kopiert eine Bilddatei in den IMAGE_DIR Ordner der Anwendung
        und gibt den neuen Pfad zurück. Verhindert doppeltes Kopieren.
        """
        if not image_path or not os.path.exists(image_path):
            return None
            
        # Verhindert das erneute Kopieren, wenn das Bild bereits im Datenspeicher ist
        if os.path.dirname(os.path.abspath(image_path)) == os.path.abspath(IMAGE_DIR):
            return image_path
            
        filename = os.path.basename(image_path)
        # Erzeugt einen einzigartigen Dateinamen, um Überschreibungen zu vermeiden
        unique_filename = f"{int(time.time())}_{random.randint(100,999)}_{filename}"
        destination_path = os.path.join(IMAGE_DIR, unique_filename)
        try:
            shutil.copy(image_path, destination_path)
            return destination_path
        except Exception as e:
            print(f"Fehler beim Kopieren des Bildes: {e}")
            return None
