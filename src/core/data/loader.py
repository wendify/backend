import logging
import pathlib
import sys

import pandas

import config
from core.data import handler


def load_csv() -> tuple[pandas.DataFrame, pandas.DataFrame]:
	if not config.INSTALLIERT_FILE.exists():
		ids = [id + 3_000_000 for id in config.INSTALLIERT_IDS]
		handler.download(config.INSTALLIERT_FILE, config.SMARD_URL, ids)

	if not config.REALISIERT_FILE.exists():
		ids = [id + 1_000_000 for id in config.REALISIERT_IDS]
		handler.download(config.REALISIERT_FILE, config.SMARD_URL, ids)

	installiert = read_csv(config.INSTALLIERT_FILE)
	realisiert = read_csv(config.REALISIERT_FILE)

	rename_columns(installiert)
	rename_columns(realisiert)

	return installiert, realisiert


def read_csv(path: pathlib.Path) -> pandas.DataFrame:
	try:
		df = pandas.read_csv(path, decimal=",", na_values=["-"], sep=";", thousands=".").fillna(0)
	except FileNotFoundError:
		logging.error(f"CSV-Datei nicht gefunden: {path}")
		sys.exit()

	for column in df.columns:
		if column.startswith("Datum"):
			df[column] = pandas.to_datetime(df[column], dayfirst=True)

	return df


def rename_columns(df: pandas.DataFrame) -> None:
	df.columns = [column.split(" [")[0] for column in df.columns]
