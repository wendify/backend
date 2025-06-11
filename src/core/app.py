import datetime
import logging

from core.prognose.ausbaupfad import Ausbaupfad
from core.prognose.datenpunkt import Datenpunkt
from core.types import ErzeugerArt
from core.setup.smard import Smard


class App:
    def __init__(self) -> None:
        self.smard: Smard = Smard()
        logging.info("Setup durchgeführt")

    def run(self) -> None:
        logging.info("Prognose wird gestartet...")

        datum = datetime.datetime(2020, 1, 2, 12, 30)
        erzeuger = self.smard.get_erzeuger(ErzeugerArt.Photovoltaik)

        datenpunkte: list[Datenpunkt] = [Datenpunkt(erzeuger.art, datetime.datetime(2028, 1, 1), 300)]
        ausbaupfad = Ausbaupfad(datenpunkte, smard=self.smard)
        print(ausbaupfad.datenpunkte)

        # print("\nInstallierter Wert:")
        # print(erzeuger.installiert.get_row(datum))
        #
        # print("\nRealisierter Wert:")
        # print(erzeuger.realisiert.get_row(datum))
        #
        # print("\nNormierter Wert:")
        # print(erzeuger.normiert.get_row(datum))

    # Plot erstellen, falls matplotlib installiert ist
    # try:
    # 	from matplotlib import pyplot
    # except ModuleNotFoundError:
    # 	return
    #
    # daten = erzeuger.realisiert
    # daten.df = daten.df[daten.anfang.dt.date == datum.date()]
    #
    # pyplot.figure(figsize=(10, 5))
    # pyplot.plot(daten.anfang, daten.werte, marker=".")
    #
    # pyplot.title("Erzeugung über die Zeit")
    # pyplot.xlabel("Zeit")
    # pyplot.ylabel(f"{erzeuger.art} Erzeugung (MW)")
    #
    # pyplot.grid(True)
    # pyplot.show()
