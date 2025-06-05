from dataclasses import dataclass
import enum


@dataclass
class ErzeugerIds:
    installiert: int
    realisiert: int


class _RohArten(enum.Enum):
    Braunkohle = ErzeugerIds(3004073, 1001223)
    Kernenergie = ErzeugerIds(3004076, 1001224)
    WindOffshore = ErzeugerIds(3004072, 1001225)
    Wasserkraft = ErzeugerIds(3004074, 1001226)
    SonstigeKonventionelle = ErzeugerIds(3004075, 1001227)
    SonstigeErneuerbare = ErzeugerIds(3000186, 1001228)
    Biomasse = ErzeugerIds(3000188, 1004066)
    WindOnshore = ErzeugerIds(3000189, 1004067)
    Photovoltaik = ErzeugerIds(3000194, 1004068)
    Steinkohle = ErzeugerIds(3000198, 1004069)
    Pumpspeicher = ErzeugerIds(3003792, 1004070)
    Erdgas = ErzeugerIds(3000207, 1004071)


class ErzeugerArt(enum.StrEnum):
    Braunkohle = "Braunkohle"
    Kernenergie = "Kernenergie"
    WindOffshore = "Wind Offshore"
    Wasserkraft = "Wasserkraft"
    SonstigeKonventionelle = "Sonstige Konventionelle"
    SonstigeErneuerbare = "Sonstige Erneuerbare"
    Biomasse = "Biomasse"
    WindOnshore = "Wind Onshore"
    Photovoltaik = "Photovoltaik"
    Steinkohle = "Steinkohle"
    Pumpspeicher = "Pumpspeicher"
    Erdgas = "Erdgas"
