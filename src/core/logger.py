import logging
from logging.handlers import RotatingFileHandler
import config

logger = logging.getLogger()


def setup_logger() -> logging.Logger:
    logger.setLevel(config.LOG_LEVEL)

    # File Handler (mit Rotation)
    file_handler = RotatingFileHandler(config.LOG_FILE, maxBytes=5_000_000, backupCount=3)
    file_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-5s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # Optional: Konsole (für Debug/Entwicklung)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)

    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
