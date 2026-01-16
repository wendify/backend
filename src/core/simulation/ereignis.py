from dataclasses import dataclass
from enum import StrEnum


# Die Gewichtung eines Ereignisses oder Erzeugers
@dataclass
class Gewichtung:
	regen: float
	sonne: float
	temperatur: float
	wind: float


# Die Art eines Ereignisses
class EreignisArt(StrEnum):
	Duerre = "Dürre"
	Sturm = "Sturm"

	# Die Gewichtung dieser EreignisArt, von -1 (sehr negativ) bis 1 (sehr positiv)
	@property
	def gewichtung(self) -> Gewichtung:
		match self:
			case EreignisArt.Duerre:
				return Gewichtung(-0.8, 1.0, 1.0, -0.8)
			case EreignisArt.Sturm:
				return Gewichtung(0.6, -1.0, -0.8, 1.0)
