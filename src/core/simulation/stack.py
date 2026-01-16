import numpy
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


# Berechnet die realisierte Erzeugung aus der maximal verfügbaren Erzeugung je Zeitschritt
def calculate_realized(
	max_available_datenreihen: dict[ErzeugerArt, Datenreihe[ErzeugerArt]],
	verbrauch_datenreihe: Datenreihe[VerbraucherArt],
	smard: Smard,
	previous_realisiert: dict[ErzeugerArt, Datenreihe[ErzeugerArt]],
) -> tuple[dict[ErzeugerArt, Datenreihe[ErzeugerArt]], Datenreihe[str]]:
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
		erzeuge_werte = erzeuger_nach_zeit[erzeuger_art]
		max_verfuegbar_df[erzeuger_art] = erzeuge_werte.reindex(zeitindex).ffill().fillna(0.0)

	alle_erzeuger = list(max_available_datenreihen.keys())
	anzahl_erzeuger = len(alle_erzeuger)
	erzeuger_zu_index = {art: i for i, art in enumerate(alle_erzeuger)}

	# Regulation-Werte
	regulation_werte = numpy.zeros(anzahl_erzeuger, dtype=float)
	for erzeuger_art in alle_erzeuger:
		erzeuger = smard.get_erzeuger(erzeuger_art)
		index = erzeuger_zu_index[erzeuger_art]
		regulation_werte[index] = float(erzeuger.art.regulierung)

	# Erneuerbare vs. Regelbare
	erneuerbare_indizes = [i for i in range(anzahl_erzeuger) if regulation_werte[i] == 0]
	regelbare_indizes = [i for i in range(anzahl_erzeuger) if regulation_werte[i] != 0]

	# Hoch-/Runterfahr-Reihenfolge
	prioritaets_indizes = [
		erzeuger_zu_index[art]
		for art in PRIORITY_ORDER
		if art in erzeuger_zu_index and regulation_werte[erzeuger_zu_index[art]] != 0
	]
	restliche_regelbare = [i for i in regelbare_indizes if i not in prioritaets_indizes]
	hochfahr_reihenfolge = prioritaets_indizes + restliche_regelbare
	runterfahr_reihenfolge = list(reversed(hochfahr_reihenfolge))

	# Numpy-Arrays für schnelle Berechnung
	max_verfuegbar_array = numpy.zeros((anzahl_zeitschritte, anzahl_erzeuger), dtype=float)
	for index, erzeuger_art in enumerate(alle_erzeuger):
		max_verfuegbar_array[:, index] = max_verfuegbar_df[erzeuger_art].to_numpy().astype(float)
	verbrauch_array = verbrauch_werte.to_numpy().astype(float)

	vorherige_erzeugung = numpy.zeros(anzahl_erzeuger, dtype=float)
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

	ergebnis_array = numpy.zeros((anzahl_zeitschritte, anzahl_erzeuger), dtype=float)
	ueberschuss_array = numpy.zeros(anzahl_zeitschritte, dtype=float)

	aktuelle_erzeugung = numpy.zeros(anzahl_erzeuger, dtype=float)
	mindest_erzeugung = numpy.zeros(anzahl_erzeuger, dtype=float)

	if anzahl_zeitschritte >= 2:
		zeitschritt_dauer = zeitindex[1] - zeitindex[0]
	else:
		zeitschritt_dauer = Timedelta(minutes=15)

	for z in range(anzahl_zeitschritte):
		max_now = max_verfuegbar_array[z]
		verbrauch_now = float(verbrauch_array[z])

		aktuelle_erzeugung.fill(0.0)
		mindest_erzeugung.fill(0.0)

		# Schritt 1: Mindestleistung
		for i in regelbare_indizes:
			reg = regulation_werte[i]
			prev = vorherige_erzeugung[i]
			max_val = max_now[i] if max_now[i] > 0 else 0.0
			if 0 < reg < 1:
				min_leistung = prev * (1 - reg)
			else:
				min_leistung = 0.0
			min_leistung = max(0.0, min(min_leistung, max_val))
			mindest_erzeugung[i] = min_leistung
			aktuelle_erzeugung[i] = min_leistung

		# Schritt 2: Erneuerbare voll einsetzen
		if erneuerbare_indizes:
			erneuerbar_now = max_now[erneuerbare_indizes].copy()
			erneuerbar_now[erneuerbar_now < 0] = 0
			aktuelle_erzeugung[erneuerbare_indizes] = erneuerbar_now

		fehlende_leistung = verbrauch_now - float(aktuelle_erzeugung.sum())

		# Schritt 3: Unterdeckung hochfahren
		if fehlende_leistung > 0:
			for i in hochfahr_reihenfolge:
				if fehlende_leistung <= 0:
					break
				reg = regulation_werte[i]
				max_val = max_now[i] if max_now[i] > 0 else 0.0
				prev = vorherige_erzeugung[i]
				max_aenderung = 2.0 * reg * max_val

				unten = max(prev - max_aenderung, mindest_erzeugung[i])
				oben = min(prev + max_aenderung, max_val)

				if aktuelle_erzeugung[i] < unten:
					zusaetzlich = unten - aktuelle_erzeugung[i]
					aktuelle_erzeugung[i] = unten
					fehlende_leistung -= zusaetzlich
					if fehlende_leistung <= 0:
						break

				spielraum = oben - aktuelle_erzeugung[i]
				if spielraum <= 0:
					continue
				zufuegen = min(spielraum, fehlende_leistung)
				aktuelle_erzeugung[i] += zufuegen
				fehlende_leistung -= zufuegen

		# Schritt 4: Überschuss runterregeln
		ueberschuss = 0.0
		if fehlende_leistung < -1e-9:
			ueberschuss = -fehlende_leistung
			for i in runterfahr_reihenfolge:
				if ueberschuss <= 0:
					break
				reg = regulation_werte[i]
				max_val = max_now[i] if max_now[i] > 0 else 0.0
				prev = vorherige_erzeugung[i]
				max_aenderung = 2.0 * reg * max_val

				unten = max(prev - max_aenderung, 0.0)
				reduzierbar = aktuelle_erzeugung[i] - unten
				if reduzierbar <= 0:
					continue
				reduktion = min(reduzierbar, ueberschuss)
				aktuelle_erzeugung[i] -= reduktion
				ueberschuss -= reduktion

		ueberschuss_array[z] = max(0.0, ueberschuss)

		# Ergebnis speichern
		aktuelle_erzeugung[aktuelle_erzeugung < 0] = 0
		ergebnis_array[z, :] = aktuelle_erzeugung
		vorherige_erzeugung[:] = aktuelle_erzeugung

	datum_von_array = zeitindex.to_numpy()
	datum_bis_array = (zeitindex + zeitschritt_dauer).to_numpy()

	ergebnis_dict: dict[ErzeugerArt, Datenreihe[ErzeugerArt]] = {}
	for i, art in enumerate(alle_erzeuger):
		df = DataFrame()
		df["Datum von"] = datum_von_array
		df["Datum bis"] = datum_bis_array
		df[art] = ergebnis_array[:, i]
		ergebnis_dict[art] = Datenreihe(art, df)

	# Überschuss-Datenreihe
	ueberschuss_df = DataFrame()
	ueberschuss_df["Datum von"] = datum_von_array
	ueberschuss_df["Datum bis"] = datum_bis_array
	ueberschuss_df["Überschuss"] = ueberschuss_array
	ueberschuss_reihe = Datenreihe("Überschuss", ueberschuss_df)

	return ergebnis_dict, ueberschuss_reihe


# Wendet den Stack-Modell-Algorithmus auf einen Ausbaupfad an
def apply_stack_model(
	ausbaupfad: Ausbaupfad,
	smard: Smard,
	verbrauch_art: VerbraucherArt = VerbraucherArt.Netzlast,
) -> tuple[dict[ErzeugerArt, Datenreihe[ErzeugerArt]], Datenreihe[str]]:
	# Maximal verfügbare Erzeugung aus Prognose-Zeitreihen extrahieren
	max_available_datenreihen: dict[ErzeugerArt, Datenreihe[ErzeugerArt]] = {}
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
	previous_realisiert: dict[ErzeugerArt, Datenreihe[ErzeugerArt]] = {}
	for art in max_available_datenreihen.keys():
		erzeuger = smard.get_erzeuger(art)
		previous_realisiert[art] = erzeuger.realisiert

	return calculate_realized(
		max_available_datenreihen=max_available_datenreihen,
		verbrauch_datenreihe=verbrauch_datenreihe,
		smard=smard,
		previous_realisiert=previous_realisiert,
	)
