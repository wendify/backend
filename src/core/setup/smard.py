import os
import pickle

import pandas as pd
import config
from core.data import loader
from core.logger import logger
from core.erzeugerArt import ErzeugerArt
from core.erzeuger import Erzeuger
from core.datenreihe import Datenreihe


class Smard:
	def __init__(self):
		self.installiert = None
		self.realisiert = None
		self.erzeuger = []

		pickle_path = config.FILE_STORAGE_PATH + "/smard_object.pkl"

		# Wenn Pickle existiert → direkt laden
		if config.ENVIRONMENT_TYPE == "prod" and os.path.exists(pickle_path):
			with open(pickle_path, "rb") as f:
				loaded = pickle.load(f)
				self.__dict__.update(loaded.__dict__)
			logger.info("Pickle geladen.")
			return

		# Objekt neu aufbauen
		self.installiert, self.realisiert = loader.load_csv()

		# Baue erzeuger
		self.create_erzeuger()

		# Pickle speichern
		with open(pickle_path, "wb") as f:
			pickle.dump(self, f)
		logger.info("Pickle gespeichert.")

	def create_erzeuger(self):
		for art in ErzeugerArt:
			df_realisiert_art = self.realisiert[['Datum von', 'Datum bis', art]]
			df_installiert_art = self.installiert[['Datum von', 'Datum bis', art]]
			realisiert_datenreihe = Datenreihe(art, df_realisiert_art)
			installiert_datenreihe = Datenreihe(art, df_installiert_art)

			erzeuger = Erzeuger(art, realisiert_datenreihe, installiert_datenreihe, None)
			self.erzeuger.append(erzeuger)

	def get_erzeuger(self, art: ErzeugerArt) -> Erzeuger|None:
		return next((e for e in self.erzeuger if e.art == art), None)



