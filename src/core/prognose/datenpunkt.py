from dataclasses import dataclass
from datetime import datetime

from core.types import ErzeugerArt


@dataclass
class Datenpunkt:
    art: ErzeugerArt
    datetime: datetime
    installiert: float
