from datetime import datetime

from fastapi import FastAPI, HTTPException
from pandas import DataFrame

from core.api.models import Ausbaupfad, Erzeugnis
from core.erzeuger import ErzeugerArt
from core.prognose import ausbaupfad, datenpunkt
from core.setup.smard import Smard


def erzeugnisse(
	df: DataFrame, a: datetime | None = None, e: datetime | None = None
) -> list[Erzeugnis]:
	models = []

	if a is not None:
		df = df[a <= df["Datum von"]]

	if e is not None:
		df = df[e >= df["Datum von"]]

	for _, row in df.iterrows():
		anfang, ende, wert = row
		models.append(Erzeugnis(anfang=anfang, ende=ende, wert=wert))

	return models


def setup(app: FastAPI, smard: Smard) -> None:
	@app.get("/erzeuger")
	def _() -> list[ErzeugerArt]:
		return [erzeuger.art for erzeuger in smard.erzeuger]

	@app.get("/erzeuger/{art}/installiert")
	def _(
		art: ErzeugerArt, anfang: datetime | None = None, ende: datetime | None = None
	) -> list[Erzeugnis]:
		try:
			erzeuger = smard.get_erzeuger(art)
		except KeyError:
			raise HTTPException(404, "Erzeuger existiert nicht")

		return erzeugnisse(erzeuger.installiert.df, anfang, ende)

	@app.get("/erzeuger/{art}/normiert")
	def _(
		art: ErzeugerArt, anfang: datetime | None = None, ende: datetime | None = None
	) -> list[Erzeugnis]:
		try:
			erzeuger = smard.get_erzeuger(art)
		except KeyError:
			raise HTTPException(404, "Erzeuger existiert nicht")

		return erzeugnisse(erzeuger.normiert.df, anfang, ende)

	@app.get("/erzeuger/{art}/realisiert")
	def _(
		art: ErzeugerArt, anfang: datetime | None = None, ende: datetime | None = None
	) -> list[Erzeugnis]:
		try:
			erzeuger = smard.get_erzeuger(art)
		except KeyError:
			raise HTTPException(404, "Erzeuger existiert nicht")

		return erzeugnisse(erzeuger.realisiert.df, anfang, ende)

	@app.post("/ausbaupfade")
	def _(
		pfad: Ausbaupfad, anfang: datetime | None = None, ende: datetime | None = None
	) -> dict[ErzeugerArt, list[Erzeugnis]]:
		datenpunkte = []

		for dp in pfad.datenpunkte:
			datenpunkte.append(
				datenpunkt.ErzeugerDatenpunkt(
					art=dp.erzeuger, datetime=dp.zeitpunkt, installiert=dp.wert
				)
			)

		konstruiert = ausbaupfad.Ausbaupfad(datenpunkte, smard=smard)

		d = {}
		for dr in konstruiert.prognose_datenreihen:
			d[dr.art] = erzeugnisse(dr.df, anfang, ende)
		return d
