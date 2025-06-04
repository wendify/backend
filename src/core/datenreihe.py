from core.erzeuger import ErzeugerArt


class Datenreihe:
    def __init__(self, art: ErzeugerArt, df):
        self.art = art
        self.df = df
