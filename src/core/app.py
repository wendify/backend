# Standard library imports
import datetime
import logging

import fastapi
import pandas as pd
import uvicorn

import config
from core.api import routes
from core.erzeuger import ErzeugerArt
from core.types import VerbraucherArt

# Project-specific imports
from core import plot_helper
from core.prognose.ausbaupfad import Ausbaupfad
from core.prognose.datenpunkt import ErzeugerDatenpunkt, VerbraucherDatenpunkt
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
		self.plot_verbraucher()
		# self.test()

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
		# erzeuger = self.smard.get_erzeuger(ErzeugerArt.Photovoltaik)
		# # Fetch another generator (here: natural gas) just to show usage; not used further
		# erzeuger2 = self.smard.get_erzeuger(ErzeugerArt.Braunkohle)

		# print("--------------------------------")	
		# print("Maximale installierte Leistung:", erzeuger.installiert.werte.max())
		# print("Minimale installierte Leistung:", erzeuger.installiert.werte.min())
		# print("Median der installierten Leistung:", erzeuger.installiert.werte.median())
		# print("Mittelwert der installierten Leistung:", erzeuger.installiert.werte.mean())
		# print("--------------------------------")
		# current_erzeuger_installiert = erzeuger.installiert.werte.max()
		# current_erzeuger2_installiert = erzeuger2.installiert.werte.max()

		# # Define future capacity milestones for the selected generator type
		# # Each ErzeugerDatenpunkt: (generator type, date from which valid, installed MW)
		# datenpunkte: list[ErzeugerDatenpunkt] = [
		# 	ErzeugerDatenpunkt(erzeuger.art, datetime.datetime(2026, 5, 1), current_erzeuger_installiert/4),
		# 	ErzeugerDatenpunkt(erzeuger.art, datetime.datetime(2027, 11, 1), current_erzeuger_installiert*2),
		# 	ErzeugerDatenpunkt(erzeuger2.art, datetime.datetime(2028, 5, 1), current_erzeuger2_installiert/4),
		# ]

		# Erzeuger laden
		pv          = self.smard.get_erzeuger(ErzeugerArt.Photovoltaik)
		wind_on     = self.smard.get_erzeuger(ErzeugerArt.WindOnshore)
		wind_off    = self.smard.get_erzeuger(ErzeugerArt.WindOffshore)
		wasser      = self.smard.get_erzeuger(ErzeugerArt.Wasserkraft)
		biomasse    = self.smard.get_erzeuger(ErzeugerArt.Biomasse)
		pumpsp      = self.smard.get_erzeuger(ErzeugerArt.Pumpspeicher)
		sonst_ern   = self.smard.get_erzeuger(ErzeugerArt.SonstigeErneuerbare)

		erdgas      = self.smard.get_erzeuger(ErzeugerArt.Erdgas)
		steinkohle  = self.smard.get_erzeuger(ErzeugerArt.Steinkohle)
		braunkohle  = self.smard.get_erzeuger(ErzeugerArt.Braunkohle)
		kernenergie = self.smard.get_erzeuger(ErzeugerArt.Kernenergie)
		sonst_konv  = self.smard.get_erzeuger(ErzeugerArt.SonstigeKonventionelle)

		datenpunkte: list[ErzeugerDatenpunkt] = [

			# ============================================================
			# ERNEUERBARE ENERGIEN – Ausbaupfad (kumulierte installierte Leistung, MW)
			# Startwerte orientieren sich an Stand 2024/2025
			# ============================================================

			# Photovoltaik (starker Ausbau, EEG-Ziele angelehnt)
			ErzeugerDatenpunkt(pv.art, datetime.datetime(2026, 1, 1), 130_000),  # ~130 GW
			ErzeugerDatenpunkt(pv.art, datetime.datetime(2030, 1, 1), 215_000),  # ~215 GW
			ErzeugerDatenpunkt(pv.art, datetime.datetime(2035, 1, 1), 260_000),  # ~260 GW

			# Wind Onshore (moderater bis starker Ausbau)
			ErzeugerDatenpunkt(wind_on.art, datetime.datetime(2026, 1, 1), 70_000),   # ~70 GW
			ErzeugerDatenpunkt(wind_on.art, datetime.datetime(2030, 1, 1), 85_000),   # ~85 GW
			ErzeugerDatenpunkt(wind_on.art, datetime.datetime(2035, 1, 1), 100_000),  # ~100 GW

			# Wind Offshore (Ausbau, aber etwas unter Zielpfad wegen Realisierungsrisiken)
			ErzeugerDatenpunkt(wind_off.art, datetime.datetime(2026, 1, 1), 11_000),  # ~11 GW
			ErzeugerDatenpunkt(wind_off.art, datetime.datetime(2030, 1, 1), 25_000),  # ~25 GW
			ErzeugerDatenpunkt(wind_off.art, datetime.datetime(2035, 1, 1), 40_000),  # ~40 GW

			# Wasserkraft (nahezu konstant, nur geringer Zubau möglich)
			ErzeugerDatenpunkt(wasser.art, datetime.datetime(2026, 1, 1), 5_600),
			ErzeugerDatenpunkt(wasser.art, datetime.datetime(2030, 1, 1), 5_800),
			ErzeugerDatenpunkt(wasser.art, datetime.datetime(2035, 1, 1), 6_000),

			# Biomasse (leicht rückläufig / plateau, EEG sieht kaum Ausbau vor)
			ErzeugerDatenpunkt(biomasse.art, datetime.datetime(2026, 1, 1), 9_500),
			ErzeugerDatenpunkt(biomasse.art, datetime.datetime(2030, 1, 1), 9_000),
			ErzeugerDatenpunkt(biomasse.art, datetime.datetime(2035, 1, 1), 8_000),

			# Pumpspeicher (leichter Ausbau + Modernisierung)
			ErzeugerDatenpunkt(pumpsp.art, datetime.datetime(2026, 1, 1), 10_000),
			ErzeugerDatenpunkt(pumpsp.art, datetime.datetime(2030, 1, 1), 11_000),
			ErzeugerDatenpunkt(pumpsp.art, datetime.datetime(2035, 1, 1), 13_000),

			# Sonstige Erneuerbare (Geothermie, Deponiegas etc.)
			ErzeugerDatenpunkt(sonst_ern.art, datetime.datetime(2026, 1, 1), 1_500),
			ErzeugerDatenpunkt(sonst_ern.art, datetime.datetime(2030, 1, 1), 3_000),
			ErzeugerDatenpunkt(sonst_ern.art, datetime.datetime(2035, 1, 1), 5_000),


			# ============================================================
			# KONVENTIONELLE ERZEUGER – Rückbaupfad / leichte Verschiebungen
			# ============================================================

			# Erdgas (etwas Ausbau H2-ready, später leichte Reduktion)
			ErzeugerDatenpunkt(erdgas.art, datetime.datetime(2026, 1, 1), 36_000),
			ErzeugerDatenpunkt(erdgas.art, datetime.datetime(2030, 1, 1), 40_000),
			ErzeugerDatenpunkt(erdgas.art, datetime.datetime(2035, 1, 1), 38_000),

			# Steinkohle (deutlicher Rückbau, Ausstieg ≈ 2030)
			ErzeugerDatenpunkt(steinkohle.art, datetime.datetime(2026, 1, 1), 12_000),
			ErzeugerDatenpunkt(steinkohle.art, datetime.datetime(2030, 1, 1), 3_000),
			ErzeugerDatenpunkt(steinkohle.art, datetime.datetime(2035, 1, 1), 0),

			# Braunkohle (Rückbau bis spätestens 2038, 2035 fast aus dem Markt)
			ErzeugerDatenpunkt(braunkohle.art, datetime.datetime(2026, 1, 1), 13_000),
			ErzeugerDatenpunkt(braunkohle.art, datetime.datetime(2030, 1, 1), 8_000),
			ErzeugerDatenpunkt(braunkohle.art, datetime.datetime(2035, 1, 1), 2_000),

			# Kernenergie (bleibt bei 0 – Ausstieg vollzogen)
			ErzeugerDatenpunkt(kernenergie.art, datetime.datetime(2026, 1, 1), 0),
			ErzeugerDatenpunkt(kernenergie.art, datetime.datetime(2030, 1, 1), 0),
			ErzeugerDatenpunkt(kernenergie.art, datetime.datetime(2035, 1, 1), 0),

			# Sonstige konventionelle (Öl, Abfall, Industrieanlagen etc.)
			ErzeugerDatenpunkt(sonst_konv.art, datetime.datetime(2026, 1, 1), 4_000),
			ErzeugerDatenpunkt(sonst_konv.art, datetime.datetime(2030, 1, 1), 3_500),
			ErzeugerDatenpunkt(sonst_konv.art, datetime.datetime(2035, 1, 1), 3_000),
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
			from matplotlib.widgets import CheckButtons, RadioButtons
		except ModuleNotFoundError:
			return

		# ---------------------------------------------------------
		# Interaktiver Stackplot aller Erzeuger
		# ---------------------------------------------------------

		# 1) Daten aller Erzeuger aus dem Ausbaupfad sammeln
		# Wir holen uns die DataFrames, setzen den Index auf "Datum von" und mergen sie.
		data_frames = []
		for dr in ausbaupfad.prognose_datenreihen:
			# dr.df hat Spalten ["Datum von", "Datum bis", <ErzeugerArt>]
			series = dr.df.set_index("Datum von")[dr.art]
			data_frames.append(series)

		if not data_frames:
			print("Keine Prognosedaten vorhanden.")
			return

		# Zu einem großen DataFrame zusammenfügen (Outer Join auf Zeitindex)
		df_all = pd.concat(data_frames, axis=1).fillna(0)
		
		# Spalten sortieren (z.B. alphabetisch), damit die Legende stabil ist
		cols = sorted(df_all.columns)
		df_all = df_all[cols]

		# Farben fixieren (damit sie beim Ausblenden nicht springen)
		cmap = pyplot.get_cmap("tab20")
		# Mapping: Spaltenname -> Farbe
		col_colors = {col: cmap(i % 20) for i, col in enumerate(cols)}

		# Enddatum der historischen Daten (SMARD) finden
		smard_end = pv.realisiert.df["Datum von"].iloc[-1]

		# Zeitpunkte der Prognose-Datenpunkte sammeln (nur unique)
		dp_times = sorted({dp.datetime for dp in datenpunkte})

		# 2) Plot 1 vorbereiten: Gesamterzeugung
		# =========================================================
		fig1, ax1 = pyplot.subplots(figsize=(12, 6))
		fig1.canvas.manager.set_window_title("Prognose: Erzeugung (Stackplot)")
		# Platz rechts für die Widgets lassen
		pyplot.subplots_adjust(right=0.75)

		# Initialer Status: Nur PV sichtbar
		visibility = [False] * len(cols)
		# Index von Photovoltaik finden
		try:
			pv_idx = cols.index(ErzeugerArt.Photovoltaik)
			visibility[pv_idx] = True
		except ValueError:
			# Falls PV nicht in der Liste, alles aus oder ersten an - egal
			pass
		
		# Resolution-Mapping
		res_map = {
			"15 min": None,
			"1 h": "h",
			"1 Tag": "D",
			"1 Woche": "W"
		}
		# Standardmäßig Wöchentlich
		current_res_label = "1 Woche"

		def get_plot_data(res_label):
			"""Resample data based on selection."""
			rule = res_map.get(res_label)
			if rule is None:
				return df_all
			# Resample using mean (average power in MW)
			return df_all.resample(rule).mean()

		def update_plot(val=None):
			"""
			Aktualisiert den Plot.
			val ist ein Dummy-Argument, damit es als Callback funktioniert.
			"""
			ax1.clear()
			
			# Aktive Spalten filtern
			active_cols = [c for c, v in zip(cols, visibility) if v]
			
			if active_cols:
				# Daten passend zur Resolution holen
				df_plot = get_plot_data(current_res_label)
				
				x = df_plot.index
				y = [df_plot[c] for c in active_cols]
				# Farben für die aktiven Spalten holen
				stack_colors = [col_colors[c] for c in active_cols]
				
				# Stackplot zeichnet die Flächen übereinander (kumuliert)
				ax1.stackplot(x, y, labels=active_cols, colors=stack_colors, alpha=0.8)
				
				# Legende
				ax1.legend(loc="upper left", bbox_to_anchor=(1.05, 1.0), borderaxespad=0.)
			
			# Zusatz-Markierungen
			# 1. Vertikale Linie: Ende der Smard-Daten
			ax1.axvline(x=smard_end, color="red", linestyle="--", linewidth=1.5, label="Ende Historie")
			
			# 2. Markierungen für Prognose-Datenpunkte
			for t in dp_times:
				ax1.axvline(x=t, color="black", linestyle=":", linewidth=1.0, alpha=0.7)
			
			ax1.set_title(f"Gesamterzeugung (Auflösung: {current_res_label})")
			ax1.set_xlabel("Zeit")
			ax1.set_ylabel("Leistung [MW]")
			ax1.grid(True, linestyle="--", alpha=0.5)
			
			# Canvas aktualisieren
			fig1.canvas.draw_idle()

		# Erster Draw
		update_plot()

		# 3) Widgets für Plot 1 erstellen
		
		# Bereich für CheckButtons (Erzeuger an/aus) - obere Hälfte rechts
		rax_check = pyplot.axes([0.78, 0.45, 0.2, 0.45])  # [left, bottom, width, height]
		rax_check.set_title("Erzeuger an/aus")
		check = CheckButtons(rax_check, cols, visibility)

		# Färbe die Checkboxen und Labels passend zum Graphen
		# 1. Versuche, die Labels (Text) zu färben
		if hasattr(check, "labels"):
			for i, label_obj in enumerate(check.labels):
				col_name = cols[i]
				label_obj.set_color(col_colors[col_name])
				label_obj.set_fontweight("bold")

		# 2. Versuche, die Rechtecke (Kästchen) zu färben
		boxes = getattr(check, "rectangles", rax_check.patches)
		if len(boxes) == 0:
			print("Warnung: Keine Checkbox-Rechtecke zum Einfärben gefunden.")

		for i, col in enumerate(cols):
			if i < len(boxes):
				rect = boxes[i]
				rect.set_facecolor(col_colors[col])
				rect.set_edgecolor("black")
				rect.set_alpha(0.8)

		def on_check_click(label):
			# Index des Labels finden
			idx = cols.index(label)
			# Status toggeln
			visibility[idx] = not visibility[idx]
			# Neu zeichnen
			update_plot()

		check.on_clicked(on_check_click)

		# Bereich für RadioButtons (Auflösung) - untere Hälfte rechts
		rax_radio = pyplot.axes([0.78, 0.1, 0.2, 0.25])
		rax_radio.set_title("Auflösung")
		# Default active index setzen: 3 für "1 Woche" (Index 3 in res_map keys)
		# Keys sind: 15 min, 1 h, 1 Tag, 1 Woche -> index 3
		radio = RadioButtons(rax_radio, list(res_map.keys()), active=3)

		def on_radio_click(label):
			nonlocal current_res_label
			current_res_label = label
			update_plot()

		radio.on_clicked(on_radio_click)

		# =========================================================
		# Plot 2 vorbereiten: Installierte Leistung (Line Plot)
		# =========================================================
		# Daten vorbereiten:
		# Wir gehen wieder durch alle Prognose-Datenreihen, aber diesmal bräuchten wir
		# eigentlich die installierte Leistung. 
		# Da wir im `App.test()` Loop die installierte Leistung nicht direkt als "Datenreihe" 
		# gespeichert haben (die Prognose-Datenreihe ist ja Erzeugung), 
		# müssen wir sie hier theoretisch rekonstruieren oder aus `ausbaupfad` holen.
		# 
		# Der Ausbaupfad berechnet die Prognose on-the-fly. 
		# Wir improvisieren hier und zeigen die Interpolation zwischen den Datenpunkten.
		
		fig2, ax2 = pyplot.subplots(figsize=(10, 5))
		fig2.canvas.manager.set_window_title("Prognose: Installierte Leistung")

		# Iteriere über alle Erzeuger und plotte deren "Pfad" (linear interpoliert zwischen Datenpunkten)
		# Wir nutzen dazu einfach die Datenpunkte selbst.
		
		# Wir brauchen ein gemeinsames Zeitraster für den Plot
		plot_start = smard_end - datetime.timedelta(days=365) # 1 Jahr zurück für Kontext
		plot_end = max(dp_times) if dp_times else smard_end + datetime.timedelta(days=365*5)
		
		# Zeitachse erstellen (monatlich reicht für Übersicht)
		time_range = pd.date_range(start=plot_start, end=plot_end, freq="D")
		
		ax2.set_title("Installierte Leistung (Ausbaupfad)")
		
		for art in cols: # Nutze gleiche Sortierung
			# 1. Hole Datenpunkte für diese Art
			dps = ausbaupfad.get_erzeuger(art)
			if not dps: 
				# Falls keine expliziten DPs, dann vielleicht konstant vom letzten SMARD-Wert
				# Wir holen den letzten installierten Wert aus dem Smard-Objekt (falls vorhanden)
				# Das ist etwas hacky hier im Test-Code, aber ok für Visualisierung.
				try:
					erz = self.smard.get_erzeuger(art)
					val = erz.installiert.werte.iloc[-1]
					# Zeichne konstante Linie
					ax2.plot([plot_start, plot_end], [val, val], 
							label=art, color=col_colors[art], linewidth=2)
				except:
					pass
				continue

			# Wir haben Datenpunkte. Dazu kommt der Startpunkt (letzter SMARD-Wert)
			erz = self.smard.get_erzeuger(art)
			last_smard_time = erz.installiert.df["Datum von"].iloc[-1]
			last_smard_val = erz.installiert.werte.iloc[-1]
			
			# Baue Stützstellen: (Zeit, Wert)
			# Startpunkt
			x_points = [last_smard_time]
			y_points = [last_smard_val]
			
			# Prognosepunkte sortiert
			dps_sorted = sorted(dps, key=lambda d: d.datetime)
			for dp in dps_sorted:
				x_points.append(dp.datetime)
				y_points.append(dp.installiert)
				
			# Plotten als Linie mit Markern
			ax2.plot(x_points, y_points, marker="o", label=art, color=col_colors[art], linewidth=2)

		# Ende Historie Linie auch hier
		ax2.axvline(x=smard_end, color="red", linestyle="--", linewidth=1.5, label="Ende Historie")
		
		ax2.set_ylabel("Installierte Leistung [MW]")
		ax2.grid(True, alpha=0.3)
		# Legende außerhalb rechts
		ax2.legend(loc="center left", bbox_to_anchor=(1, 0.5))
		fig2.tight_layout()

		pyplot.show()

		# Short textual summary to quickly verify size and covered time span
		print("\nPrognose-Form:", prognose.df.shape)
		print("Zeitraum:", prognose.df["Datum von"].iloc[0], "→", prognose.df["Datum bis"].iloc[-1])

	def plot_verbraucher(self) -> None:
		"""
		Plot Verbraucher-Prognose (Netzlast).
		Gleiche Logik wie Erzeuger-Prognose.
		"""
		logging.info("Verbraucher wird geplottet...")
		
		# Verbraucher-Datenpunkte definieren (Netzlast-Prognose)
		verbraucher_datenpunkte: list[VerbraucherDatenpunkt] = [
			VerbraucherDatenpunkt(VerbraucherArt.Netzlast, datetime.datetime(2026, 1, 1), self.smard.get_verbraucher(VerbraucherArt.Netzlast).df["Netzlast"].mean()),
			VerbraucherDatenpunkt(VerbraucherArt.Netzlast, datetime.datetime(2030, 1, 1), self.smard.get_verbraucher(VerbraucherArt.Netzlast).df["Netzlast"].mean()*2),
			VerbraucherDatenpunkt(VerbraucherArt.Netzlast, datetime.datetime(2035, 1, 1), self.smard.get_verbraucher(VerbraucherArt.Netzlast).df["Netzlast"].mean()),
		]

		print(self.smard.get_verbraucher(VerbraucherArt.Netzlast).df["Netzlast"].mean())

		# Ausbaupfad erstellen (leere Erzeuger-Liste, nur Verbraucher)
		ausbaupfad = Ausbaupfad([], verbraucher_datenpunkte, smard=self.smard)
		
		# Verbraucher-Prognose-Datenreihen holen und zusammenführen
		datenreihen = ausbaupfad.prognose_verbraucher_datenreihen
		df_merged = plot_helper.merge_datenreihen(datenreihen)
		
		# Auf Tages-Daten resamplen für bessere Sichtbarkeit
		df_daily = plot_helper.resample_dataframe(df_merged, "1w")
		
		# Lineplot erstellen
		plot_helper.create_lineplot(
			df=df_daily,
			title="Verbraucher-Prognose (Netzlast)",
			ylabel="Leistung [MW]",
			show_markers=False,
		)
		plot_helper.show_plots()

	def plot_examples(self) -> None:
		"""
		Demonstrates how to use the plot_helper module for plotting Datenreihen.
		
		This method shows:
		1) How to merge multiple Datenreihen into one DataFrame
		2) How to create a stackplot (stacked area chart)
		3) How to create a lineplot
		4) How to add vertical marker lines
		5) How to resample data to different resolutions
		6) How to filter specific columns for plotting
		"""
		logging.info("Plot-Beispiele werden erstellt...")

		# ---------------------------------------------------------------
		# Step 1: Build an Ausbaupfad with example data points
		# ---------------------------------------------------------------
		
		# Load some generators from SMARD
		pv = self.smard.get_erzeuger(ErzeugerArt.Photovoltaik)
		wind_on = self.smard.get_erzeuger(ErzeugerArt.WindOnshore)
		wind_off = self.smard.get_erzeuger(ErzeugerArt.WindOffshore)
		braunkohle = self.smard.get_erzeuger(ErzeugerArt.Braunkohle)

		# Define some example data points for the forecast
		datenpunkte: list[ErzeugerDatenpunkt] = [
			# Photovoltaik expansion
			ErzeugerDatenpunkt(pv.art, datetime.datetime(2026, 1, 1), 130_000),
			ErzeugerDatenpunkt(pv.art, datetime.datetime(2030, 1, 1), 215_000),
			ErzeugerDatenpunkt(pv.art, datetime.datetime(2035, 1, 1), 260_000),
			
			# Wind Onshore expansion
			ErzeugerDatenpunkt(wind_on.art, datetime.datetime(2026, 1, 1), 70_000),
			ErzeugerDatenpunkt(wind_on.art, datetime.datetime(2030, 1, 1), 85_000),
			ErzeugerDatenpunkt(wind_on.art, datetime.datetime(2035, 1, 1), 100_000),
			
			# Wind Offshore expansion
			ErzeugerDatenpunkt(wind_off.art, datetime.datetime(2026, 1, 1), 11_000),
			ErzeugerDatenpunkt(wind_off.art, datetime.datetime(2030, 1, 1), 25_000),
			ErzeugerDatenpunkt(wind_off.art, datetime.datetime(2035, 1, 1), 40_000),
			
			# Braunkohle phase-out
			ErzeugerDatenpunkt(braunkohle.art, datetime.datetime(2026, 1, 1), 13_000),
			ErzeugerDatenpunkt(braunkohle.art, datetime.datetime(2030, 1, 1), 8_000),
			ErzeugerDatenpunkt(braunkohle.art, datetime.datetime(2035, 1, 1), 2_000),
		]

		# Build the Ausbaupfad
		ausbaupfad = Ausbaupfad(datenpunkte, smard=self.smard)

		# ---------------------------------------------------------------
		# Step 2: Merge Datenreihen using plot_helper
		# ---------------------------------------------------------------
		
		# Get all prognose Datenreihen from the Ausbaupfad
		datenreihen = ausbaupfad.prognose_datenreihen
		
		# Use plot_helper to merge them into a single DataFrame
		df_merged = plot_helper.merge_datenreihen(datenreihen)
		
		print("Merged DataFrame shape:", df_merged.shape)
		print("Columns:", list(df_merged.columns))

		# ---------------------------------------------------------------
		# Step 3: Create a color map for consistent coloring
		# ---------------------------------------------------------------
		
		# Get sorted column names
		columns = sorted(df_merged.columns)
		
		# Create a color map that assigns a unique color to each generator type
		color_map = plot_helper.get_color_map(columns)

		# ---------------------------------------------------------------
		# Step 4: Create a stackplot showing all generators
		# ---------------------------------------------------------------
		
		# Resample to weekly data for better visibility
		df_weekly = plot_helper.resample_dataframe(df_merged, "1w")
		
		# Create the stackplot
		fig1, ax1 = plot_helper.create_stackplot(
			df=df_weekly,
			title="Prognose: Stromerzeugung (Stackplot)",
			xlabel="Zeit",
			ylabel="Leistung [MW]",
			color_map=color_map,
			figsize=(12, 6),
		)
		
		# Find the end of historical SMARD data
		smard_end = pv.realisiert.df["Datum von"].iloc[-1]
		
		# Add a vertical line to mark the end of historical data
		plot_helper.add_vertical_line(
			ax=ax1,
			x_value=smard_end,
			color="red",
			linestyle="--",
			linewidth=2.0,
			label="Ende Historie",
		)
		
		# Add vertical lines for each forecast data point
		dp_times = sorted({dp.datetime for dp in datenpunkte})
		plot_helper.add_multiple_vertical_lines(
			ax=ax1,
			x_values=dp_times,
			color="black",
			linestyle=":",
			alpha=0.5,
		)

		# ---------------------------------------------------------------
		# Step 5: Create a filtered stackplot (only renewables)
		# ---------------------------------------------------------------
		
		# Filter to show only selected generators
		renewables = [
			ErzeugerArt.Photovoltaik,
			ErzeugerArt.WindOnshore,
			ErzeugerArt.WindOffshore,
		]
		df_renewables = plot_helper.filter_columns(df_weekly, renewables)
		
		# Create a second stackplot with only renewables
		fig2, ax2 = plot_helper.create_stackplot(
			df=df_renewables,
			title="Prognose: Erneuerbare Energien",
			ylabel="Leistung [MW]",
			color_map=color_map,
			figsize=(10, 5),
		)
		
		# Add end of history marker
		plot_helper.add_vertical_line(ax2, smard_end, color="red", linestyle="--")

		# ---------------------------------------------------------------
		# Step 6: Create a lineplot for comparison
		# ---------------------------------------------------------------
		
		# Resample to daily data for the lineplot
		df_daily = plot_helper.resample_dataframe(df_merged, "1d")
		
		# Filter to only Photovoltaik and Braunkohle for clear comparison
		comparison_columns = [ErzeugerArt.Photovoltaik, ErzeugerArt.Braunkohle]
		df_comparison = plot_helper.filter_columns(df_daily, comparison_columns)
		
		# Create a lineplot
		fig3, ax3 = plot_helper.create_lineplot(
			df=df_comparison,
			title="Vergleich: Photovoltaik vs. Braunkohle",
			ylabel="Leistung [MW]",
			color_map=color_map,
			figsize=(10, 5),
			show_markers=False,  # Too many points for markers
		)
		
		# Add end of history marker
		plot_helper.add_vertical_line(ax3, smard_end, color="red", linestyle="--")

		# ---------------------------------------------------------------
		# Step 7: Show all plots
		# ---------------------------------------------------------------
		
		print("\nPlots werden angezeigt...")
		plot_helper.show_plots()
