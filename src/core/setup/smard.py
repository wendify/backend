import logging
import pickle

import config
from core.data import loader
from core.datenreihe import Datenreihe
from core.erzeuger import Erzeuger
from core.types import ErzeugerArt, VerbraucherArt


def get_regulation(art: ErzeugerArt) -> float:
	"""Get the regulation value for an ErzeugerArt.

	Regulation represents how much the output can be changed up or down
	within one time step, as a fraction of the installed capacity.

	Args:
		art: The type of energy producer

	Returns:
		Regulation value between 0.0 and 1.0
	"""
	if art == ErzeugerArt.Erdgas:
		return 1.0
	elif art == ErzeugerArt.Photovoltaik:
		return 0.0
	elif art == ErzeugerArt.Steinkohle:
		return 0.05
	elif art == ErzeugerArt.Braunkohle:
		return 0.02
	elif art == ErzeugerArt.Kernenergie:
		return 0.02
	elif art == ErzeugerArt.WindOffshore:
		return 0
	elif art == ErzeugerArt.WindOnshore:
		return 0
	elif art == ErzeugerArt.Wasserkraft:
		return 0
	elif art == ErzeugerArt.Biomasse:
		return 0.4
	elif art == ErzeugerArt.Pumpspeicher:
		return 1
	elif art == ErzeugerArt.SonstigeErneuerbare:
		return 0
	elif art == ErzeugerArt.SonstigeKonventionelle:
		return 0.2
	else:
		# Default regulation for other types
		# Can be adjusted as needed
		return 0.0


def get_co2(art: ErzeugerArt) -> float:
	"""Get the CO2 emission factor for an ErzeugerArt.

	Returns the CO2 emissions in tonnes per MWh of electricity generated.
	Values are based on typical emission factors for German power plants.

	Args:
		art: The type of energy producer

	Returns:
		CO2 emission factor in tonnes/MWh
	"""
	if art == ErzeugerArt.Braunkohle:
		# Lignite: highest emissions (~1100 g/kWh)
		return 1.1
	elif art == ErzeugerArt.Steinkohle:
		# Hard coal: (~850 g/kWh)
		return 0.85
	elif art == ErzeugerArt.Erdgas:
		# Natural gas: (~400 g/kWh)
		return 0.4
	elif art == ErzeugerArt.Kernenergie:
		# Nuclear: minimal lifecycle emissions (~10 g/kWh)
		return 0.01
	elif art == ErzeugerArt.Biomasse:
		# Biomass: considered CO2-neutral in operation
		return 0.0
	elif art == ErzeugerArt.SonstigeKonventionelle:
		# Other conventional: assume mix (~500 g/kWh)
		return 0.5
	else:
		# Renewables (PV, Wind, Hydro, Pumpspeicher): zero operational emissions
		return 0.0


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
		self.verbraucher: list[Datenreihe[VerbraucherArt]] = []

		self.installiert, self.realisiert, self.verbraucht = loader.load_csv()

		# Baue Erzeuger
		self.create_erzeuger()
		self.create_verbraucher()

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
			regulation = get_regulation(art)
			erzeuger = Erzeuger(art, installiert, realisiert, regulation)

			self.erzeuger.append(erzeuger)

	def get_erzeuger(self, art: ErzeugerArt) -> Erzeuger:
		try:
			return next(e for e in self.erzeuger if e.art == art)
		except StopIteration:
			logging.error(f"Erzeuger nicht gefunden: {art}")
			raise KeyError(art)

	def create_verbraucher(self) -> None:
		for art in VerbraucherArt:
			df = self.verbraucht[["Datum von", "Datum bis", art]]
			verbraucher = Datenreihe(art, df)

			self.verbraucher.append(verbraucher)

	def get_verbraucher(self, art: VerbraucherArt) -> Datenreihe[VerbraucherArt]:
		try:
			return next(v for v in self.verbraucher if v.art == art)
		except StopIteration:
			logging.error(f"Verbraucher nicht gefunden: {art}")
			raise KeyError(art)
