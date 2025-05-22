import datetime
import sys
import typing

import requests

import erzeuger


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
		"timestamp_from": int(datetime.datetime(2015, 1, 1).timestamp()) * 1000,
		"timestamp_to": int(datetime.datetime(2025, 1, 1).timestamp()) * 1000,
	}

	request: Request = {
		"request_form": [form],
	}

	with requests.post(url, json=request) as response:
		if not response.ok:
			sys.exit("Fehler: " + response.text)

		with open(path, "bw") as file:
			file.write(response.content)


def main() -> None:
	path = "erzeuger.csv"
	url = "https://www.smard.de/nip-download-manager/nip/download/market-data"

	download(path, url)
