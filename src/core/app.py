# Standard library imports
import datetime
import logging

import fastapi
import uvicorn

import config
from core.api import routes
from core.erzeuger import ErzeugerArt

# Project-specific imports
from core.prognose.ausbaupfad import Ausbaupfad
from core.prognose.datenpunkt import Datenpunkt
from core.setup.smard import Smard
from core.simulation import Simulation


class App:
	"""
	Small driver class that wires data sources (SMARD), builds a forecast (Ausbaupfad),
	optionally applies a simulation (e.g. drought), and visualizes the result.
	"""

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
		"""
		Run a short end-to-end flow:
		1) build a simple Ausbaupfad from a few Datenpunkte
		2) compute a Prognose-Datenreihe
		3) apply a drought simulation
		4) show a quick plot and a short textual summary
		"""
		# Start message so it is clear in the logs what happens now
		logging.info("Prognose wird gestartet...")

		# Example timestamp used in the commented debug section below
		datum = datetime.datetime(2025, 1, 2, 12, 30)
		# Get a generator (here: lignite) from SMARD; used for the Ausbaupfad below
		erzeuger = self.smard.get_erzeuger(ErzeugerArt.Braunkohle)
		# Fetch another generator (here: natural gas) just to show usage; not used further
		erzeuger2 = self.smard.get_erzeuger(ErzeugerArt.Erdgas)

		# Define future capacity milestones for the selected generator type
		# Each Datenpunkt: (generator type, date from which valid, installed MW)
		datenpunkte: list[Datenpunkt] = [
			Datenpunkt(erzeuger.art, datetime.datetime(2026, 5, 1), 6000),
			Datenpunkt(erzeuger.art, datetime.datetime(2027, 11, 1), 12000),
		]
		# Build the Ausbaupfad from those points and pass SMARD for required context/data
		ausbaupfad = Ausbaupfad(datenpunkte, smard=self.smard)
		# Quick debug print: shows the internal list of Datenpunkte
		print(ausbaupfad.datenpunkte)
		# Create a forecast time series for a specific generator type (here: Photovoltaik)
		prognose = ausbaupfad.get_prognose_datenreihe(ErzeugerArt.Photovoltaik)
		# Show the first rows before any simulation is applied
		print("\nErste Prognose-Zeilen (vor Simulation):")
		print(prognose.df.head())

		# Build a drought simulation; intensity 0.8 = strong impact on production
		simulation = Simulation.create_drought(intensity=0.8)
		# Apply the simulation to the forecast for the chosen generator type
		prognose_with_drought = simulation.apply_to_datenreihe(prognose, ErzeugerArt.Photovoltaik)
		# Show the first rows after the simulation was applied
		print("\nErste Prognose-Zeilen (nach Dürre-Simulation):")
		print(prognose_with_drought.df.head())

		# Optional direct probes for a single timestamp; kept as commented examples
		# print("\nInstallierter Wert:")
		# print(erzeuger.installiert.get_row(datum))
		#
		# print("\nRealisierter Wert:")
		# print(erzeuger.realisiert.get_row(datum))
		#
		# print("\nNormierter Wert:")
		# print(erzeuger.normiert.get_row(datum))

		# Plot only if matplotlib is available; otherwise just return silently
		try:
			from matplotlib import pyplot
		except ModuleNotFoundError:
			return

		# Plot the full forecast time series (no date filter)
		pyplot.figure(figsize=(12, 5))
		# Baseline forecast without simulation
		pyplot.plot(
			prognose.df["Datum von"],
			prognose.df[ErzeugerArt.Photovoltaik],
			linewidth=0.8,
			label="Ohne Simulation",
			alpha=0.7,
		)
		# Forecast after applying the drought simulation
		pyplot.plot(
			prognose_with_drought.df["Datum von"],
			prognose_with_drought.df[ErzeugerArt.Photovoltaik],
			linewidth=0.8,
			label="Mit Dürre (80%)",
			alpha=0.7,
		)
		# Basic plot metadata for readability
		pyplot.title(f"Prognose {ErzeugerArt.Photovoltaik} – mit/ohne Dürre-Simulation")
		pyplot.xlabel("Zeit")
		pyplot.ylabel(f"{ErzeugerArt.Photovoltaik} Erzeugung (MW)")
		pyplot.legend()
		pyplot.grid(True)
		pyplot.tight_layout()
		pyplot.show()

		# Short textual summary to quickly verify size and covered time span
		print("\nPrognose-Form:", prognose.df.shape)
		print("Zeitraum:", prognose.df["Datum von"].iloc[0], "→", prognose.df["Datum bis"].iloc[-1])
