from core.logger import logger
from core.setup.smard import Smard


class App:
	def __init__(self):
		pass

	def run(self):
		logger.info("Starting")

		smard = Smard()

		print(smard.installiert.info())
		print(smard.realisiert.info())
