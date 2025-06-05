import config
from core.erzeugerArt import ErzeugerArt, _RohArten
from core.data import csv_handler
import pandas as pd


def load_csv():
	# pickle_path = config.FILE_STORAGE_PATH + "/erzeuger_cleaned.pkl"

	# Wenn Pickle existiert → direkt laden
	# if os.path.exists(pickle_path):
	#     df_pv = pd.read_pickle(pickle_path)
	#     print("Pickle geladen.")
	#     print(df_pv.info())
	#     return df_pv

	# Falls Pickle nicht existiert → CSV laden
	if not config.INSTALLIERT_FILE.exists():
		installiert_ids = [art.value.installiert for art in _RohArten]
		csv_handler.download(config.INSTALLIERT_FILE, config.SMARD_URL, installiert_ids)

	if not config.REALISIERT_FILE.exists():
		realisiert_ids = [art.value.realisiert for art in _RohArten]
		csv_handler.download(config.REALISIERT_FILE, config.SMARD_URL, realisiert_ids)

	# Parsen und bereinigen
	installiert = csv_handler.clean_column_names(csv_handler.parse(config.INSTALLIERT_FILE))
	realisiert = csv_handler.clean_column_names(csv_handler.parse(config.REALISIERT_FILE))

	# Spalten extrahieren
	# df_pv = df_cleaned[['datum_von', 'datum_bis', 'photovoltaik_mwh']].copy()

	# Als Pickle speichern
	# df_pv.to_pickle(pickle_path)
	# print("Pickle neu erstellt.")
	# print(df_pv.info())
	return installiert, realisiert
