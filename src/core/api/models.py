import datetime
import enum

import pydantic


class Datenpunkt(pydantic.BaseModel):
	art: str
	wert: float
	zeitpunkt: datetime.datetime


# Die Art eines Wetterereignisses
class EreignisArt(enum.Enum):
	Duerre = enum.auto()
	Regen = enum.auto()
	Schneefall = enum.auto()
	Sturm = enum.auto()


# Ein Wetterereignis eines Ausbaupfades
class Ereignis(pydantic.BaseModel):
	art: EreignisArt
	ende: datetime.datetime
	start: datetime.datetime
	wert: int = pydantic.Field(ge=0, le=5)


class Datenpunkt(pydantic.BaseModel):
	anfang: datetime.datetime
	ende: datetime.datetime
	wert: float


class Erzeuger(pydantic.BaseModel):
	art: str
	name: str
