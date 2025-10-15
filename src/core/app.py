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

        datum = datetime.datetime(2025, 1, 2, 12, 30)
        erzeuger = self.smard.get_erzeuger(ErzeugerArt.Braunkohle)
        erzeuger2 = self.smard.get_erzeuger(ErzeugerArt.Erdgas)

        datenpunkte: list[Datenpunkt] = [
            Datenpunkt(erzeuger.art, datetime.datetime(2026, 5, 1), 6000),
            Datenpunkt(erzeuger.art, datetime.datetime(2027, 11, 1), 12000),
        ]
        ausbaupfad = Ausbaupfad(datenpunkte, smard=self.smard)
        print(ausbaupfad.datenpunkte)
        prognose = ausbaupfad.get_prognose_datenreihe(ErzeugerArt.Photovoltaik)
        print("\nErste Prognose-Zeilen (Braunkohle):")
        print(prognose.df.head())

        # print("\nInstallierter Wert:")
        # print(erzeuger.installiert.get_row(datum))
        #
        # print("\nRealisierter Wert:")
        # print(erzeuger.realisiert.get_row(datum))
        #
        # print("\nNormierter Wert:")
        # print(erzeuger.normiert.get_row(datum))

        # Plot erstellen, falls matplotlib installiert ist
        try:
            from matplotlib import pyplot
        except ModuleNotFoundError:
            return

        # Komplette Prognose-Zeitreihe plotten (kein Datum-Filter)
        pyplot.figure(figsize=(12, 5))
        pyplot.plot(prognose.df["Datum von"], prognose.df[ErzeugerArt.Photovoltaik], linewidth=0.8)
        pyplot.title(f"Prognose {ErzeugerArt.Photovoltaik} – gesamte Zeitreihe")
        pyplot.xlabel("Zeit")
        pyplot.ylabel(f"{ErzeugerArt.Photovoltaik} Erzeugung (MW)")
        pyplot.grid(True)
        pyplot.tight_layout()
        pyplot.show()

        # Kurze Zusammenfassung zur Kontrolle
        print("\nPrognose-Form:", prognose.df.shape)
        print("Zeitraum:", prognose.df["Datum von"].iloc[0], "→", prognose.df["Datum bis"].iloc[-1])
