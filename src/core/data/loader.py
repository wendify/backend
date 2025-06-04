import os
import config
from core.erzeugerArt import ErzeugerArt
from core.data import csv_handler
import pandas as pd

def load_csv():
    # TODO: Refactoring später
    csv_path = config.FILE_STORAGE_PATH + "/erzeuger.csv"
    # pickle_path = config.FILE_STORAGE_PATH + "/erzeuger_cleaned.pkl"

    # Wenn Pickle existiert → direkt laden
    # if os.path.exists(pickle_path):
    #     df_pv = pd.read_pickle(pickle_path)
    #     print("Pickle geladen.")
    #     print(df_pv.info())
    #     return df_pv

    # Falls Pickle nicht existiert → CSV laden
    if not csv_handler.check_csv_file_available(csv_path):
        csv_handler.download(csv_path, config.SMARD_DOWNLOAD_URL, list(ErzeugerArt))

    # Parsen und bereinigen
    df = csv_handler.parse(csv_path)
    df_cleaned = csv_handler.clean_column_names(df)

    # Spalten extrahieren
    # df_pv = df_cleaned[['datum_von', 'datum_bis', 'photovoltaik_mwh']].copy()

    # Als Pickle speichern
    # df_pv.to_pickle(pickle_path)
    # print("Pickle neu erstellt.")
    # print(df_pv.info())
    return df_cleaned
