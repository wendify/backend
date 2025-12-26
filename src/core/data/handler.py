import logging
import sys
from pathlib import Path
from typing import TypedDict

import requests

import config


# JSON-Format einer Teilanfrage
class Form(TypedDict):
	format: str
	language: str
	moduleIds: list[int]
	region: str
	resolution: str
	timestamp_from: int
	timestamp_to: int


# JSON-Format einer ganzen Anfrage
class Request(TypedDict):
	request_form: list[Form]


# Lädt eine CSV-Datei von SMARD herunter
def download(ids: list[int], path: Path) -> None:
	logging.info(f"CSV-Datei wird heruntergeladen: {path}")

	form: Form = {
		"format": "CSV",
		"language": "de",
		"moduleIds": ids,
		"region": "DE",
		"resolution": "quarterhour",
		"timestamp_from": int(config.SMARD_FROM.timestamp() * 1000),
		"timestamp_to": int(config.SMARD_TO.timestamp() * 1000),
	}

	request: Request = {
		"request_form": [form],
	}

	with requests.post(config.SMARD_URL, json=request) as response:
		# Bei HTTP-Fehler diesen ausgeben und beenden
		if not response.ok:
			logging.error(response.text)
			sys.exit()

		# Inhalt in die angegebene Datei schreiben
		with open(path, "wb") as file:
			file.write(response.content)
