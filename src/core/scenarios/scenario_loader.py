"""
CSV-basierter Szenario-Loader.

Lädt Erzeuger-, Verbraucher- und Event-Datenpunkte aus CSV-Dateien.
Jedes Szenario liegt in einem eigenen Ordner mit CSV-Dateien:
- erzeuger.csv (erforderlich)
- verbraucher.csv (erforderlich)
- events.csv (optional)

CSV-Format:
- erzeuger.csv: Datum, ErzeugerArt, Installiert
- verbraucher.csv: Datum, VerbraucherArt, Verbrauch
- events.csv: DatumVon, DatumBis, EventTyp, Intensitaet

Wichtig:
- Datum sollte die erste Spalte sein (empfohlen)
- In verbraucher.csv sind nur noch FESTE Zahlenwerte erlaubt (kein SMARD_MEAN o.ä.).
- events.csv ist optional - wenn nicht vorhanden, werden keine Events angewendet.
"""

import datetime
import re
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from core.prognose.datenpunkt import ErzeugerDatenpunkt, VerbraucherDatenpunkt
from core.setup.smard import Smard
from core.simulation.event import EventDatenpunkt, EventType
from core.types import ErzeugerArt, VerbraucherArt

SCENARIOS_DIR = Path(__file__).parent


def load_scenario(
	szenario_name: str,
	smard: Smard,  # API-kompatibel; wird hier nicht genutzt
) -> Tuple[List[ErzeugerDatenpunkt], List[VerbraucherDatenpunkt], List[EventDatenpunkt]]:
	"""
	Lädt ein Szenario aus CSV-Dateien.

	Args:
	    szenario_name: Name des Szenario-Ordners (z.B. "default")
	    smard: SMARD-Datenquelle (für API-Kompatibilität, wird nicht genutzt)

	Returns:
	    Tuple von (erzeuger_datenpunkte, verbraucher_datenpunkte, event_datenpunkte)
	"""
	_ = smard

	szenario_ordner = SCENARIOS_DIR / szenario_name
	if not szenario_ordner.exists():
		raise FileNotFoundError(f"Szenario-Ordner nicht gefunden: {szenario_ordner}")

	erzeuger_csv = szenario_ordner / "erzeuger.csv"
	verbraucher_csv = szenario_ordner / "verbraucher.csv"
	events_csv = szenario_ordner / "events.csv"

	erzeuger_datenpunkte = _lade_erzeuger_csv(erzeuger_csv)
	verbraucher_datenpunkte = _lade_verbraucher_csv(verbraucher_csv)
	event_datenpunkte = _lade_events_csv(events_csv)

	# Deterministische Reihenfolge
	erzeuger_datenpunkte.sort(key=lambda d: (d.art.value, d.datetime))
	verbraucher_datenpunkte.sort(key=lambda d: (d.art.value, d.datetime))
	event_datenpunkte.sort(key=lambda d: d.datum_von)

	return erzeuger_datenpunkte, verbraucher_datenpunkte, event_datenpunkte


def _lade_erzeuger_csv(csv_pfad: Path) -> List[ErzeugerDatenpunkt]:
	if not csv_pfad.exists():
		raise FileNotFoundError(f"Erzeuger-CSV nicht gefunden: {csv_pfad}")

	# utf-8-sig frisst BOM weg (Excel!)
	df = pd.read_csv(csv_pfad, dtype=str, keep_default_na=False, encoding="utf-8-sig")
	df.columns = df.columns.str.strip()

	erwartete_spalten = {"ErzeugerArt", "Datum", "Installiert"}
	if not erwartete_spalten.issubset(set(df.columns)):
		raise ValueError(
			f"CSV muss Spalten {erwartete_spalten} enthalten. Gefunden: {set(df.columns)}"
		)

	datenpunkte: List[ErzeugerDatenpunkt] = []

	for idx, zeile in df.iterrows():
		# Datum (sollte erste Spalte sein, aber flexibel)
		datum_string = str(zeile["Datum"]).strip()
		datum = _parse_datum(datum_string)

		# ErzeugerArt
		art_string = str(zeile["ErzeugerArt"]).strip()
		erzeuger_art = _string_zu_erzeuger_art(art_string)

		# Installierte Leistung
		installiert_raw = str(zeile["Installiert"]).strip()
		installiert = int(round(_parse_number(installiert_raw, "Installiert", idx)))

		datenpunkte.append(
			ErzeugerDatenpunkt(
				art=erzeuger_art,
				datetime=datum,
				installiert=installiert,
			)
		)

	return datenpunkte


