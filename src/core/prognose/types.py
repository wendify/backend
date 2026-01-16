from dataclasses import dataclass
from datetime import datetime

from core.setup.erzeuger import ErzeugerArt
from core.setup.verbraucher import VerbraucherArt
from core.simulation.ereignis import EreignisArt


# Eine Zeile von Ausbaupfad-Ereignissen
@dataclass
class Ereignis:
	anfang: datetime
	ende: datetime
	art: EreignisArt
	intensitaet: float


# Eine Zeile von Ausbaupfad-Installationen
@dataclass
class Installation:
	datum: datetime
	art: ErzeugerArt
	wert: float


# Eine Zeile von Ausbaupfad-Verbräuchen
@dataclass
class Verbrauch:
	datum: datetime
	art: VerbraucherArt
	wert: float
