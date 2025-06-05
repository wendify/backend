import logging

import config


def setup() -> None:
	logger = logging.getLogger()

	# Konsole
	console_formatter = logging.Formatter("[%(levelname)s] %(message)s")

	console_handler = logging.StreamHandler()
	console_handler.setFormatter(console_formatter)

	# Log-Datei
	file_formatter = logging.Formatter(
		"[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S",
	)

	file_handler = logging.FileHandler(config.LOG_FILE)
	file_handler.setFormatter(file_formatter)

	# Logger anpassen
	logger.addHandler(console_handler)
	logger.addHandler(file_handler)
	logger.setLevel(config.LOG_LEVEL)
