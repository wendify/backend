"""
Stack-Modell Algorithmus zur Erzeugungszuordnung

Logik:
1. Mindestleistung (MUSS) für Dispatchables berechnen
2. Erneuerbare IMMER voll nutzen (keine Abregelung)
3. Überschuss = MUSS + Erneuerbare - Verbrauch
   - Bei Überschuss: Dispatchables Richtung 0 regeln (mit Ramp-Limits)
   - Bei Unterdeckung: Dispatchables hochfahren (mit Ramp-Limits)

- Erneuerbare (regulation = 0) werden nie abgeregelt, Überschuss wird akzeptiert
- Konventionelle werden mit Ramp-Limits (± 2*reg*max_avail) geregelt
- Mindestleistung (MUSS) für EPS < reg < 1-EPS: prev_realized * (1 - reg)
"""

import time

import numpy
from numpy import float64
from pandas import DataFrame, Timedelta

from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard
from core.setup.verbraucher import VerbraucherArt

# Prioritätenreihenfolge für das Auffüllen bei Unterdeckung
PRIORITY_ORDER = [
	ErzeugerArt.Kernenergie,
	ErzeugerArt.Pumpspeicher,
	ErzeugerArt.Biomasse,
	ErzeugerArt.Erdgas,
	ErzeugerArt.Steinkohle,
	ErzeugerArt.Braunkohle,
	ErzeugerArt.SonstigeKonventionelle,
]

EPS = 1e-9


