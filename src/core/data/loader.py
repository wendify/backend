import config

from core.data import csv_handler


def load_csv():
    csv_path = config.FILE_STORAGE_PATH + "/erzeuger.csv"
    csv_handler.download(csv_path, config.SMARD_DOWNLOAD_URL)
    pd_frame = csv_handler.parse(csv_path)
