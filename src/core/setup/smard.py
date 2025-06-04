import os
import pandas as pd
import config
from core.data import loader
from core.logger import logger


class Smard:
    def __init__(self):
        self.df = None
        self.erzeuger = []


        pickle_path = config.FILE_STORAGE_PATH + "/smard_object.pkl"

        # Wenn Pickle existiert → direkt laden
        if os.path.exists(pickle_path):
            self.df = pd.read_pickle(pickle_path)
            logger.info("Pickle geladen.")
            return

        self.df = loader.load_csv()

        self.df.to_pickle(pickle_path)
        logger.info("Pickle neu erstellt.")


    # def create_erzeuger(self):

