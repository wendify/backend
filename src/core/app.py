import datetime
import logging

import fastapi
import uvicorn

import config
from core.api import routes
from core.erzeuger import ErzeugerArt
from core.prognose.ausbaupfad import Ausbaupfad
from core.prognose.datenpunkt import Datenpunkt
from core.setup.smard import Smard


class App:
	def __init__(self) -> None:
		self.api = fastapi.FastAPI()
		self.smard = Smard()

		routes.setup(self.api, self.smard)

	def run(self) -> None:
		logging.info("Anwendung gestartet")
		self.start()

	def start(self) -> None:
		uvicorn.run(self.api, host=config.API_HOST, port=config.API_PORT, log_level="error")

	def test(self) -> None:
		datum = datetime.datetime(2025, 1, 2, 12, 30)
		erzeuger = self.smard.get_erzeuger(ErzeugerArt.Photovoltaik)

		datenpunkte: list[Datenpunkt] = [
			Datenpunkt(erzeuger.art, datetime.datetime(2026, 5, 1), 6000),
			Datenpunkt(erzeuger.art, datetime.datetime(2027, 11, 1), 12000),
		]
		ausbaupfad = Ausbaupfad(datenpunkte, smard=self.smard)
		print(ausbaupfad.datenpunkte)
		prognose = ausbaupfad.get_prognose_datenreihe(ErzeugerArt.Photovoltaik)
		print("\nErste Prognose-Zeilen (Braunkohle):")
		print(prognose.df.head())

		# print("\nInstallierter Wert:")
		# print(erzeuger.installiert.get_row(datum))
		#
		# print("\nRealisierter Wert:")
		# print(erzeuger.realisiert.get_row(datum))
		#
		# print("\nNormierter Wert:")
		# print(erzeuger.normiert.get_row(datum))

		# Plot erstellen, falls matplotlib installiert ist
		try:
			from matplotlib import pyplot
		except ModuleNotFoundError:
			return

		# Komplette Prognose-Zeitreihe plotten (kein Datum-Filter)
		pyplot.figure(figsize=(12, 5))
		pyplot.plot(prognose.df["Datum von"], prognose.df[ErzeugerArt.Photovoltaik], linewidth=0.8)
		pyplot.title(f"Prognose {ErzeugerArt.Photovoltaik} – gesamte Zeitreihe")
		pyplot.xlabel("Zeit")
		pyplot.ylabel(f"{ErzeugerArt.Photovoltaik} Erzeugung (MW)")
		pyplot.grid(True)
		pyplot.tight_layout()
		pyplot.show()

		# Kurze Zusammenfassung zur Kontrolle
		print("\nPrognose-Form:", prognose.df.shape)
		print("Zeitraum:", prognose.df["Datum von"].iloc[0], "→", prognose.df["Datum bis"].iloc[-1])
