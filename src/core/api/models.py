import datetime

import pydantic


class DatenpunktModel(pydantic.BaseModel):
	anfang: datetime.datetime
	ende: datetime.datetime
	wert: float


class ErzeugerModel(pydantic.BaseModel):
	art: str
	name: str
