"""
Default energy transition scenario (Energiewende-Szenario).

This scenario is based on:
- EEG targets for renewable energy expansion
- Coal phase-out plans
- Nuclear exit (already completed)
- Projected grid load development
"""

import datetime
from typing import Tuple, List

from core.prognose.datenpunkt import ErzeugerDatenpunkt, VerbraucherDatenpunkt
from core.setup.smard import Smard
from core.types import ErzeugerArt, VerbraucherArt


def create_default_scenario(
	smard: Smard,
) -> Tuple[List[ErzeugerDatenpunkt], List[VerbraucherDatenpunkt]]:
	"""
	Creates the default energy transition scenario.
	
	This scenario includes:
	- Strong PV expansion (EEG targets)
	- Moderate to strong wind expansion
	- Coal phase-out by 2030-2038
	- Nuclear at 0 (exit completed)
	- Gas as bridging technology
	
	Args:
		smard: SMARD data source for current baseline values
		
	Returns:
		Tuple of (erzeuger_datenpunkte, verbraucher_datenpunkte)
	"""
	# Load current generator data from SMARD
	pv = smard.get_erzeuger(ErzeugerArt.Photovoltaik)
	wind_on = smard.get_erzeuger(ErzeugerArt.WindOnshore)
	wind_off = smard.get_erzeuger(ErzeugerArt.WindOffshore)
	wasser = smard.get_erzeuger(ErzeugerArt.Wasserkraft)
	biomasse = smard.get_erzeuger(ErzeugerArt.Biomasse)
	pumpsp = smard.get_erzeuger(ErzeugerArt.Pumpspeicher)
	sonst_ern = smard.get_erzeuger(ErzeugerArt.SonstigeErneuerbare)
	erdgas = smard.get_erzeuger(ErzeugerArt.Erdgas)
	steinkohle = smard.get_erzeuger(ErzeugerArt.Steinkohle)
	braunkohle = smard.get_erzeuger(ErzeugerArt.Braunkohle)
	kernenergie = smard.get_erzeuger(ErzeugerArt.Kernenergie)
	sonst_konv = smard.get_erzeuger(ErzeugerArt.SonstigeKonventionelle)
	
	# =========================================================================
	# ERZEUGER-DATENPUNKTE (installed capacity in MW)
	# =========================================================================
	
	erzeuger_datenpunkte: List[ErzeugerDatenpunkt] = [
		# -----------------------------------------------------------------
		# ERNEUERBARE ENERGIEN - Ausbaupfad
		# -----------------------------------------------------------------
		
		# Photovoltaik (starker Ausbau, EEG-Ziele angelehnt)
		ErzeugerDatenpunkt(pv.art, datetime.datetime(2026, 1, 1), 130_000),   # ~130 GW
		ErzeugerDatenpunkt(pv.art, datetime.datetime(2030, 1, 1), 215_000),   # ~215 GW
		ErzeugerDatenpunkt(pv.art, datetime.datetime(2035, 1, 1), 260_000),   # ~260 GW
		
		# Wind Onshore (moderater bis starker Ausbau)
		ErzeugerDatenpunkt(wind_on.art, datetime.datetime(2026, 1, 1), 70_000),    # ~70 GW
		ErzeugerDatenpunkt(wind_on.art, datetime.datetime(2030, 1, 1), 85_000),    # ~85 GW
		ErzeugerDatenpunkt(wind_on.art, datetime.datetime(2035, 1, 1), 100_000),   # ~100 GW
		
		# Wind Offshore (Ausbau, etwas unter Zielpfad wegen Realisierungsrisiken)
		ErzeugerDatenpunkt(wind_off.art, datetime.datetime(2026, 1, 1), 11_000),   # ~11 GW
		ErzeugerDatenpunkt(wind_off.art, datetime.datetime(2030, 1, 1), 25_000),   # ~25 GW
		ErzeugerDatenpunkt(wind_off.art, datetime.datetime(2035, 1, 1), 40_000),   # ~40 GW
		
		# Wasserkraft (nahezu konstant, nur geringer Zubau möglich)
		ErzeugerDatenpunkt(wasser.art, datetime.datetime(2026, 1, 1), 5_600),
		ErzeugerDatenpunkt(wasser.art, datetime.datetime(2030, 1, 1), 5_800),
		ErzeugerDatenpunkt(wasser.art, datetime.datetime(2035, 1, 1), 6_000),
		
		# Biomasse (leicht rückläufig / plateau, EEG sieht kaum Ausbau vor)
		ErzeugerDatenpunkt(biomasse.art, datetime.datetime(2026, 1, 1), 9_500),
		ErzeugerDatenpunkt(biomasse.art, datetime.datetime(2030, 1, 1), 9_000),
		ErzeugerDatenpunkt(biomasse.art, datetime.datetime(2035, 1, 1), 8_000),
		
		# Pumpspeicher (leichter Ausbau + Modernisierung)
		ErzeugerDatenpunkt(pumpsp.art, datetime.datetime(2026, 1, 1), 10_000),
		ErzeugerDatenpunkt(pumpsp.art, datetime.datetime(2030, 1, 1), 11_000),
		ErzeugerDatenpunkt(pumpsp.art, datetime.datetime(2035, 1, 1), 13_000),
		
		# Sonstige Erneuerbare (Geothermie, Deponiegas etc.)
		ErzeugerDatenpunkt(sonst_ern.art, datetime.datetime(2026, 1, 1), 1_500),
		ErzeugerDatenpunkt(sonst_ern.art, datetime.datetime(2030, 1, 1), 3_000),
		ErzeugerDatenpunkt(sonst_ern.art, datetime.datetime(2035, 1, 1), 5_000),
		
		# -----------------------------------------------------------------
		# KONVENTIONELLE ERZEUGER - Rückbaupfad
		# -----------------------------------------------------------------
		
		# Erdgas (etwas Ausbau H2-ready, später leichte Reduktion)
		ErzeugerDatenpunkt(erdgas.art, datetime.datetime(2026, 1, 1), 36_000),
		ErzeugerDatenpunkt(erdgas.art, datetime.datetime(2030, 1, 1), 40_000),
		ErzeugerDatenpunkt(erdgas.art, datetime.datetime(2035, 1, 1), 38_000),
		
		# Steinkohle (deutlicher Rückbau, Ausstieg ≈ 2030)
		ErzeugerDatenpunkt(steinkohle.art, datetime.datetime(2026, 1, 1), 12_000),
		ErzeugerDatenpunkt(steinkohle.art, datetime.datetime(2030, 1, 1), 3_000),
		ErzeugerDatenpunkt(steinkohle.art, datetime.datetime(2035, 1, 1), 0),
		
		# Braunkohle (Rückbau bis spätestens 2038, 2035 fast aus dem Markt)
		ErzeugerDatenpunkt(braunkohle.art, datetime.datetime(2026, 1, 1), 13_000),
		ErzeugerDatenpunkt(braunkohle.art, datetime.datetime(2030, 1, 1), 8_000),
		ErzeugerDatenpunkt(braunkohle.art, datetime.datetime(2035, 1, 1), 2_000),
		
		# Kernenergie (bleibt bei 0 – Ausstieg vollzogen)
		ErzeugerDatenpunkt(kernenergie.art, datetime.datetime(2026, 1, 1), 0),
		ErzeugerDatenpunkt(kernenergie.art, datetime.datetime(2030, 1, 1), 0),
		ErzeugerDatenpunkt(kernenergie.art, datetime.datetime(2035, 1, 1), 0),
		
		# Sonstige konventionelle (Öl, Abfall, Industrieanlagen etc.)
		ErzeugerDatenpunkt(sonst_konv.art, datetime.datetime(2026, 1, 1), 4_000),
		ErzeugerDatenpunkt(sonst_konv.art, datetime.datetime(2030, 1, 1), 3_500),
		ErzeugerDatenpunkt(sonst_konv.art, datetime.datetime(2035, 1, 1), 3_000),
	]
	
	# =========================================================================
	# VERBRAUCHER-DATENPUNKTE (grid load forecast in MW)
	# =========================================================================
	
	# Get current average grid load as baseline
	netzlast = smard.get_verbraucher(VerbraucherArt.Netzlast)
	current_mean_load = netzlast.df["Netzlast"].mean()
	
	verbraucher_datenpunkte: List[VerbraucherDatenpunkt] = [
		# Grid load expected to increase due to electrification (heat pumps, EVs, etc.)
		VerbraucherDatenpunkt(VerbraucherArt.Netzlast, datetime.datetime(2026, 1, 1), current_mean_load),
		VerbraucherDatenpunkt(VerbraucherArt.Netzlast, datetime.datetime(2030, 1, 1), current_mean_load * 10),
		VerbraucherDatenpunkt(VerbraucherArt.Netzlast, datetime.datetime(2035, 1, 1), current_mean_load),
	]
	
	return erzeuger_datenpunkte, verbraucher_datenpunkte

