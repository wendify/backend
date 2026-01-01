import logging
from datetime import datetime

import coloredlogs

import config


# Führt das Setup für den Logger durch
def setup() -> None:
	# Root-Logger holen
	logger = logging.getLogger()

	# Trennzeile mit momentanem Datum in Datei schreiben
	with open(config.LOG_FILE, "a") as file:
		print("-" * 40, datetime.now().replace(microsecond=0), "-" * 40, file=file)

	# Farbige Logs in der Konsole installieren
	coloredlogs.install(fmt="[%(levelname)s] %(message)s", level=config.LOG_LEVEL)

	# Logs in der Log-Datei installieren
	format = "[%(asctime)s] [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s"
	formatter = logging.Formatter(format, datefmt="%Y-%m-%d %H:%M:%S")

	handler = logging.FileHandler(config.LOG_FILE)
	handler.setFormatter(formatter)

	# Logger anpassen
	logger.addHandler(handler)
	logger.debug("Logger ist fertig eingerichtet!")
