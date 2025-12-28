from dataclasses import dataclass
from datetime import datetime

from core.setup.erzeuger import ErzeugerArt
from core.setup.verbraucher import VerbraucherArt


@dataclass
class ErzeugerDatenpunkt:
	art: ErzeugerArt
	datetime: datetime
	installiert: float


@dataclass
class VerbraucherDatenpunkt:
	art: VerbraucherArt
	datetime: datetime
	verbraucht: float