def calculate_realized_generation(
	max_available_datenreihen: dict[ErzeugerArt, Datenreihe],
	verbrauch_datenreihe: Datenreihe,
	smard: Smard,
	previous_realisiert: dict[ErzeugerArt, Datenreihe] | None = None,
) -> dict[ErzeugerArt, Datenreihe]:
	"""
	Berechnet die realisierte Erzeugung aus der maximal verfügbaren Erzeugung je Zeitschritt.

	Dispatch-Logik:
	1) Mindestleistung (MUSS) für regelbare Erzeuger
	2) Erneuerbare IMMER voll nutzen (keine Abregelung)
	3) Bei Unterdeckung: Regelbare hochfahren (mit Ramp-Limits)
	4) Bei Überschuss: Regelbare runterregeln (mit Ramp-Limits)
	"""

	# ==========================================================================
	# Vorbereitung: Zeitraster und Daten aufbereiten
	# ==========================================================================

	# Verbrauchsdaten auf gemeinsamen Zeitindex bringen
	verbrauch_nach_zeit = verbrauch_datenreihe.df.set_index("Datum von")
	if verbrauch_nach_zeit.index.has_duplicates:
		verbrauch_nach_zeit = verbrauch_nach_zeit.groupby(level=0).mean()

	zeitindex = verbrauch_nach_zeit.index
	anzahl_zeitschritte = len(zeitindex)
	verbrauch_werte = verbrauch_nach_zeit[verbrauch_datenreihe.art]

	# Alle Erzeuger-Daten auf denselben Zeitindex bringen
	max_verfuegbar_df = DataFrame(index=zeitindex)
	for erzeuger_art, datenreihe in max_available_datenreihen.items():
		erzeuger_nach_zeit = datenreihe.df.set_index("Datum von")
		if erzeuger_nach_zeit.index.has_duplicates:
			erzeuger_nach_zeit = erzeuger_nach_zeit.groupby(level=0).mean()
		erzeuger_werte = erzeuger_nach_zeit[erzeuger_art]
		angepasste_werte = erzeuger_werte.reindex(zeitindex)
		max_verfuegbar_df[erzeuger_art] = angepasste_werte.ffill().fillna(0.0)

	# Liste aller Erzeugerarten und Zuordnung zu Indizes
	alle_erzeuger = list(max_available_datenreihen.keys())
	anzahl_erzeuger = len(alle_erzeuger)
	erzeuger_zu_index = {art: i for i, art in enumerate(alle_erzeuger)}

	# ==========================================================================
	# Regulation-Werte holen und Erzeuger klassifizieren
	# ==========================================================================

	regulation_werte = numpy.zeros(anzahl_erzeuger, dtype=float64)
	for erzeuger_art in alle_erzeuger:
		erzeuger = smard.get_erzeuger(erzeuger_art)
		index = erzeuger_zu_index[erzeuger_art]
		regulation_werte[index] = float(erzeuger.art.regulierung)

	# Erneuerbare vs Regelbare trennen
	erneuerbare_indizes: list[int] = []
	regelbare_indizes: list[int] = []

	for index in range(anzahl_erzeuger):
		if regulation_werte[index] <= EPS:
			erneuerbare_indizes.append(index)
		else:
			regelbare_indizes.append(index)

	# Reihenfolge zum Hochfahren (nach Priorität)
	prioritaets_indizes: list[int] = []
	for erzeuger_art in PRIORITY_ORDER:
		if erzeuger_art in erzeuger_zu_index:
			index = erzeuger_zu_index[erzeuger_art]
			if regulation_werte[index] > EPS:
				prioritaets_indizes.append(index)

	prioritaets_set = set(prioritaets_indizes)
	restliche_regelbare = [index for index in regelbare_indizes if index not in prioritaets_set]

	hochfahr_reihenfolge = prioritaets_indizes + restliche_regelbare
	runterfahr_reihenfolge = list(reversed(hochfahr_reihenfolge))

	# ==========================================================================
	# Daten in numpy Arrays umwandeln (schneller für Berechnungen)
	# ==========================================================================

	max_verfuegbar_array = numpy.zeros((anzahl_zeitschritte, anzahl_erzeuger), dtype=float64)
	for index, erzeuger_art in enumerate(alle_erzeuger):
		max_verfuegbar_array[:, index] = max_verfuegbar_df[erzeuger_art].values.astype(float64)

	verbrauch_array = verbrauch_werte.values.astype(float64)

	# Vorheriger realisierter Zustand (für Ramp-Limits)
	vorherige_erzeugung = numpy.zeros(anzahl_erzeuger, dtype=float64)
	if previous_realisiert is not None:
		for erzeuger_art, datenreihe in previous_realisiert.items():
			if erzeuger_art in erzeuger_zu_index:
				index = erzeuger_zu_index[erzeuger_art]
				erzeuger_nach_zeit = datenreihe.df.set_index("Datum von")
				if erzeuger_nach_zeit.index.has_duplicates:
					erzeuger_nach_zeit = erzeuger_nach_zeit.groupby(level=0).mean()
				erzeuger_zeitreihe = erzeuger_nach_zeit[erzeuger_art]
				if len(erzeuger_zeitreihe) > 0:
					vorherige_erzeugung[index] = float(erzeuger_zeitreihe.iloc[-1])

	# ==========================================================================
	# Hauptberechnung: Zeitschritt für Zeitschritt
	# ==========================================================================

	ergebnis_array = numpy.zeros((anzahl_zeitschritte, anzahl_erzeuger), dtype=float64)

	# Arbeits-Arrays für jeden Zeitschritt
	aktuelle_erzeugung = numpy.zeros(anzahl_erzeuger, dtype=float64)
	mindest_erzeugung = numpy.zeros(anzahl_erzeuger, dtype=float64)

	print(f"Berechne {anzahl_zeitschritte} Zeitschritte...")
	start_zeit = time.time()
	fortschritt_intervall = 50000

	anzahl_ueberschuss_schritte = 0
	anzahl_unterdeckungs_schritte = 0

	# Zeitschrittdauer für "Datum bis" berechnen
	if anzahl_zeitschritte >= 2:
		zeitschritt_dauer = zeitindex[1] - zeitindex[0]
	else:
		zeitschritt_dauer = Timedelta(minutes=15)

	for zeitschritt_index in range(anzahl_zeitschritte):
		max_verfuegbar_jetzt = max_verfuegbar_array[zeitschritt_index]
		verbrauch_jetzt = float(verbrauch_array[zeitschritt_index])

		aktuelle_erzeugung.fill(0.0)
		mindest_erzeugung.fill(0.0)

		# ---------------------------------------------------------------------
		# Schritt 1: Mindestleistung (MUSS) für regelbare Erzeuger berechnen
		# ---------------------------------------------------------------------
		for index in regelbare_indizes:
			regulation = regulation_werte[index]
			vorherige_leistung = vorherige_erzeugung[index]
			max_verfuegbar = max_verfuegbar_jetzt[index]

			if max_verfuegbar < 0.0:
				max_verfuegbar = 0.0

			# Mindestleistung nur für teilweise regelbare Erzeuger (0 < reg < 1)
			if (regulation > EPS) and (regulation < 1.0 - EPS):
				mindest_leistung = vorherige_leistung * (1.0 - regulation)
			else:
				mindest_leistung = 0.0

			# Sicherstellen dass Mindestleistung im gültigen Bereich liegt
			if mindest_leistung < 0.0:
				mindest_leistung = 0.0
			if mindest_leistung > max_verfuegbar:
				mindest_leistung = max_verfuegbar

			mindest_erzeugung[index] = mindest_leistung
			aktuelle_erzeugung[index] = mindest_leistung

		# ---------------------------------------------------------------------
		# Schritt 2: Erneuerbare IMMER voll einsetzen (keine Abregelung)
		# ---------------------------------------------------------------------
		if len(erneuerbare_indizes) > 0:
			erneuerbare_verfuegbar = max_verfuegbar_jetzt[erneuerbare_indizes].copy()
			erneuerbare_verfuegbar[erneuerbare_verfuegbar < 0.0] = 0.0
			aktuelle_erzeugung[erneuerbare_indizes] = erneuerbare_verfuegbar

		# Lücke oder Überschuss berechnen: Verbrauch - (MUSS + Erneuerbare)
		fehlende_leistung = verbrauch_jetzt - float(aktuelle_erzeugung.sum())

		if fehlende_leistung <= 0.0:
			anzahl_ueberschuss_schritte += 1
		else:
			anzahl_unterdeckungs_schritte += 1

		# ---------------------------------------------------------------------
		# Schritt 3: Bei Unterdeckung - Regelbare hochfahren (mit Ramp-Limits)
		# ---------------------------------------------------------------------
		if fehlende_leistung > 0.0:
			for index in hochfahr_reihenfolge:
				if fehlende_leistung <= 0.0:
					break

				regulation = regulation_werte[index]
				max_verfuegbar = max_verfuegbar_jetzt[index]
				if max_verfuegbar < 0.0:
					max_verfuegbar = 0.0

				vorherige_leistung = vorherige_erzeugung[index]
				max_aenderung = 2.0 * regulation * max_verfuegbar

				# Berechne erlaubten Bereich durch Ramp-Limits
				unteres_limit = vorherige_leistung - max_aenderung
				if unteres_limit < 0.0:
					unteres_limit = 0.0

				oberes_limit = vorherige_leistung + max_aenderung
				if oberes_limit > max_verfuegbar:
					oberes_limit = max_verfuegbar

				# Mindestleistung muss eingehalten werden
				if unteres_limit < mindest_erzeugung[index]:
					unteres_limit = mindest_erzeugung[index]

				# Falls wir unter dem unteren Limit sind, zuerst darauf anheben
				if aktuelle_erzeugung[index] < unteres_limit:
					zusaetzlich_noetig = unteres_limit - aktuelle_erzeugung[index]
					aktuelle_erzeugung[index] = unteres_limit
					fehlende_leistung -= zusaetzlich_noetig
					if fehlende_leistung <= 0.0:
						break

				# Wie viel können wir noch hochfahren?
				verfuegbarer_spielraum = oberes_limit - aktuelle_erzeugung[index]
				if verfuegbarer_spielraum <= 0.0:
					continue

				# Fülle die Lücke soweit möglich
				zufuegen = (
					verfuegbarer_spielraum
					if verfuegbarer_spielraum <= fehlende_leistung
					else fehlende_leistung
				)
				aktuelle_erzeugung[index] += zufuegen
				fehlende_leistung -= zufuegen

		# ---------------------------------------------------------------------
		# Schritt 4: Bei Überschuss - Regelbare runterregeln (mit Ramp-Limits)
		#            Erneuerbare werden NICHT abgeregelt!
		# ---------------------------------------------------------------------
		if fehlende_leistung < -1e-9:
			ueberschuss = -fehlende_leistung

			# Regelbare Richtung 0 fahren (mit Ramp-Limits)
			for index in runterfahr_reihenfolge:
				if ueberschuss <= 0.0:
					break

				regulation = regulation_werte[index]
				max_verfuegbar = max_verfuegbar_jetzt[index]
				if max_verfuegbar < 0.0:
					max_verfuegbar = 0.0

				vorherige_leistung = vorherige_erzeugung[index]
				max_aenderung = 2.0 * regulation * max_verfuegbar

				# Unteres Limit durch Ramp-Down (Ziel ist 0, nicht Mindestleistung)
				unteres_limit = vorherige_leistung - max_aenderung
				if unteres_limit < 0.0:
					unteres_limit = 0.0

				# Wie viel können wir reduzieren?
				reduzierbarer_betrag = aktuelle_erzeugung[index] - unteres_limit
				if reduzierbarer_betrag <= 0.0:
					continue

				# Reduziere soweit wie möglich
				reduktion = (
					reduzierbarer_betrag if reduzierbarer_betrag <= ueberschuss else ueberschuss
				)
				aktuelle_erzeugung[index] -= reduktion
				ueberschuss -= reduktion

			# Überschuss bleibt bestehen - KEINE Abregelung der Erneuerbaren
			fehlende_leistung = -ueberschuss

		# ---------------------------------------------------------------------
		# Ergebnis speichern und für nächsten Zeitschritt merken
		# ---------------------------------------------------------------------
		aktuelle_erzeugung[aktuelle_erzeugung < 0.0] = 0.0
		ergebnis_array[zeitschritt_index, :] = aktuelle_erzeugung
		vorherige_erzeugung[:] = aktuelle_erzeugung

		# Fortschritt ausgeben
		if (zeitschritt_index + 1) % fortschritt_intervall == 0:
			vergangene_zeit = time.time() - start_zeit
			fortschritt_prozent = ((zeitschritt_index + 1) / anzahl_zeitschritte) * 100
			durchschnitt_pro_schritt = vergangene_zeit / (zeitschritt_index + 1)
			geschaetzte_restzeit = durchschnitt_pro_schritt * (
				anzahl_zeitschritte - (zeitschritt_index + 1)
			)
			print(
				f"  Fortschritt: {zeitschritt_index + 1}/{anzahl_zeitschritte} ({fortschritt_prozent:.1f}%) | "
				f"Zeit: {vergangene_zeit:.1f}s | Verbleibend: {geschaetzte_restzeit:.1f}s"
			)

	berechnungs_dauer = time.time() - start_zeit
	print(f"Berechnung abgeschlossen in {berechnungs_dauer:.2f} Sekunden")
	print(
		f"  Überschuss-Zeitschritte: {anzahl_ueberschuss_schritte} "
		f"({100 * anzahl_ueberschuss_schritte / anzahl_zeitschritte:.1f}%)"
	)
	print(
		f"  Unterdeckungs-Zeitschritte: {anzahl_unterdeckungs_schritte} "
		f"({100 * anzahl_unterdeckungs_schritte / anzahl_zeitschritte:.1f}%)"
	)

	# ==========================================================================
	# Ergebnisse zurück in Datenreihen umwandeln
	# ==========================================================================

	ergebnis_dict: dict[ErzeugerArt, Datenreihe] = {}
	datum_von_array = zeitindex.to_numpy()
	datum_bis_array = (zeitindex + zeitschritt_dauer).to_numpy()

	for index, erzeuger_art in enumerate(alle_erzeuger):
		df = DataFrame()
		df["Datum von"] = datum_von_array
		df["Datum bis"] = datum_bis_array
		df[erzeuger_art] = ergebnis_array[:, index]
		ergebnis_dict[erzeuger_art] = Datenreihe(erzeuger_art, df)

	return ergebnis_dict


