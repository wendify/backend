import logging
import os

import coloredlogs

import config


# Führt das Setup für den Logger durch
def setup() -> None:
	# Root-Logger holen
	logger = logging.getLogger()

	# Trennzeile in Datei schreiben, falls existent
	if config.LOG_FILE.exists():
		with open(config.LOG_FILE, "r+") as file:
			lines = file.readlines()

			if lines and not lines[-1].startswith("-"):
				file.seek(0, os.SEEK_END)
				file.write("-" * 60 + "\n")

	# Farbige Logs in der Konsole installieren
	styles = {
		"debug": {"color": "blue"},
		"error": {"color": "red"},
		"info": {"color": "green"},
		"warning": {"color": "yellow"},
	}

	coloredlogs.install(fmt="[%(levelname)s] %(message)s", level_styles=styles)

	# Logs in der Log-Datei installieren
	format = "[%(asctime)s] [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s"
	formatter = logging.Formatter(format, datefmt="%Y-%m-%d %H:%M:%S")

	handler = logging.FileHandler(config.LOG_FILE)
	handler.setFormatter(formatter)

	# Logger anpassen
	logger.addHandler(handler)
	logger.setLevel(config.LOG_LEVEL)
