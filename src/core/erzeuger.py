from core.datenreihe import Datenreihe
from core.types import ErzeugerArt


class Erzeuger:
	def __init__(
		self,
		art: ErzeugerArt,
		installiert: Datenreihe[ErzeugerArt],
		realisiert: Datenreihe[ErzeugerArt],
		regulation: float,
	) -> None:
		self.art = art
		self.installiert = installiert
		self.realisiert = realisiert
		self.regulation = regulation

		normiert = realisiert.df.copy()
		normiert[self.art] /= installiert.df[self.art]
		normiert = normiert.fillna(0)

		self.normiert: Datenreihe = Datenreihe(art, normiert)
