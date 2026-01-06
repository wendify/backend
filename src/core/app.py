import logging
import time

from core.prognose import loader
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard
from core.setup.verbraucher import VerbraucherArt
from core.simulation.co2_calc import calculate_co2_emissions
from core.simulation.simulator import apply_events_to_realized
from core.simulation.stack_model import apply_stack_model_to_ausbaupfad
from core.visualization.plots import show_all_plots


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

		print(f"Ausbaupfad erstellt in {step_duration} Sekunden")
		print(f"Erzeuger-Datenreihen: {len(ausbaupfad.prognose_erzeuger)}", end=", ")
		print(f"Verbraucher-Datenreihen: {len(ausbaupfad.prognose_verbraucher)}")

		# =====================================================================
		# Step 2.5: Apply Events to Prognose (before stack model)
		# =====================================================================
		if ausbaupfad.ereignisse:
			print("\n=== Schritt 2.5: Events auf Prognose anwenden ===")
			step_start = time.time()

			# Konvertiere Liste zu Dict für Event-Anwendung
			prognose_dict: dict[ErzeugerArt, Datenreihe] = {}
			for datenreihe in ausbaupfad.prognose_erzeuger:
				prognose_dict[datenreihe.art] = datenreihe

			# Events anwenden
			modifizierte_prognose = apply_events_to_realized(prognose_dict, ausbaupfad.ereignisse)

			# Zurück zu Liste konvertieren und Ausbaupfad aktualisieren
			ausbaupfad.prognose_erzeuger = list(modifizierte_prognose.values())

			step_duration = time.time() - step_start
			print(f"  {len(ausbaupfad.ereignisse)} Events angewendet")
			for event in ausbaupfad.ereignisse:
				print(
					f"    - {event.art.value}: {event.anfang.date()} bis {event.ende.date()} (Intensität: {event.intensitaet})"
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
			datenpunkte=ausbaupfad.installiert,
			smard=self.smard,
			co2_df=co2_df,
			default_resolution="1 Woche",
			debug_art=ErzeugerArt.Steinkohle,
		)
