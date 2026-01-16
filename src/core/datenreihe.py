import logging
from datetime import datetime

from pandas import DataFrame, Series


class Datenreihe[T]:
	def __init__(self, art: T, df: DataFrame) -> None:
		self.art = art
		self.df = df

	@property
	def anfang(self) -> Series:
		return self.df["Datum von"]

	@property
	def ende(self) -> Series:
		return self.df["Datum bis"]

	@property
	def werte(self) -> Series:
		return self.df[self.art]

	def get_row(self, timestamp: datetime) -> Series:
		result = self.df[(self.anfang <= timestamp) & (self.ende > timestamp)]

		if result.empty:
			logging.error(f"Kein Eintrag für {self.art}: {timestamp}")
			raise KeyError(timestamp)

		return result.iloc[0]
