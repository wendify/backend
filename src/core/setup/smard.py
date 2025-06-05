import logging
import pickle

import config
from core.data import loader
from core.erzeugerArt import ErzeugerArt
from core.erzeuger import Erzeuger
from core.datenreihe import Datenreihe


class Smard:
	def __init__(self):
		self.installiert = None
		self.realisiert = None
		self.erzeuger = []

		# Wenn Pickle existiert → direkt laden
		if config.ENVIRONMENT == "prod" and config.PICKLE_FILE.exists():
			with open(config.PICKLE_FILE, "rb") as f:
				loaded = pickle.load(f)
				self.__dict__.update(loaded.__dict__)
			logging.info("Pickle geladen.")
			return

		# Objekt neu aufbauen
		self.installiert, self.realisiert = loader.load_csv()

		# Baue erzeuger
		self.create_erzeuger()

		# Pickle speichern
		with open(config.PICKLE_FILE, "wb") as f:
			pickle.dump(self, f)
		logging.info("Pickle gespeichert.")

	def create_erzeuger(self):
		for art in ErzeugerArt:
			df_realisiert_art = self.realisiert[["Datum von", "Datum bis", art]]
			df_installiert_art = self.installiert[["Datum von", "Datum bis", art]]
			realisiert_datenreihe = Datenreihe(art, df_realisiert_art)
			installiert_datenreihe = Datenreihe(art, df_installiert_art)

			erzeuger = Erzeuger(art, realisiert_datenreihe, installiert_datenreihe, None)
			self.erzeuger.append(erzeuger)

	def get_erzeuger(self, art: ErzeugerArt) -> Erzeuger | None:
		return next((e for e in self.erzeuger if e.art == art), None)
