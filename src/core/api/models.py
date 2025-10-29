import datetime
import enum

import pydantic

from core.types import ErzeugerArt


# Ein Datenpunkt eines Erzeugers
class Erzeugnis(pydantic.BaseModel):
	anfang: datetime.datetime
	ende: datetime.datetime
	wert: float


# Ein Datenpunkt eines Ausbaupfades
class Datenpunkt(pydantic.BaseModel):
	erzeuger: ErzeugerArt
	wert: float
	zeitpunkt: datetime.datetime


# Die Art eines Wetterereignisses
class EreignisArt(enum.Enum):
	Duerre = "Dürre"
	Regen = "Regen"
	Schneefall = "Schneefall"
	Sturm = "Sturm"


# Ein Wetterereignis eines Ausbaupfades
class Ereignis(pydantic.BaseModel):
	art: EreignisArt
	ende: datetime.datetime
	intensitaet: int
	start: datetime.datetime


# Ein Ausbaupfad eines Benutzers
class Ausbaupfad(pydantic.BaseModel):
	datenpunkte: list[Datenpunkt]
	ereignisse: list[Ereignis]
