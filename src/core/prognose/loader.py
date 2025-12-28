import logging
from pathlib import Path

import config
from core.data import loader
from core.prognose.datenpunkt import ErzeugerDatenpunkt, VerbraucherDatenpunkt
from core.setup.erzeuger import ErzeugerArt
from core.setup.verbraucher import VerbraucherArt
from core.simulation.event import EventDatenpunkt, EventType

# Temporär
type Ausbau = tuple[list[ErzeugerDatenpunkt], list[VerbraucherDatenpunkt], list[EventDatenpunkt]]


# Lädt einen einzelnen Ausbaupfad
def load(path: Path) -> Ausbau:
	logging.info(f"Ausbaupfad wird gelesen: {path}")

	# Listen anlegen
	ereignisse: list[EventDatenpunkt] = []
	installiert: list[ErzeugerDatenpunkt] = []
	verbraucht: list[VerbraucherDatenpunkt] = []

	# Ereignisse laden
	joined = path.joinpath("ereignisse.csv")

	if joined.is_file():
		for _, row in loader.read_csv(joined).iterrows():
			anfang = row["Datum von"]
			ende = row["Datum bis"]
			art = EventType(row["Art"])
			intensitaet = row["Intensität"]

			ereignisse.append(EventDatenpunkt(anfang, ende, art, intensitaet))

	# Installiert laden
	joined = path.joinpath("installiert.csv")

	if joined.is_file():
		for _, row in loader.read_csv(joined).iterrows():
			datum = row["Datum"]
			art = ErzeugerArt(row["Art"])
			wert = row["Wert"]

			installiert.append(ErzeugerDatenpunkt(art, datum, wert))

	# Installiert laden
	joined = path.joinpath("verbraucht.csv")

	if joined.is_file():
		for _, row in loader.read_csv(joined).iterrows():
			datum = row["Datum"]
			art = VerbraucherArt(row["Art"])
			wert = row["Wert"]

			verbraucht.append(VerbraucherDatenpunkt(art, datum, wert))

	# Listen zurückgeben
	return installiert, verbraucht, ereignisse


# Lädt alle verfügbaren Ausbaupfade
def load_all() -> dict[str, Ausbau]:
	ausbaupfade: dict[str, Ausbau] = {}

	# Alle Unterverzeichnisse einzeln laden
	for path in config.AUSBAU_DIR.iterdir():
		if path.is_dir():
			ausbaupfade[path.name] = load(path)

	# Ausbaupfade zurückgeben
	return ausbaupfade
