import pandas as pd

from core.erzeuger import ErzeugerArt
from datetime import datetime


class Datenreihe:
    def __init__(self, art: ErzeugerArt, df):
        self.art = art
        self.df = df

    def get_value_by_datetime(self, timestamp: datetime):
        ts = pd.Timestamp(timestamp)
        result = self.df.loc[self.df["Datum von"] == ts]
        if result.empty:
            raise KeyError(f"Kein Eintrag für {ts}")
        return result.squeeze()
