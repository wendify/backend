import logging
import time

from core.prognose import loader
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard
from core.simulation import co2_calc, simulator, stack_model
from core.visualization import plots


# Die Hauptklasse dieses Projekts
class App:
	def __init__(self) -> None:
		# SMARD-Daten vor der Simulation laden
		self.smard = Smard()

	# Startet die Simulation
	def run(self) -> None:
		logging.info("Simulation wird gestartet...")

		# Gesamte Zeitmessung starten
		total_start = time.time()

		# Schritt 1
		print("\n=== Schritt 1: Ausbaupfade laden ===")
		ausbaupfade = loader.load_all()

		# Abbrechen, wenn keine Ausbaupfade existieren
		if not ausbaupfade:
			raise FileNotFoundError("Kein Ausbaupfad gefunden!")

		# Wenn nur ein Ausbaupfad, diesen nehmen
		if len(ausbaupfade) == 1:
			ausbaupfad = ausbaupfade[0]

		# Ansonsten durch Eingabe auswählen lassen
		else:
			names = ", ".join(sorted(a.name for a in ausbaupfade))
			name = input(f"Ausbaupfad auswählen [{names}]: ")

			try:
				ausbaupfad = next(a for a in ausbaupfade if a.name == name)
			except StopIteration:
				raise FileNotFoundError("Ausbaupfad nicht gefunden!")

		# Informationen zum Ausbaupfad ausgeben
		print(f"Ausbaupfad ausgewählt: {ausbaupfad.name}")
		print(f"Installationen: {len(ausbaupfad.installiert)}", end=", ")
		print(f"Verbräuche: {len(ausbaupfad.verbraucht)}", end=", ")
		print(f"Ereignisse: {len(ausbaupfad.ereignisse)}")

		# Schritt 2
		print("\n=== Schritt 2: Ausbaupfad verarbeiten ===")
		step_start = time.time()

		ausbaupfad.process(self.smard)
		step_duration = time.time() - step_start

		print(f"Ausbaupfad erstellt in {step_duration:.2f} Sekunden")
		print(f"Erzeuger-Datenreihen: {len(ausbaupfad.prognose_erzeuger)}", end=", ")
		print(f"Verbraucher-Datenreihen: {len(ausbaupfad.prognose_verbraucher)}")

		# Schritt 3
		print("\n=== Schritt 3: Ereignisse auf Prognose anwenden ===")
		step_start = time.time()

		simulator.apply_events(ausbaupfad.prognose_erzeuger, ausbaupfad.ereignisse)
		step_duration = time.time() - step_start

		print(f"Ereignisse angewendet in {step_duration:.2f} Sekunden")
		print(f"Ereignisse: {len(ausbaupfad.ereignisse)}")

		# Schritt 4
		print("\n=== Schritt 4: Stack-Modell anwenden ===")
		step_start = time.time()

		realisiert_datenreihen = stack_model.apply_stack_model_to_ausbaupfad(ausbaupfad, self.smard)
		step_duration = time.time() - step_start

		print(f"Stack-Modell angewendet in {step_duration:.2f} Sekunden")
		print(f"Erzeugte Datenreihen: {len(realisiert_datenreihen)}")

		# Schritt 5
		print("\n=== Schritt 5: CO2-Berechnung ===")
		step_start = time.time()

		co2_df = co2_calc.calculate_co2_emissions(realisiert_datenreihen)
		step_duration = time.time() - step_start

		print(f"CO2-Emissionen berechnet in {step_duration:.2f} Sekunden")
		print(f"Erzeugte Datenreihen: {len(co2_df.columns)}")

		# Schritt 6
		print("\n=== Schritt 6: Visualisierung im Browser ===")
		step_start = time.time()

		# TODO: Plots komplett erneuern
		plots.show_all_plots(
			ausbaupfad=ausbaupfad,
			realisiert_datenreihen=realisiert_datenreihen,
			datenpunkte=ausbaupfad.installiert,
			smard=self.smard,
			co2_df=co2_df,
			default_resolution="1 Woche",
			debug_art=ErzeugerArt.Steinkohle,
		)

		step_duration = time.time() - step_start
		total_duration = time.time() - total_start

		print(f"Plots generiert in {step_duration:.2f} Sekunden")
		print(f"\n=== Gesamtdauer: {total_duration:.2f} Sekunden ===")