def apply_stack_model_to_ausbaupfad(
	ausbaupfad: Ausbaupfad,
	smard: Smard,
	verbrauch_art: VerbraucherArt = VerbraucherArt.Netzlast,
) -> dict[ErzeugerArt, Datenreihe]:
	"""
	Wendet den Stack-Modell-Algorithmus auf einen Ausbaupfad an.
	"""

	# Maximal verfügbare Erzeugung aus Prognose-Zeitreihen extrahieren
	max_available_datenreihen: dict[ErzeugerArt, Datenreihe] = {}
	for datenreihe in ausbaupfad.prognose_erzeuger:
		art = datenreihe.art
		df = datenreihe.df[["Datum von", "Datum bis", art]].copy()
		max_available_datenreihen[art] = Datenreihe(art, df)

	# Verbrauchsreihe wählen
	verbrauch_datenreihe = None
	if ausbaupfad.prognose_verbraucher:
		for dr in ausbaupfad.prognose_verbraucher:
			if dr.art == verbrauch_art:
				verbrauch_datenreihe = dr
				break
		if verbrauch_datenreihe is None:
			verbrauch_datenreihe = ausbaupfad.prognose_verbraucher[0]

	if verbrauch_datenreihe is None:
		verbrauch_datenreihe = smard.get_verbraucher(verbrauch_art).verbraucht

	# Startzustand aus SMARD (prev_realized)
	previous_realisiert: dict[ErzeugerArt, Datenreihe] = {}
	for art in max_available_datenreihen.keys():
		erzeuger = smard.get_erzeuger(art)
		previous_realisiert[art] = erzeuger.realisiert

	return calculate_realized_generation(
		max_available_datenreihen=max_available_datenreihen,
		verbrauch_datenreihe=verbrauch_datenreihe,
		smard=smard,
		previous_realisiert=previous_realisiert,
	)
