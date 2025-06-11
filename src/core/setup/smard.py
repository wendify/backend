import logging
import pickle

import pandas
from pandas.core.interchange.dataframe_protocol import DataFrame

import config
from core.data import loader
from core.datenreihe import Datenreihe
from core.erzeuger import Erzeuger
from core.types import ErzeugerArt


class Smard:
	def __init__(self) -> None:
		# Wenn Pickle existiert, direkt laden
		if config.ENVIRONMENT == "prod" and config.PICKLE_FILE.exists():
			with open(config.PICKLE_FILE, "rb") as file:
				loaded = pickle.load(file)

			logging.info(f"Pickle geladen: {config.PICKLE_FILE}")

			self.__dict__.update(loaded.__dict__)
			return

		# Objekt neu aufbauen
		self.erzeuger: list[Erzeuger] = []
		installiert_tmp, realisiert_tmp = loader.load_csv()
		self.installiert: DataFrame = installiert_tmp
		self.realisiert: DataFrame = realisiert_tmp

		# Baue Erzeuger
		self.create_erzeuger()

		# Pickle speichern
		if config.ENVIRONMENT == "prod":
			with open(config.PICKLE_FILE, "wb") as file:
				pickle.dump(self, file)

			logging.info(f"Pickle gespeichert: {config.PICKLE_FILE}")

	def create_erzeuger(self) -> None:
		for art in ErzeugerArt:
			df_installiert = self.installiert[["Datum von", "Datum bis", art]]
			df_realisiert = self.realisiert[["Datum von", "Datum bis", art]]

			installiert = Datenreihe(art, df_installiert)
			realisiert = Datenreihe(art, df_realisiert)
			erzeuger = Erzeuger(art, installiert, realisiert)

			self.erzeuger.append(erzeuger)

	def get_erzeuger(self, art: ErzeugerArt) -> Erzeuger:
		try:
			return next(e for e in self.erzeuger if e.art == art)
		except StopIteration:
			logging.error(f"Erzeuger nicht gefunden: {art}")
			raise KeyError
