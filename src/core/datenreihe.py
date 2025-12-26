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
