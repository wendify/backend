import datetime
import typing

import requests

import erzeuger


class Antwort(typing.TypedDict):
	series: list[tuple[int, float | None]]
	timestamps: list[int]


class Link:
	ROOT = "https://www.smard.de/app/chart_data"

	@classmethod
	def werte(cls, art: erzeuger.ErzeugerArt, woche: datetime.datetime) -> str:
		return f"{cls.ROOT}/{art}/DE/{art}_DE_quarterhour_{int(woche.timestamp() * 1000)}.json"

	@classmethod
	def wochen(cls, art: erzeuger.ErzeugerArt) -> str:
		return f"{cls.ROOT}/{art}/DE/index_quarterhour.json"


class Smard:
	@staticmethod
	def timestamp(zeit: int) -> datetime.datetime:
		return datetime.datetime.fromtimestamp(zeit / 1000)

	@classmethod
	def werte(cls, art: erzeuger.ErzeugerArt, woche: datetime.datetime) -> dict[datetime.datetime, float]:
		antwort: Antwort = requests.get(Link.werte(art, woche)).json()
		return {cls.timestamp(zeit): wert for zeit, wert in antwort["series"] if wert is not None}

	@classmethod
	def wochen(cls, art: erzeuger.ErzeugerArt) -> list[datetime.datetime]:
		antwort: Antwort = requests.get(Link.wochen(art)).json()
		return [cls.timestamp(zeit) for zeit in antwort["timestamps"]]
