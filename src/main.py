import operator

import erzeuger
import smard


def main() -> None:
	wochen = smard.Smard.wochen(erzeuger.ErzeugerArt.Photovoltaik)
	werte = smard.Smard.werte(erzeuger.ErzeugerArt.Photovoltaik, wochen[-1])

	zeit, wert = max(werte.items(), key=operator.itemgetter(1))
	print("Maximaler PV-Wert diese Woche:", zeit, "-", wert)
