from enum import StrEnum


class ErzeugerArt(StrEnum):
	Biomasse = "Biomasse"
	Braunkohle = "Braunkohle"
	Erdgas = "Erdgas"
	Kernenergie = "Kernenergie"
	Photovoltaik = "Photovoltaik"
	Pumpspeicher = "Pumpspeicher"
	SonstigeErneuerbare = "Sonstige Erneuerbare"
	SonstigeKonventionelle = "Sonstige Konventionelle"
	Steinkohle = "Steinkohle"
	Wasserkraft = "Wasserkraft"
	WindOffshore = "Wind Offshore"
	WindOnshore = "Wind Onshore"


class VerbraucherArt(StrEnum):
	Netzlast = "Netzlast"
	NetzlastInklPumpspeicher = "Netzlast inkl. Pumpspeicher"
	Pumpspeicher = "Pumpspeicher"
	Residuallast = "Residuallast"
