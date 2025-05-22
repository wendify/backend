from core.logger import logger
from core.data import loader


class App:
    def __init__(self):
        pass

    def run(self):
        logger.info('Starting')

        loader.load_csv()


