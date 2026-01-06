import logging
from pathlib import Path

import config
from core.data import loader
from core.prognose.ausbaupfad import Ausbaupfad
from core.prognose.types import Ereignis, Installation, Verbrauch
from core.setup.erzeuger import ErzeugerArt
from core.setup.verbraucher import VerbraucherArt
from core.simulation.event import EreignisArt


# Lädt einen einzelnen Ausbaupfad
def load(path: Path) -> Ausbaupfad:
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

	# Verbraucht laden
	joined = path.joinpath("verbraucht.csv")

	if joined.is_file():
		for _, row in loader.read_csv(joined).iterrows():
			datum = row["Datum"]
			art = VerbraucherArt(row["Art"])
			wert = row["Wert"]

			verbraucht.append(Verbrauch(datum, art, wert))

	# Ausbaupfad erstellen und zurückgeben
	return Ausbaupfad(path.name, ereignisse, installiert, verbraucht)


# Lädt alle verfügbaren Ausbaupfade
def load_all() -> list[Ausbaupfad]:
	ausbaupfade: list[Ausbaupfad] = []

	# Alle Unterverzeichnisse einzeln laden
	for path in config.AUSBAU_DIR.iterdir():
		if path.is_dir():
			ausbaupfade.append(load(path))

	# Ausbaupfade zurückgeben
	return ausbaupfade
