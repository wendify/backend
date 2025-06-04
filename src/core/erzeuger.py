from core.erzeugerArt import ErzeugerArt
from core.datenreihe import Datenreihe


class Erzeuger:
    def __init__(self, art: ErzeugerArt):
        self.art = art
        self.verbrauch_installiert: Datenreihe = None