def _lade_verbraucher_csv(csv_pfad: Path) -> List[VerbraucherDatenpunkt]:
	if not csv_pfad.exists():
		raise FileNotFoundError(f"Verbraucher-CSV nicht gefunden: {csv_pfad}")

	df = pd.read_csv(csv_pfad, dtype=str, keep_default_na=False, encoding="utf-8-sig")
	df.columns = df.columns.str.strip()

	erwartete_spalten = {"VerbraucherArt", "Datum", "Verbrauch"}
	if not erwartete_spalten.issubset(set(df.columns)):
		raise ValueError(
			f"CSV muss Spalten {erwartete_spalten} enthalten. Gefunden: {set(df.columns)}"
		)

	datenpunkte: List[VerbraucherDatenpunkt] = []

	for idx, zeile in df.iterrows():
		# Datum (sollte erste Spalte sein, aber flexibel)
		datum_string = str(zeile["Datum"]).strip()
		datum = _parse_datum(datum_string)

		# VerbraucherArt
		art_string = str(zeile["VerbraucherArt"]).strip()
		verbraucher_art = _string_zu_verbraucher_art(art_string)

		# Verbrauch
		verbrauch_raw = str(zeile["Verbrauch"]).strip()
		if not verbrauch_raw:
			raise ValueError(f"Leerer Verbrauch in Zeile {idx + 2} ({csv_pfad.name}).")

		# Nur feste Zahlen: wenn jemand doch SMARD_MEAN reinschreibt -> harte Fehlermeldung
		if verbrauch_raw.upper() == "SMARD_MEAN":
			raise ValueError(
				f"Ungültiger Wert 'SMARD_MEAN' in {csv_pfad.name} Zeile {idx + 2}. "
				f"Erlaubt sind nur feste Zahlenwerte."
			)

		verbrauch = float(_parse_number(verbrauch_raw, "Verbrauch", idx))

		datenpunkte.append(
			VerbraucherDatenpunkt(
				art=verbraucher_art,
				datetime=datum,
				verbraucht=verbrauch,
			)
		)

	return datenpunkte


def _lade_events_csv(csv_pfad: Path) -> List[EventDatenpunkt]:
	"""
	Lädt Event-Datenpunkte aus einer CSV-Datei.

	CSV-Format:
	    DatumVon,DatumBis,EventTyp,Intensitaet
	    2030-06-01,2030-08-31,drought,0.8

	Args:
	    csv_pfad: Pfad zur events.csv

	Returns:
	    Liste von EventDatenpunkt-Objekten (leer wenn Datei nicht existiert)
	"""
	# Events sind optional - wenn Datei nicht existiert, leere Liste zurückgeben
	if not csv_pfad.exists():
		return []

	df = pd.read_csv(csv_pfad, dtype=str, keep_default_na=False, encoding="utf-8-sig")
	df.columns = df.columns.str.strip()

	# Prüfen ob Datei leer ist (nur Header oder komplett leer)
	if df.empty:
		return []

	erwartete_spalten = {"DatumVon", "DatumBis", "EventTyp", "Intensitaet"}
	if not erwartete_spalten.issubset(set(df.columns)):
		raise ValueError(
			f"events.csv muss Spalten {erwartete_spalten} enthalten. Gefunden: {set(df.columns)}"
		)

	datenpunkte: List[EventDatenpunkt] = []

	for idx, zeile in df.iterrows():
		# DatumVon
		datum_von_string = str(zeile["DatumVon"]).strip()
		datum_von = _parse_datum(datum_von_string)

		# DatumBis
		datum_bis_string = str(zeile["DatumBis"]).strip()
		datum_bis = _parse_datum(datum_bis_string)

		# Validierung: DatumBis muss nach DatumVon sein
		if datum_bis <= datum_von:
			raise ValueError(
				f"DatumBis ({datum_bis_string}) muss nach DatumVon ({datum_von_string}) sein "
				f"in Zeile {idx + 2}"
			)

		# EventTyp
		event_typ_string = str(zeile["EventTyp"]).strip().lower()
		event_typ = _string_zu_event_typ(event_typ_string, idx)

		# Intensitaet (0.0 bis 1.0)
		intensitaet_raw = str(zeile["Intensitaet"]).strip()
		intensitaet = float(_parse_number(intensitaet_raw, "Intensitaet", idx))

		# Validierung: Intensität zwischen 0 und 1
		if intensitaet < 0.0 or intensitaet > 1.0:
			raise ValueError(
				f"Intensitaet muss zwischen 0.0 und 1.0 liegen, "
				f"gefunden: {intensitaet} in Zeile {idx + 2}"
			)

		datenpunkte.append(
			EventDatenpunkt(
				datum_von=datum_von,
				datum_bis=datum_bis,
				event_typ=event_typ,
				intensitaet=intensitaet,
			)
		)

	return datenpunkte


