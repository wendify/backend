import os
import config
from core.erzeugerArt import ErzeugerArt
from core.data import csv_handler
import pandas as pd


def load_csv():
	# TODO: Refactoring später
	installiert_path = config.FILE_STORAGE_PATH + "/installiert.csv"
	realisiert_path = config.FILE_STORAGE_PATH + "/realisiert.csv"
	# pickle_path = config.FILE_STORAGE_PATH + "/erzeuger_cleaned.pkl"

	# Wenn Pickle existiert → direkt laden
	# if os.path.exists(pickle_path):
	#     df_pv = pd.read_pickle(pickle_path)
	#     print("Pickle geladen.")
	#     print(df_pv.info())
	#     return df_pv

	# Falls Pickle nicht existiert → CSV laden
	if not csv_handler.check_csv_file_available(installiert_path):
		installiert_ids = [art.value.installiert for art in ErzeugerArt]
		csv_handler.download(installiert_path, config.SMARD_DOWNLOAD_URL, installiert_ids)

	if not csv_handler.check_csv_file_available(realisiert_path):
		realisiert_ids = [art.value.realisiert for art in ErzeugerArt]
		csv_handler.download(realisiert_path, config.SMARD_DOWNLOAD_URL, realisiert_ids)

	# Parsen und bereinigen
	installiert = csv_handler.clean_column_names(csv_handler.parse(installiert_path))
	realisiert = csv_handler.clean_column_names(csv_handler.parse(realisiert_path))

	# Spalten extrahieren
	# df_pv = df_cleaned[['datum_von', 'datum_bis', 'photovoltaik_mwh']].copy()

	# Als Pickle speichern
	# df_pv.to_pickle(pickle_path)
	# print("Pickle neu erstellt.")
	# print(df_pv.info())
	return installiert, realisiert
