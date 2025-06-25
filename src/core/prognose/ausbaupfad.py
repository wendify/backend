import logging
from collections import defaultdict
from datetime import datetime

import pandas as pd

from core.prognose.datenpunkt import Datenpunkt
from core.setup.smard import Smard
from core.types import ErzeugerArt
from core.datenreihe import Datenreihe


def validate_datenpunkte(datenpunkte: list[Datenpunkt]) -> bool:
    if not isinstance(datenpunkte, list):
        raise ValueError("Datenpunkte ist keine Liste")

    if not all(isinstance(dp, Datenpunkt) for dp in datenpunkte):
        raise ValueError("Mindestens ein Eintrag ist kein Datenpunkt")

    return True


def ergaenze_erzeuger_datenpunkte(datenpunkte: list[Datenpunkt], smard: Smard) -> list[Datenpunkt]:
    vorhandene_arten = {dp.art for dp in datenpunkte}
    erwartete_arten = set(ErzeugerArt)
    fehlende = erwartete_arten - vorhandene_arten

    # max jahr finden in vorhandene Daten
    max_datetime: datetime = datetime.min

    # finde max wert
    for punkt in datenpunkte:
        if punkt.datetime > max_datetime:
            max_datetime = punkt.datetime

    if fehlende:
        if smard is None:
            raise ValueError(
                f"Fehlende ErzeugerArten: {fehlende} – kein smard übergeben")

        for art in fehlende:
            erzeuger = smard.get_erzeuger(art)
            # 1. Letzter Timestamp im Index
            letzter_zeitpunkt = erzeuger.installiert.df.index[-1]
            letzte_reihe = erzeuger.installiert.df.loc[letzter_zeitpunkt]
            letzter_installierter_wert = letzte_reihe[erzeuger.art]
            neuer_dp = Datenpunkt(art, datetime=max_datetime,
                                  installiert=float(letzter_installierter_wert))
            datenpunkte.append(neuer_dp)

    return datenpunkte


def create_prognose_datenreihen(datenpunkte: list[Datenpunkt], smard:Smard) -> list[Datenreihe]:
    # Gruppiere Datenpunkte nach ErzeugerArt
    gruppiert: dict[ErzeugerArt, list[Datenpunkt]] = defaultdict(list)
    for dp in datenpunkte:
        gruppiert[dp.art].append(dp)

    erzeuger_datenreihen: list[Datenreihe] = []

    for art, dps in gruppiert.items():
        # Sortiere die Datenpunkte chronologisch
        dps.sort(key=lambda dp: dp.datetime)

        daten = []
        for i in range(len(dps)):
            start = dps[i].datetime
            end = dps[i + 1].datetime if i + 1 < len(dps) else start  # oder ein sinnvolles Enddatum setzen
            daten.append({
                "Datum von": start,
                "Datum bis": end,
                art: dps[i].installiert
            })

        df = pd.DataFrame(daten)
        erzeuger_datenreihen.append(Datenreihe(art, df))

    return erzeuger_datenreihen


class Ausbaupfad:
    def __init__(self, datenpunkte: list[Datenpunkt], smard: Smard | None = None):
        if not validate_datenpunkte(datenpunkte):
            logging.error("Validierung fehlgeschlagen!")
            raise ValueError("Validierung fehlgeschlagen!")

        # Ergänze Datenpunkte für fehlende ErzeugerArten (anhand aller Erzeuger aus Smard)
        datenpunkte = ergaenze_erzeuger_datenpunkte(datenpunkte, smard)
        self.datenpunkte = datenpunkte

        self.prognose_datenreihen: list[Datenreihe] = create_prognose_datenreihen(self.datenpunkte, smard)
        # Interpolation der Datenpunkte
        # self.interpolate_datenpunkte()

    def interpolate_datenpunkte(self) -> None:
        """Interpoliert die Datenpunkte für eine glattere Kurve."""
        for art in ErzeugerArt:
            datenreihe = self.get_erzeuger(art)
            if not datenreihe:
                continue

            # Interpolation durchführen
            interpolierte_werte = self.interpolate(datenreihe)
            self.datenreihen_interpoliert.append(interpolierte_werte)

    def get_erzeuger(self, art: ErzeugerArt) -> Datenreihe:
        """Gibt alle Datenpunkte für einen bestimmten Erzeuger zurück."""
        return [dp for dp in self.datenpunkte if dp.art == art]
