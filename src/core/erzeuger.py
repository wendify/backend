from dataclasses import dataclass
import pandas as pd
from core.erzeugerArt import ErzeugerArt
from core.datenreihe import Datenreihe

@dataclass
class Erzeuger:
    art: ErzeugerArt
    verbrauch_realisiert: Datenreihe
    verbrauch_installiert: Datenreihe
    e_norm: Datenreihe

    def __post_init__(self):
        spalte = self.art.value  # z. B. 'Photovoltaik'

        # Sortieren
        df_real = self.verbrauch_realisiert.df.sort_values('Datum von').copy()
        df_inst = self.verbrauch_installiert.df.sort_values('Datum von').copy()

        # Merge: installierten Wert je Jahr zuordnen (backward match)
        df_merged = pd.merge_asof(
            df_real.assign(Zeit=df_real['Datum von']),
            df_inst[['Datum von', spalte]].rename(columns={'Datum von': 'Zeit', spalte: f'{spalte}_jahr'}),
            on='Zeit',
            direction='backward'
        )

        # Normieren
        df_merged[spalte] = df_merged[spalte] / df_merged[f'{spalte}_jahr']

        # End-DataFrame
        df_final = df_merged[['Datum von', 'Datum bis', spalte]].copy()
        self.e_norm = Datenreihe(self.art, df_final)
