from enum import StrEnum

from pandas import DataFrame

from core.setup.datenreihe import Datenreihe


# Die möglichen Arten eines Verbrauchers
class VerbraucherArt(StrEnum):
	Netzlast = "Netzlast"
	NetzlastInklPumpspeicher = "Netzlast inkl. Pumpspeicher"
	Pumpspeicher = "Pumpspeicher"
	Residuallast = "Residuallast"


# Repräsentiert einen speziellen Verbraucher
class Verbraucher:
	def __init__(self, art: VerbraucherArt, verbraucht: DataFrame) -> None:
		self.art = art
		self.verbraucht = Datenreihe(art, verbraucht)
