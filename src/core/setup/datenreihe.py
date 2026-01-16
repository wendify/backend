from typing import Self

from pandas import DataFrame, Series


# Abstraktion über SMARD-DataFrames
class Datenreihe[T]:
	def __init__(self, art: T, df: DataFrame) -> None:
		self.art = art
		self.df = df

	# Spalte der Anfangsdaten
	@property
	def anfang(self) -> Series:
		return self.df["Datum von"]

	# Spalte der Enddaten
	@property
	def ende(self) -> Series:
		return self.df["Datum bis"]

	# Spalte der tatsächlichen Werte
	@property
	def werte(self) -> Series:
		return self.df[self.art]

	# Kopiert diese Datenreihe zur Modifizierung
	def copy(self) -> Self:
		return type(self)(self.art, self.df.copy())
