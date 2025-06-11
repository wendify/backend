import logging
from datetime import datetime

from core.prognose.datenpunkt import Datenpunkt
from core.setup.smard import Smard
from core.types import ErzeugerArt


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
            raise ValueError(f"Fehlende ErzeugerArten: {fehlende} – kein smard übergeben")

        for art in fehlende:
            erzeuger = smard.get_erzeuger(art)
            # 1. Letzter Timestamp im Index
            letzter_zeitpunkt = erzeuger.installiert.df.index[-1]
            letzte_reihe = erzeuger.installiert.df.loc[letzter_zeitpunkt]
            letzter_installierter_wert = letzte_reihe[erzeuger.art]
            neuer_dp = Datenpunkt(art, datetime=max_datetime, installiert=float(letzter_installierter_wert))
            datenpunkte.append(neuer_dp)

    return datenpunkte


class Ausbaupfad:
    def __init__(self, datenpunkte: list[Datenpunkt], smard: Smard | None = None):
        if not validate_datenpunkte(datenpunkte):
            logging.error("Validierung fehlgeschlagen!")
            raise ValueError("Validierung fehlgeschlagen!")

        # Ergänze Datenpunkte für fehlende ErzeugerArten (anhand aller Erzeuger aus Smard)
        datenpunkte = ergaenze_erzeuger_datenpunkte(datenpunkte, smard)
        self.datenpunkte = datenpunkte
