import sys

import pandas


def parse(path: str) -> pandas.DataFrame:
	try:
		frame = pandas.read_csv(path, decimal=",", na_values=["-"], sep=";", thousands=".")
	except FileNotFoundError:
		sys.exit("Fehler: CSV-Datei noch nicht heruntergeladen")

	for column in frame.columns:
		if column.startswith("Datum"):
			frame[column] = pandas.to_datetime(frame[column], dayfirst=True)

	return frame


def main() -> None:
	path = "erzeuger.csv"
	frame = parse(path)

	print(frame.dtypes)
