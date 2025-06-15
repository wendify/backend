import fastapi
import pandas

from core.api.models import DatenpunktModel, ErzeugerModel
from core.erzeuger import ErzeugerArt
from core.setup.smard import Smard


def datenpunkte(df: pandas.DataFrame) -> list[DatenpunktModel]:
	models = []

	for _, row in df.iterrows():
		anfang, ende, wert = row
		models.append(DatenpunktModel(anfang=anfang, ende=ende, wert=wert))

	return models


def setup(app: fastapi.FastAPI, smard: Smard) -> None:
	@app.get("/erzeuger")
	def _() -> list[ErzeugerModel]:
		models = []

		for erzeuger in smard.erzeuger:
			art = erzeuger.art.name
			name = erzeuger.art.value

			models.append(ErzeugerModel(art=art, name=name))

		return models

	@app.get("/erzeuger/{art}/installiert")
	def _(art: str) -> list[DatenpunktModel]:
		try:
			erzeuger = smard.get_erzeuger(ErzeugerArt[art])
		except KeyError:
			raise fastapi.HTTPException(404, "Erzeuger existiert nicht")

		return datenpunkte(erzeuger.installiert.df)

	@app.get("/erzeuger/{art}/normiert")
	def _(art: str) -> list[DatenpunktModel]:
		try:
			erzeuger = smard.get_erzeuger(ErzeugerArt[art])
		except KeyError:
			raise fastapi.HTTPException(404, "Erzeuger existiert nicht")

		return datenpunkte(erzeuger.normiert.df)

	@app.get("/erzeuger/{art}/realisiert")
	def _(art: str) -> list[DatenpunktModel]:
		try:
			erzeuger = smard.get_erzeuger(ErzeugerArt[art])
		except KeyError:
			raise fastapi.HTTPException(404, "Erzeuger existiert nicht")

		return datenpunkte(erzeuger.realisiert.df)
