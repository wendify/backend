from dotenv import load_dotenv
import os

# .env einmal beim Laden der config laden
load_dotenv()

# Zugriff auf Variablen
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_LEVEL = os.getenv("LOG_LEVEL")

SMARD_DOWNLOAD_URL = os.getenv("SMARD_DOWNLOAD_URL")

# Basisverzeichnis für Daten wie bspw. .csv-Dateien
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # --> config/
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))  # --> zurück zu /src

FILE_STORAGE_PATH = os.path.join(BASE_DIR, "data")

os.makedirs(FILE_STORAGE_PATH, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
