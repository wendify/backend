import datetime
import logging
import typing

import pandas

from core.types import ErzeugerArt


class Datenreihe:
	def __init__(self, art: ErzeugerArt, df: pandas.DataFrame) -> None:
		self.art: ErzeugerArt = art
		self.df = df

	@property
	def anfang(self) -> pandas.Series:
		return self.df["Datum von"]

	@property
	def ende(self) -> pandas.Series:
		return self.df["Datum bis"]

	@property
	def werte(self) -> pandas.Series:
		return self.df[self.art]

	def get_row(self, timestamp: datetime.datetime) -> pandas.Series:
		result = self.df[(self.anfang <= timestamp) & (self.ende > timestamp)]

		if result.empty:
			logging.error(f"Kein Eintrag für {self.art}: {timestamp}")
			raise KeyError

		return result.iloc[0]
