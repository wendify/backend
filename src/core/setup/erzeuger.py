from enum import StrEnum

from pandas import DataFrame

from core.setup.datenreihe import Datenreihe
from core.simulation.event import Gewichtung


# Die möglichen Arten eines Erzeugers
class ErzeugerArt(StrEnum):
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

	# Emissionen dieser ErzeugerArt in Tonnen pro MWh
	@property
	def emissionen(self) -> float:
		match self:
			case ErzeugerArt.Braunkohle:
				return 1.1
			case ErzeugerArt.Erdgas:
				return 0.4
			case ErzeugerArt.Kernenergie:
				return 0.01
			case ErzeugerArt.SonstigeKonventionelle:
				return 0.5
			case ErzeugerArt.Steinkohle:
				return 0.85
			case _:
				return 0.0

	# Die Gewichtung dieser ErzeugerArt, von 0 (keine Abhängigkeit) bis 1 (volle Abhängigkeit)
	@property
	def gewichtung(self) -> Gewichtung:
		match self:
			case ErzeugerArt.Biomasse:
				return Gewichtung(0.6, 0.5, 0.4, 0.1)
			case ErzeugerArt.Braunkohle:
				return Gewichtung(0.1, 0.0, 0.1, 0.0)
			case ErzeugerArt.Erdgas:
				return Gewichtung(0.1, 0.0, 0.1, 0.0)
			case ErzeugerArt.Kernenergie:
				return Gewichtung(0.2, 0.0, 0.2, 0.0)
			case ErzeugerArt.Photovoltaik:
				return Gewichtung(0.0, 1.0, 0.6, 0.0)
			case ErzeugerArt.Pumpspeicher:
				return Gewichtung(0.5, 0.0, 0.2, 0.0)
			case ErzeugerArt.SonstigeErneuerbare:
				return Gewichtung(0.3, 0.4, 0.3, 0.3)
			case ErzeugerArt.SonstigeKonventionelle:
				return Gewichtung(0.1, 0.0, 0.1, 0.0)
			case ErzeugerArt.Steinkohle:
				return Gewichtung(0.1, 0.0, 0.1, 0.0)
			case ErzeugerArt.Wasserkraft:
				return Gewichtung(0.8, 0.0, 0.3, 0.0)
			case ErzeugerArt.WindOffshore:
				return Gewichtung(0.0, 0.0, 0.0, 1.0)
			case ErzeugerArt.WindOnshore:
				return Gewichtung(0.0, 0.0, 0.0, 1.0)

	# Mögliche Regulierung dieser ErzeugerArt innerhalb eines Zeitschritts
	@property
	def regulierung(self) -> float:
		match self:
			case ErzeugerArt.Biomasse:
				return 0.4
			case ErzeugerArt.Braunkohle:
				return 0.02
			case ErzeugerArt.Erdgas:
				return 1.0
			case ErzeugerArt.Kernenergie:
				return 0.02
			case ErzeugerArt.Pumpspeicher:
				return 1.0
			case ErzeugerArt.SonstigeKonventionelle:
				return 0.2
			case ErzeugerArt.Steinkohle:
				return 0.05
			case _:
				return 0.0


# Repräsentiert einen speziellen Erzeuger
class Erzeuger:
	def __init__(self, art: ErzeugerArt, installiert: DataFrame, realisiert: DataFrame) -> None:
		normiert = realisiert.copy()
		normiert[art] /= installiert[art]
		normiert = normiert.fillna(0)

		self.art = art
		self.installiert = Datenreihe(art, installiert)
		self.normiert = Datenreihe(art, normiert)
		self.realisiert = Datenreihe(art, realisiert)
