import logging
import sys

import coloredlogs

import config


def setup() -> None:
	logger = logging.getLogger()

	# Trennzeile in Datei schreiben (vor neuen Logeinträgen)
	with open(config.LOG_FILE, "a", encoding="utf-8") as f:
		f.write("-" * 60 + "\n")

	# Farbige Console prints
	coloredlogs.install(
		level='DEBUG',
		logger=logger,
		stream=sys.stdout,
		fmt='[%(levelname)s] %(message)s',
		level_styles={
			'debug': {'color': 'blue'},
			'info': {'color': 'green'},
			'warning': {'color': 'yellow'},
			'error': {'color': 'red'},
			'critical': {'color': 'red', 'bold': True}
		},
		field_styles={
			'levelname': None,
			'asctime': None,
			'message': None
		}
	)

	# Log-Datei
	file_formatter = logging.Formatter(
		"[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S",
	)

	file_handler = logging.FileHandler(config.LOG_FILE)
	file_handler.setFormatter(file_formatter)

	# Logger anpassen
	logger.addHandler(file_handler)
	logger.setLevel(config.LOG_LEVEL)
