from pandas import DataFrame

from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt


# Berechnet CO2-Emissionen für jeden Erzeuger basierend auf der realisierten Erzeugung
def calculate_emissions(
	realisiert: dict[ErzeugerArt, Datenreihe[ErzeugerArt]],
) -> DataFrame:
	# Wenn keine Daten vorhanden sind, leeres DataFrame zurückgeben
	if not realisiert:
		return DataFrame()

	# Zeitindex aus der ersten Datenreihe erzeugen
	anfang = next(iter(realisiert.values())).anfang

	# Zeitschritt zwischen Werten berechnen, 15 Minuten als Standard
	if len(anfang) >= 2:
		step = (anfang.iloc[1] - anfang.iloc[0]).total_seconds() / 3600
	else:
		step = 0.25

	# Ergebnis-DataFrame erzeugen
	result = DataFrame({"Datum von": anfang}).set_index("Datum von")

	# Emissionen für jeden Erzeuger berechnen und hinzufügen
	for art, reihe in realisiert.items():
		result[art] = reihe.werte.to_numpy() * art.emissionen * step

	# Endresultat zurückgeben
	return result
