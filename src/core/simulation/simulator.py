import dataclasses

from core.prognose.loader import Ereignis
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.simulation.event import Gewichtung


# Bestimmt den Impakt von Kombination aus Ereignis und Erzeuger
def calculate_impact(art: ErzeugerArt, ereignis: Ereignis) -> float:
	total = 0

	# Jede Gewichtung einzeln berechnen, immer jeweils im Bereich [-1, 1]
	for parameter in dataclasses.fields(Gewichtung):
		name = parameter.name
		total += getattr(art.gewichtung, name) * getattr(ereignis.art.gewichtung, name)

	# Auf Bereich [-1, 1] normieren
	total /= len(dataclasses.fields(Gewichtung))

	# Intensität anwenden
	total *= ereignis.intensitaet

	# Auf Bereich [0, 2] abbilden
	return total + 1


# Wendet Ereignisse auf Datenreihen an
def apply_events(datenreihen: list[Datenreihe[ErzeugerArt]], ereignisse: list[Ereignis]) -> None:
	# Auf jede Datenreihe jedes Ereignis anwenden
	for datenreihe in datenreihen:
		for ereignis in ereignisse:
			# Maske für Zeitbereich erstellen
			maske = (datenreihe.anfang >= ereignis.anfang) & (datenreihe.ende < ereignis.ende)

			# Impakt berechnen (konstant für Ereignis und Erzeuger)
			impact = calculate_impact(datenreihe.art, ereignis)

			# Vektorisiert multiplizieren
			datenreihe.df.loc[maske, datenreihe.art] *= impact
