import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import config
from core.data import loader
from core.setup.erzeuger import ErzeugerArt
from core.setup.verbraucher import VerbraucherArt
from core.simulation.event import EreignisArt


# Eine Zeile von Ausbaupfad-Ereignissen
@dataclass
class Ereignis:
	anfang: datetime
	ende: datetime
	art: EreignisArt
	intensitaet: float


# Eine Zeile von Ausbaupfad-Installationen
@dataclass
class Installation:
	datum: datetime
	art: ErzeugerArt
	wert: float


# Eine Zeile von Ausbaupfad-Verbräuchen
@dataclass
class Verbrauch:
	datum: datetime
	art: VerbraucherArt
	wert: float


# Temporär
type Ausbau = tuple[list[Ereignis], list[Installation], list[Verbrauch]]


# Lädt einen einzelnen Ausbaupfad
def load(path: Path) -> Ausbau:
	logging.info(f"Ausbaupfad wird gelesen: {path}")

	# Listen anlegen
	ereignisse: list[Ereignis] = []
	installiert: list[Installation] = []
	verbraucht: list[Verbrauch] = []

	# Ereignisse laden
	joined = path.joinpath("ereignisse.csv")

	if joined.is_file():
		for _, row in loader.read_csv(joined).iterrows():
			anfang = row["Datum von"]
			ende = row["Datum bis"]
			art = EreignisArt(row["Art"])
			intensitaet = row["Intensität"]

			ereignisse.append(Ereignis(anfang, ende, art, intensitaet))

	# Installiert laden
	joined = path.joinpath("installiert.csv")

	if joined.is_file():
		for _, row in loader.read_csv(joined).iterrows():
			datum = row["Datum"]
			art = ErzeugerArt(row["Art"])
			wert = row["Wert"]

			installiert.append(Installation(datum, art, wert))

	# Installiert laden
	joined = path.joinpath("verbraucht.csv")

	if joined.is_file():
		for _, row in loader.read_csv(joined).iterrows():
			datum = row["Datum"]
			art = VerbraucherArt(row["Art"])
			wert = row["Wert"]

			verbraucht.append(Verbrauch(datum, art, wert))

	# Listen zurückgeben
	return ereignisse, installiert, verbraucht


# Lädt alle verfügbaren Ausbaupfade
def load_all() -> dict[str, Ausbau]:
	ausbaupfade: dict[str, Ausbau] = {}

	# Alle Unterverzeichnisse einzeln laden
	for path in config.AUSBAU_DIR.iterdir():
		if path.is_dir():
			ausbaupfade[path.name] = load(path)

	# Ausbaupfade zurückgeben
	return ausbaupfade
