import enum

from core.datenreihe import Datenreihe


class ErzeugerArt(enum.StrEnum):
	Biomasse = "Biomasse"
	Braunkohle = "Braunkohle"
	Erdgas = "Erdgas"
	Kernenergie = "Kernenergie"
	Photovoltaik = "Photovoltaik"
	Pumpspeicher = "Pumpspeicher"
	SonstigeErneuerbare = "Sonstige Erneuerbare"
	SonstigeKonventionelle = "Sonstige Konventionelle"
	Steinkohle = "Steinkohle"
	Wasserkraft = "Wasserkraft"
	WindOffshore = "Wind Offshore"
	WindOnshore = "Wind Onshore"


class Erzeuger:
	def __init__(self, art: ErzeugerArt, installiert: Datenreihe, realisiert: Datenreihe) -> None:
		self.art = art
		self.installiert = installiert
		self.realisiert = realisiert

		normiert = realisiert.df.copy()
		normiert[self.art] /= installiert.df[self.art]

		self.normiert = Datenreihe(art, normiert)
