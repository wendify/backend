import os
import pathlib
import sys

import dotenv


# Lädt Env-Wert mit vorgegebenen erlaubten Werten
def getenv(key: str, *values: str) -> str:
	value = os.getenv(key)

	if value is None:
		sys.exit(f"[ENV] Variable nicht gefunden: {key}")

	if len(values) > 0 and value not in values:
		sys.exit(f"[ENV] Variable ungültig: {key}, erlaubt sind: {', '.join(values)}")

	return value


# Lädt Env-Wert als Ganzzahl
def getint(key: str) -> int:
	value = getenv(key)

	try:
		return int(value)
	except ValueError:
		sys.exit(f"[ENV] Variable keine Ganzzahl: {key}")


# Env-Datei laden
dotenv.load_dotenv()

# Verzeichnisse
BASE_DIR = pathlib.Path(__file__).parent.parent
DATA_DIR = BASE_DIR.joinpath("data")
LOGS_DIR = BASE_DIR.joinpath("logs")

# Daten
INSTALLIERT_FILE = DATA_DIR.joinpath("installiert.csv")
REALISIERT_FILE = DATA_DIR.joinpath("realisiert.csv")
VERBRAUCHT_FILE = DATA_DIR.joinpath("verbraucht.csv")

# SMARD-Module
INSTALLIERT_IDS = 186, 188, 189, 194, 198, 207, 3792, 4072, 4073, 4074, 4075, 4076
REALISIERT_IDS = 1223, 1224, 1225, 1226, 1227, 1228, 4066, 4067, 4068, 4069, 4070, 4071
VERBRAUCHT_IDS = 410, 4359, 4387, 5140

# FastAPI-Konfiguration
API_HOST = getenv("API_HOST")
API_PORT = getint("API_PORT")

# Logging
LOG_FILE = LOGS_DIR.joinpath("backend.log")
LOG_LEVEL = getenv("LOG_LEVEL")

# Sonstiges
ENORM_EXTRAPOLATION_MODE = getenv("ENORM_EXTRAPOLATION_MODE", "daily", "last", "yearly")
ENVIRONMENT = getenv("ENVIRONMENT", "dev", "prod")
PICKLE_FILE = DATA_DIR.joinpath("smard.pkl")
SMARD_URL = getenv("SMARD_URL")

# Verzeichnisse erstellen
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
