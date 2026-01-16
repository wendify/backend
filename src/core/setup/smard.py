import logging
import pickle

import config
from core.data import loader
from core.setup.erzeuger import Erzeuger, ErzeugerArt
from core.setup.verbraucher import Verbraucher, VerbraucherArt


# Die Sammlung aller SMARD-Daten in einem Objekt
class Smard:
	def __init__(self) -> None:
		# Wenn Pickle existiert, direkt laden
		if config.ENVIRONMENT == "prod" and config.PICKLE_FILE.exists():
			with open(config.PICKLE_FILE, "rb") as file:
				loaded = pickle.load(file)

			logging.info(f"Pickle geladen: {config.PICKLE_FILE}")

			self.__dict__.update(loaded.__dict__)
			return

		# Wenn Pickle nicht existiert, Objekt neu aufbauen
		logging.info("SMARD-Instanz wird aufgebaut...")

		# Rohe DataFrames aus den Dateien laden
		self.installiert, self.realisiert, self.verbraucht = loader.load_csv()

		# Erzeuger und Verbraucher neu aufbauen
		self.erzeuger: list[Erzeuger] = []
		self.verbraucher: list[Verbraucher] = []

		self.create_erzeuger()
		self.create_verbraucher()

		# Pickle speichern
		if config.ENVIRONMENT == "prod":
			with open(config.PICKLE_FILE, "wb") as file:
				pickle.dump(self, file)

			logging.info(f"Pickle gespeichert: {config.PICKLE_FILE}")

	# Erstellt alle nötigen Verbraucher
	def create_erzeuger(self) -> None:
		for art in ErzeugerArt:
			installiert = self.installiert[["Datum von", "Datum bis", art]]
			realisiert = self.realisiert[["Datum von", "Datum bis", art]]
			erzeuger = Erzeuger(art, installiert, realisiert)

			self.erzeuger.append(erzeuger)

	# Erstellt alle nötigen Verbraucher
	def create_verbraucher(self) -> None:
		for art in VerbraucherArt:
			verbraucht = self.verbraucht[["Datum von", "Datum bis", art]]
			verbraucher = Verbraucher(art, verbraucht)

			self.verbraucher.append(verbraucher)

	# Holt den Erzeuger mit der angegebenen Art
	def get_erzeuger(self, art: ErzeugerArt) -> Erzeuger:
		try:
			return next(e for e in self.erzeuger if e.art == art)
		except StopIteration:
			raise KeyError(f"Erzeuger nicht gefunden: {art}")

	# Holt den Verbraucher mit der angegebenen Art
	def get_verbraucher(self, art: VerbraucherArt) -> Verbraucher:
		try:
			return next(v for v in self.verbraucher if v.art == art)
		except StopIteration:
			raise KeyError(f"Verbraucher nicht gefunden: {art}")