def _string_zu_event_typ(typ_string: str, row_idx: int) -> EventType:
	"""Konvertiert einen String zu EventType Enum."""
	mapping = {
		"drought": EventType.drought,
		"dürre": EventType.drought,
		"duerre": EventType.drought,
	}

	if typ_string in mapping:
		return mapping[typ_string]

	# Fallback: Direkt als Enum-Wert versuchen
	for event_typ in EventType:
		if event_typ.value == typ_string or event_typ.name == typ_string:
			return event_typ

	raise ValueError(
		f"Unbekannter EventTyp: '{typ_string}' in Zeile {row_idx + 2}. "
		f"Erlaubt: {[e.value for e in EventType]}"
	)


_DE_THOUSANDS = re.compile(r"^\d{1,3}(\.\d{3})+(,\d+)?$")  # 55.000 oder 1.234.567,89
_US_THOUSANDS = re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$")  # 55,000 oder 1,234,567.89


def _parse_number(value: str, field: str, row_idx: int) -> float:
	"""
	Robustes Parsen von Zahlen aus CSV:
	- erlaubt Unterstriche/Spaces: 130_000 / "130 000"
	- erlaubt DE-Format: 55.000 / 1.234.567,89
	- erlaubt US-Format: 55,000 / 1,234,567.89
	- erlaubt Dezimalkomma: 12,34
	"""
	raw = str(value).strip().replace(" ", "").replace("_", "")

	if _DE_THOUSANDS.match(raw):
		# Tausenderpunkte raus, Dezimalkomma -> Punkt
		raw = raw.replace(".", "").replace(",", ".")
	elif _US_THOUSANDS.match(raw):
		# Tausenderkommas raus
		raw = raw.replace(",", "")
	else:
		# Wenn nur ein Komma und kein Punkt: Dezimalkomma
		if raw.count(",") == 1 and raw.count(".") == 0:
			raw = raw.replace(",", ".")

	try:
		return float(raw)
	except ValueError:
		raise ValueError(
			f"Ungültiger Zahlenwert für '{field}' in Zeile {row_idx + 2}: '{value}'. "
			f"Beispiele: 55000 | 55.000 | 55,000 | 12,34"
		)


def _parse_datum(datum_string: str) -> datetime.datetime:
	try:
		return datetime.datetime.fromisoformat(datum_string)
	except ValueError:
		raise ValueError(
			f"Ungültiges Datumsformat: '{datum_string}'. Erwartet: YYYY-MM-DD (z.B. 2030-01-01)"
		)


def _string_zu_erzeuger_art(art_string: str) -> ErzeugerArt:
	mapping = {
		"Photovoltaik": ErzeugerArt.Photovoltaik,
		"PV": ErzeugerArt.Photovoltaik,
		"Wind Onshore": ErzeugerArt.WindOnshore,
		"WindOnshore": ErzeugerArt.WindOnshore,
		"Wind Offshore": ErzeugerArt.WindOffshore,
		"WindOffshore": ErzeugerArt.WindOffshore,
		"Wasserkraft": ErzeugerArt.Wasserkraft,
		"Biomasse": ErzeugerArt.Biomasse,
		"Pumpspeicher": ErzeugerArt.Pumpspeicher,
		"Sonstige Erneuerbare": ErzeugerArt.SonstigeErneuerbare,
		"SonstigeErneuerbare": ErzeugerArt.SonstigeErneuerbare,
		"Erdgas": ErzeugerArt.Erdgas,
		"Steinkohle": ErzeugerArt.Steinkohle,
		"Braunkohle": ErzeugerArt.Braunkohle,
		"Kernenergie": ErzeugerArt.Kernenergie,
		"Sonstige Konventionelle": ErzeugerArt.SonstigeKonventionelle,
		"SonstigeKonventionelle": ErzeugerArt.SonstigeKonventionelle,
	}
	if art_string in mapping:
		return mapping[art_string]
	for art in ErzeugerArt:
		if art.value == art_string or art.name == art_string:
			return art
	raise ValueError(f"Unbekannte ErzeugerArt: '{art_string}'")


def _string_zu_verbraucher_art(art_string: str) -> VerbraucherArt:
	mapping = {
		"Netzlast": VerbraucherArt.Netzlast,
		"Netzlast inkl. Pumpspeicher": VerbraucherArt.NetzlastInklPumpspeicher,
		"NetzlastInklPumpspeicher": VerbraucherArt.NetzlastInklPumpspeicher,
		"Pumpspeicher": VerbraucherArt.Pumpspeicher,
		"Residuallast": VerbraucherArt.Residuallast,
	}
	if art_string in mapping:
		return mapping[art_string]
	for art in VerbraucherArt:
		if art.value == art_string or art.name == art_string:
			return art
	raise ValueError(f"Unbekannte VerbraucherArt: '{art_string}'")
