import datetime
import logging
import pathlib
import sys
import typing

import requests


class Form(typing.TypedDict):
	format: str
	language: str
	moduleIds: list[int]
	region: str
	resolution: str
	timestamp_from: int
	timestamp_to: int


class Request(typing.TypedDict):
	request_form: list[Form]


def download(path: pathlib.Path, url: str, ids: list[int]) -> None:
	form: Form = {
		"format": "CSV",
		"language": "de",
		"moduleIds": ids,
		"region": "DE",
		"resolution": "quarterhour",
		"timestamp_from": int(datetime.datetime(2024, 1, 1).timestamp()) * 1000,
		"timestamp_to": int(datetime.datetime(2025, 10, 31).timestamp()) * 1000,
	}

	request: Request = {
		"request_form": [form],
	}

	with requests.post(url, json=request) as response:
		if not response.ok:
			logging.error(response.text)
			sys.exit()

		with open(path, "wb") as file:
			file.write(response.content)
