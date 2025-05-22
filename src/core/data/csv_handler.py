import datetime
import sys
import typing
import requests
import pandas
import logging

from core import erzeuger
from core.logger import logger


class Form(typing.TypedDict):
    format: str
    language: str
    moduleIds: list[int]
    region: str
    timestamp_from: int
    timestamp_to: int


class Request(typing.TypedDict):
    request_form: list[Form]


def download(path: str, url: str) -> None:
    form: Form = {
        "format": "CSV",
        "language": "de",
        "moduleIds": list(erzeuger.ErzeugerArt),
        "region": "DE",
        "timestamp_from": int(datetime.datetime(2024, 1, 1).timestamp()) * 1000,
        "timestamp_to": int(datetime.datetime(2025, 1, 1).timestamp()) * 1000,
    }

    request: Request = {
        "request_form": [form],
    }

    with requests.post(url, json=request) as response:
        if not response.ok:
            logger.error(response.text)
            sys.exit()

        with open(path, "bw") as file:
            file.write(response.content)


def parse(path: str) -> pandas.DataFrame:
    try:
        frame = pandas.read_csv(path, decimal=",", na_values=["-"], sep=";", thousands=".")
    except FileNotFoundError:
        logger.error("File not found.")
        sys.exit()

    for column in frame.columns:
        if column.startswith("Datum"):
            frame[column] = pandas.to_datetime(frame[column], dayfirst=True)

    return frame
