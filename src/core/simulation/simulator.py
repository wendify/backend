from typing import Dict, List

from core.prognose.loader import Ereignis
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.simulation.event import create_event_from_type
from core.simulation.impact import calculate_impact_factor


def apply_events_to_realized(
	realisiert_datenreihen: Dict[ErzeugerArt, Datenreihe],
	events: List[Ereignis],
) -> Dict[ErzeugerArt, Datenreihe]:
	"""
	Wendet Events auf die realisierte Erzeugung an (nur im jeweiligen Zeitbereich).

	Für jeden EventDatenpunkt wird der Impact-Faktor auf alle Zeitpunkte
	innerhalb [datum_von, datum_bis) angewendet.

	Args:
		realisiert_datenreihen: Dict von ErzeugerArt zu Datenreihe mit realisierter Erzeugung
		events: Liste von EventDatenpunkt mit Zeitbereichen und Intensitäten

	Returns:
		Neues Dict mit modifizierten Datenreihen (Original bleibt unverändert)
	"""
	# Wenn keine Events, Original zurückgeben
	if not events:
		return realisiert_datenreihen

	# Kopie erstellen um Original nicht zu verändern
	ergebnis: Dict[ErzeugerArt, Datenreihe] = {}

	for erzeuger_art, original_datenreihe in realisiert_datenreihen.items():
		# DataFrame kopieren
		df = original_datenreihe.df.copy()

		# Für jeden Event
		for event in events:
			# SimulationEvent erstellen
			simulation_event = create_event_from_type(event.art, event.intensitaet)

			# Zeitbereich filtern: datum_von <= Datum < datum_bis
			datum_spalte = df["Datum von"]

			# Maske für Zeitbereich erstellen
			in_zeitbereich = (datum_spalte >= event.anfang) & (datum_spalte < event.ende)

			# Anzahl betroffener Zeitschritte
			anzahl_betroffen = in_zeitbereich.sum()

			if anzahl_betroffen == 0:
				continue

			# Impact-Faktor EINMAL berechnen (ist konstant für Event + ErzeugerArt)
			impact_factor = calculate_impact_factor(simulation_event, erzeuger_art)

			# Vektorisiert multiplizieren (SCHNELL!)
			df.loc[in_zeitbereich, erzeuger_art] *= impact_factor

		# Neue Datenreihe erstellen
		ergebnis[erzeuger_art] = Datenreihe(erzeuger_art, df)

	return ergebnis
