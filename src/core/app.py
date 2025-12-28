"""
Main application module.

This is the entry point for the energy transition simulation.
It orchestrates:
1. SMARD data loading
2. Scenario configuration
3. Prognosis calculation (Ausbaupfad)
4. Stack model simulation
5. Visualization (Plotly in browser)
"""

import logging
import time

from core.prognose import loader
from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard
from core.setup.verbraucher import VerbraucherArt
from core.simulation.co2_calc import calculate_co2_emissions
from core.simulation.simulator import apply_events_to_realized
from core.simulation.stack_model import apply_stack_model_to_ausbaupfad
from core.visualization.plots import show_all_plots


class App:
	"""
	Main application class.

	Wires together:
	- Data sources (SMARD)
	- Scenarios (future capacity targets)
	- Simulation (stack model)
	- Visualization (Plotly interactive plots)
	"""

	def __init__(self) -> None:
		"""Initialize the application with API and data source."""
		self.smard = Smard()

	def run(self) -> None:
		"""
		Run the complete energy transition simulation:

		1. Load scenario (expansion targets)
		2. Build Ausbaupfad (forecast time series)
		3. Apply stack model (convert potential to realized generation)
		4. Show interactive plots in browser
		"""
		logging.info("Simulation wird gestartet...")
		total_start = time.time()

		# =====================================================================
		# Step 1: Load scenario from CSV files
		# =====================================================================
		print("\n=== Schritt 1: Szenario laden ===")
		szenario_name, (datenpunkte, verbraucher_datenpunkte, event_datenpunkte) = next(
			iter(loader.load_all().items())
		)
		print(f"  Szenario '{szenario_name}' geladen")
		print(f"  {len(datenpunkte)} Erzeuger-Datenpunkte")
		print(f"  {len(verbraucher_datenpunkte)} Verbraucher-Datenpunkte")
		print(f"  {len(event_datenpunkte)} Event-Datenpunkte")

		# =====================================================================
		# Step 2: Build Ausbaupfad (forecast)
		# =====================================================================
		print("\n=== Schritt 2: Ausbaupfad erstellen ===")
		step_start = time.time()

		ausbaupfad = Ausbaupfad(datenpunkte, verbraucher_datenpunkte, smard=self.smard)

		step_duration = time.time() - step_start
		print(f"  Ausbaupfad erstellt in {step_duration:.2f} Sekunden")
		print(f"  {len(ausbaupfad.prognose_datenreihen)} Prognose-Datenreihen")

		# =====================================================================
		# Step 2.5: Apply Events to Prognose (before stack model)
		# =====================================================================
		if event_datenpunkte:
			print("\n=== Schritt 2.5: Events auf Prognose anwenden ===")
			step_start = time.time()

			# Konvertiere Liste zu Dict für Event-Anwendung
			prognose_dict: dict[ErzeugerArt, Datenreihe] = {}
			for datenreihe in ausbaupfad.prognose_datenreihen:
				prognose_dict[datenreihe.art] = datenreihe

			# Events anwenden
			modifizierte_prognose = apply_events_to_realized(prognose_dict, event_datenpunkte)

			# Zurück zu Liste konvertieren und Ausbaupfad aktualisieren
			ausbaupfad.prognose_datenreihen = list(modifizierte_prognose.values())

			step_duration = time.time() - step_start
			print(f"  {len(event_datenpunkte)} Events angewendet")
			for event in event_datenpunkte:
				print(
					f"    - {event.event_typ.value}: {event.datum_von.date()} bis {event.datum_bis.date()} (Intensität: {event.intensitaet})"
				)
			print(f"  Events dauerten: {step_duration:.2f} Sekunden")

		# =====================================================================
		# Step 3: Apply stack model
		# =====================================================================
		print("\n=== Schritt 3: Stack-Modell anwenden ===")
		step_start = time.time()

		realisiert_datenreihen = apply_stack_model_to_ausbaupfad(
			ausbaupfad=ausbaupfad,
			smard=self.smard,
			verbrauch_art=VerbraucherArt.Netzlast,
		)

		step_duration = time.time() - step_start
		print(f"  Realisierte Erzeugung für {len(realisiert_datenreihen)} Erzeuger berechnet")
		print(f"  Stack-Modell dauerte: {step_duration:.2f} Sekunden")

		# =====================================================================
		# Step 3.5: CO2 Calculation
		# =====================================================================
		print("\n=== Schritt 3.5: CO2-Berechnung ===")
		step_start = time.time()

		co2_df = calculate_co2_emissions(realisiert_datenreihen)

		step_duration = time.time() - step_start
		print(f"  CO2-Daten für {len(co2_df.columns)} Erzeuger berechnet")
		print(f"  CO2-Berechnung dauerte: {step_duration:.2f} Sekunden")

		# =====================================================================
		# Step 4: Visualization (Plotly in browser)
		# =====================================================================
		print("\n=== Schritt 4: Visualisierung ===")

		total_duration = time.time() - total_start
		print(
			f"\n=== Gesamtdauer: {total_duration:.2f} Sekunden ({total_duration / 60:.2f} Minuten) ===\n"
		)

		# Show interactive Plotly plots in browser
		show_all_plots(
			ausbaupfad=ausbaupfad,
			realisiert_datenreihen=realisiert_datenreihen,
			datenpunkte=datenpunkte,
			smard=self.smard,
			co2_df=co2_df,
			default_resolution="1 Woche",
			debug_art=ErzeugerArt.Steinkohle,
		)
