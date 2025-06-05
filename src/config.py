import os
import pathlib
import sys

import dotenv


def getenv(key: str, *values: str) -> str:
	value = os.getenv(key)

	if value is None:
		sys.exit(f"[ENV] Variable {key} nicht gefunden")
	elif len(values) > 0 and value not in values:
		sys.exit(f"[ENV] Variable {key} ungültig, erlaubt sind: {', '.join(values)}")
	else:
		return value


# Env-Datei laden
dotenv.load_dotenv()

# Verzeichnisse
BASE_DIR = pathlib.Path(__file__).parent.parent
DATA_DIR = BASE_DIR.joinpath("data")
LOGS_DIR = BASE_DIR.joinpath("logs")

# Daten
INSTALLIERT_FILE = DATA_DIR.joinpath("installiert.csv")
REALISIERT_FILE = DATA_DIR.joinpath("realisiert.csv")

# Logging
LOG_FILE = LOGS_DIR.joinpath("backend.log")
LOG_LEVEL = getenv("LOG_LEVEL")

# Sonstiges
ENVIRONMENT = getenv("ENVIRONMENT", "dev", "prod")
PICKLE_FILE = DATA_DIR.joinpath("smard.pkl")
SMARD_URL = getenv("SMARD_URL")

# Verzeichnisse erstellen
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
