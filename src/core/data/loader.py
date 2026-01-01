import logging
import sys
from pathlib import Path

import pandas
from pandas import DataFrame

import config
from core.data import handler


# Lädt alle nötigen CSV-Dateien für SMARD
def load_csv() -> tuple[DataFrame, DataFrame, DataFrame]:
	if not config.INSTALLIERT_FILE.exists():
		ids = [id + 3_000_000 for id in config.INSTALLIERT_IDS]
		handler.download(ids, config.INSTALLIERT_FILE)

	if not config.REALISIERT_FILE.exists():
		ids = [id + 1_000_000 for id in config.REALISIERT_IDS]
		handler.download(ids, config.REALISIERT_FILE)

	if not config.VERBRAUCHT_FILE.exists():
		ids = [id + 5_000_000 for id in config.VERBRAUCHT_IDS]
		handler.download(ids, config.VERBRAUCHT_FILE)

	installiert = read_csv(config.INSTALLIERT_FILE)
	realisiert = read_csv(config.REALISIERT_FILE)
	verbraucht = read_csv(config.VERBRAUCHT_FILE)

	return installiert, realisiert, verbraucht


# Lädt eine einzelne CSV-Datei, auch wiederverwendbar für Ausbaupfade
def read_csv(path: Path) -> DataFrame:
	logging.debug(f"CSV-Datei wird gelesen: {path}")

	try:
		df = pandas.read_csv(path, decimal=",", na_values=["-"], sep=";", thousands=".").fillna(0)
	except FileNotFoundError:
		logging.error(f"CSV-Datei nicht gefunden: {path}")
		sys.exit()

	# Zusätze wie [MW] oder [MWh] aus Spaltennamen streichen
	df.columns = [column.split("[")[0].strip() for column in df.columns]

	# Datumsspalten in Datumsobjekte parsen
	for column in df.columns:
		if column.startswith("Datum"):
			df[column] = pandas.to_datetime(df[column], dayfirst=True)

	return df
