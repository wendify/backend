"""
Stack-Modell Algorithmus zur Erzeugungszuordnung (korrigiert)

- Erneuerbare werden bevorzugt: Sie decken die Nachfrage so weit wie möglich,
  und werden nur abgeregelt, wenn sonst Überschuss entsteht, der nicht über
  konventionelles Abregeln (Ramp-Down + Mindestleistung) vermieden werden kann.

- Konventionelle werden mit Ramp-Limits (± 2*reg*max_avail) geregelt.
- Mindestleistung (MUSS) für EPS < reg < 1-EPS: prev_realized * (1 - reg)
  (geclippt auf [0, max_avail])

Wichtige Fixes:
- EPS-Logik statt `reg == 0.0` (sonst werden PV/Wind oft NICHT als erneuerbar erkannt)
- Überschuss wird sauber behandelt: konventionell runterregeln, erst dann (falls nötig)
  Erneuerbare proportional abregeln.
"""

import time
from typing import Dict, List

import numpy as np
import pandas as pd

from core.datenreihe import Datenreihe
from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.smard import Smard
from core.types import ErzeugerArt, VerbraucherArt


# Prioritätenreihenfolge für das Auffüllen bei Unterdeckung
PRIORITY_ORDER = [
	ErzeugerArt.Kernenergie,
	ErzeugerArt.Pumpspeicher,
	ErzeugerArt.Biomasse,
	ErzeugerArt.Erdgas,
	ErzeugerArt.Steinkohle,
	ErzeugerArt.Braunkohle,
	ErzeugerArt.SonstigeKonventionelle,
]

EPS = 1e-9


def calculate_realized_generation(
	max_available_datenreihen: Dict[ErzeugerArt, Datenreihe],
	verbrauch_datenreihe: Datenreihe,
	smard: Smard,
	previous_realisiert: Dict[ErzeugerArt, Datenreihe] | None = None,
) -> Dict[ErzeugerArt, Datenreihe]:
	"""
	Berechnet die realisierte Erzeugung aus der maximal verfügbaren Erzeugung je Zeitschritt.

	Dispatch-Logik:
	1) Mindestleistung (MUSS) für konventionelle mit EPS<reg<1-EPS aus prev*(1-reg)
	2) Erneuerbare decken den Rest der Nachfrage (Curtailment nur wenn Überschuss nicht anders weg geht)
	3) Konventionelle decken verbleibenden Bedarf nach Priorität (Ramp-Limits)
	4) Falls Überschuss entsteht (Ramp-Down/MUSS), wird konventionell abgeregelt,
	   und erst wenn das nicht reicht, werden Erneuerbare proportional abgeregelt.
	"""

	# ==========================================================================
	# Schritt 1: Gemeinsames Zeitraster (pandas)
	# ==========================================================================

	verbrauch_indexed = verbrauch_datenreihe.df.set_index("Datum von")
	if verbrauch_indexed.index.has_duplicates:
		verbrauch_indexed = verbrauch_indexed.groupby(level=0).mean()

	time_index = verbrauch_indexed.index
	total_steps = len(time_index)

	verbrauch_series = verbrauch_indexed[verbrauch_datenreihe.art]

	max_available_df = pd.DataFrame(index=time_index)
	for art, datenreihe in max_available_datenreihen.items():
		max_available_indexed = datenreihe.df.set_index("Datum von")
		if max_available_indexed.index.has_duplicates:
			max_available_indexed = max_available_indexed.groupby(level=0).mean()
		max_available_series = max_available_indexed[art]
		reindexed = max_available_series.reindex(time_index)
		max_available_df[art] = reindexed.ffill().fillna(0.0)

	arts = list(max_available_datenreihen.keys())
	num_arts = len(arts)
	art_to_idx = {art: i for i, art in enumerate(arts)}

	# ==========================================================================
	# Schritt 2: regulation-Werte nur einmal holen
	# ==========================================================================

	regulation_arr = np.zeros(num_arts, dtype=np.float64)
	for art in arts:
		erz = smard.get_erzeuger(art)
		regulation_arr[art_to_idx[art]] = float(erz.regulation)

	renewable_indices: List[int] = []
	dispatchable_indices: List[int] = []

	# !!! WICHTIG: EPS statt == 0.0
	for i in range(num_arts):
		if regulation_arr[i] <= EPS:
			renewable_indices.append(i)
		else:
			dispatchable_indices.append(i)

	# Dispatch-Reihenfolge (hochfahren) nach Priorität
	priority_indices: List[int] = []
	for art in PRIORITY_ORDER:
		if art in art_to_idx:
			idx = art_to_idx[art]
			if regulation_arr[idx] > EPS:
				priority_indices.append(idx)

	priority_set = set(priority_indices)
	remaining_dispatch_indices: List[int] = [
		i for i in dispatchable_indices if i not in priority_set
	]

	dispatch_up_order = priority_indices + remaining_dispatch_indices
	dispatch_down_order = list(reversed(dispatch_up_order))  # bei Überschuss: umgekehrt reduzieren

	# ==========================================================================
	# Schritt 3: pandas -> numpy
	# ==========================================================================

	max_available_arr = np.zeros((total_steps, num_arts), dtype=np.float64)
	for i, art in enumerate(arts):
		max_available_arr[:, i] = max_available_df[art].values.astype(np.float64)

	verbrauch_arr = verbrauch_series.values.astype(np.float64)

	prev_realized_arr = np.zeros(num_arts, dtype=np.float64)
	if previous_realisiert is not None:
		for art, datenreihe in previous_realisiert.items():
			if art in art_to_idx:
				idx = art_to_idx[art]
				previous_indexed = datenreihe.df.set_index("Datum von")
				if previous_indexed.index.has_duplicates:
					previous_indexed = previous_indexed.groupby(level=0).mean()
				previous_series = previous_indexed[art]
				if len(previous_series) > 0:
					prev_realized_arr[idx] = float(previous_series.iloc[-1])

	# ==========================================================================
	# Schritt 4: Ergebnis-Array
	# ==========================================================================

	result_arr = np.zeros((total_steps, num_arts), dtype=np.float64)

	# Hilfs-Arrays (wiederverwendet)
	out = np.zeros(num_arts, dtype=np.float64)
	min_out = np.zeros(num_arts, dtype=np.float64)

	print(f"Berechne {total_steps} Zeitschritte (korrigiert/optimiert)...")
	loop_start = time.time()
	progress_interval = 50000

	debug_surplus_steps = 0
	debug_bedarf_steps = 0

	# Zeitschritt-Dauer für Datum bis (besser als hardcoded 15 min)
	if total_steps >= 2:
		step_delta = time_index[1] - time_index[0]
	else:
		step_delta = pd.Timedelta(minutes=15)

	for step_idx in range(total_steps):
		max_avail_t = max_available_arr[step_idx]
		demand_t = float(verbrauch_arr[step_idx])

		out.fill(0.0)
		min_out.fill(0.0)

		# ---------------------------------------------------------------------
		# 1) Mindestleistung (MUSS) für Dispatchables
		# ---------------------------------------------------------------------
		for idx in dispatchable_indices:
			reg = regulation_arr[idx]
			prev = prev_realized_arr[idx]
			max_avail = max_avail_t[idx]
			if max_avail < 0.0:
				max_avail = 0.0

			# Mindestleistung nur für EPS < reg < 1-EPS
			if (reg > EPS) and (reg < 1.0 - EPS):
				base = prev * (1.0 - reg)
			else:
				base = 0.0

			val = base
			if val < 0.0:
				val = 0.0
			if val > max_avail:
				val = max_avail

			min_out[idx] = val
			out[idx] = val

		remaining = demand_t - float(out.sum())

		# ---------------------------------------------------------------------
		# 2) Erneuerbare bevorzugt nutzen (nur bis Nachfrage gedeckt)
		# ---------------------------------------------------------------------
		if remaining > 0.0 and len(renewable_indices) > 0:
			avail_ren = max_avail_t[renewable_indices].copy()
			avail_ren[avail_ren < 0.0] = 0.0
			total_ren = float(avail_ren.sum())

			if total_ren <= remaining + 1e-12:
				out[renewable_indices] = avail_ren
				remaining -= total_ren
			else:
				scale = remaining / total_ren if total_ren > 0.0 else 0.0
				out[renewable_indices] = avail_ren * scale
				remaining = 0.0

		if remaining <= 0.0:
			debug_surplus_steps += 1
		else:
			debug_bedarf_steps += 1

		# ---------------------------------------------------------------------
		# 3) Konventionelle hochfahren (Priority) mit Ramp-Limits
		# ---------------------------------------------------------------------
		if remaining > 0.0:
			for idx in dispatch_up_order:
				if remaining <= 0.0:
					break

				reg = regulation_arr[idx]
				max_avail = max_avail_t[idx]
				if max_avail < 0.0:
					max_avail = 0.0

				prev = prev_realized_arr[idx]
				max_delta = 2.0 * reg * max_avail

				lower = prev - max_delta
				if lower < 0.0:
					lower = 0.0
				upper = prev + max_delta
				if upper > max_avail:
					upper = max_avail

				if lower < min_out[idx]:
					lower = min_out[idx]

				# Wenn wir technisch nicht so weit runter dürfen, muss out mindestens lower sein
				if out[idx] < lower:
					delta = lower - out[idx]
					out[idx] = lower
					remaining -= delta
					if remaining <= 0.0:
						break

				headroom = upper - out[idx]
				if headroom <= 0.0:
					continue

				add = headroom if headroom <= remaining else remaining
				out[idx] += add
				remaining -= add

		# ---------------------------------------------------------------------
		# 4) Überschussbehandlung: konventionell runter, dann (falls nötig) EE abregeln
		# ---------------------------------------------------------------------
		if remaining < -1e-9:
			surplus = -remaining

			# 4a) Dispatchables runterregeln (Ramp-Down + Mindestleistung)
			for idx in dispatch_down_order:
				if surplus <= 0.0:
					break

				reg = regulation_arr[idx]
				max_avail = max_avail_t[idx]
				if max_avail < 0.0:
					max_avail = 0.0

				prev = prev_realized_arr[idx]
				max_delta = 2.0 * reg * max_avail

				lower = prev - max_delta
				if lower < 0.0:
					lower = 0.0
				if lower < min_out[idx]:
					lower = min_out[idx]

				reducible = out[idx] - lower
				if reducible <= 0.0:
					continue

				red = reducible if reducible <= surplus else surplus
				out[idx] -= red
				surplus -= red

			# 4b) Wenn immer noch Überschuss: Erneuerbare proportional abregeln (last resort)
			if surplus > 1e-9 and len(renewable_indices) > 0:
				ren_now = out[renewable_indices].copy()
				total_ren_now = float(ren_now.sum())
				if total_ren_now > 0.0:
					new_total = total_ren_now - surplus
					if new_total < 0.0:
						new_total = 0.0
					scale = new_total / total_ren_now
					out[renewable_indices] = ren_now * scale
					surplus = 0.0

			remaining = -surplus

		# ---------------------------------------------------------------------
		# 5) Ergebnis speichern & prev updaten
		# ---------------------------------------------------------------------
		out[out < 0.0] = 0.0
		result_arr[step_idx, :] = out
		prev_realized_arr[:] = out

		if (step_idx + 1) % progress_interval == 0:
			elapsed = time.time() - loop_start
			progress_pct = ((step_idx + 1) / total_steps) * 100
			avg = elapsed / (step_idx + 1)
			eta = avg * (total_steps - (step_idx + 1))
			print(
				f"  Fortschritt: {step_idx + 1}/{total_steps} ({progress_pct:.1f}%) | "
				f"Zeit: {elapsed:.1f}s | Verbleibend: {eta:.1f}s"
			)

	loop_duration = time.time() - loop_start
	print(f"Berechnung abgeschlossen in {loop_duration:.2f} Sekunden")
	print(
		f"  DEBUG: Überschuss-Schritte (remaining <= 0): {debug_surplus_steps} "
		f"({100*debug_surplus_steps/total_steps:.1f}%)"
	)
	print(
		f"  DEBUG: Bedarf-Schritte (remaining > 0): {debug_bedarf_steps} "
		f"({100*debug_bedarf_steps/total_steps:.1f}%)"
	)

	# ==========================================================================
	# Schritt 6: numpy -> Datenreihen
	# ==========================================================================

	result: Dict[ErzeugerArt, Datenreihe] = {}
	datum_von = time_index.to_numpy()
	datum_bis = (time_index + step_delta).to_numpy()

	for i, art in enumerate(arts):
		df = pd.DataFrame()
		df["Datum von"] = datum_von
		df["Datum bis"] = datum_bis
		df[art] = result_arr[:, i]
		result[art] = Datenreihe(art, df)

	return result


def apply_stack_model_to_ausbaupfad(
	ausbaupfad: Ausbaupfad,
	smard: Smard,
	verbrauch_art: VerbraucherArt = VerbraucherArt.Netzlast,
) -> Dict[ErzeugerArt, Datenreihe]:
	"""
	Wendet den Stack-Modell-Algorithmus auf einen Ausbaupfad an.
	"""

	# Maximal verfügbare Erzeugung aus Prognose-Zeitreihen extrahieren
	max_available_datenreihen: Dict[ErzeugerArt, Datenreihe] = {}
	for datenreihe in ausbaupfad.prognose_datenreihen:
		art = datenreihe.art
		df = datenreihe.df[["Datum von", "Datum bis", art]].copy()
		max_available_datenreihen[art] = Datenreihe(art, df)

	# Verbrauchsreihe wählen
	verbrauch_datenreihe = None
	if ausbaupfad.prognose_verbraucher_datenreihen:
		for dr in ausbaupfad.prognose_verbraucher_datenreihen:
			if dr.art == verbrauch_art:
				verbrauch_datenreihe = dr
				break
		if verbrauch_datenreihe is None:
			verbrauch_datenreihe = ausbaupfad.prognose_verbraucher_datenreihen[0]

	if verbrauch_datenreihe is None:
		verbrauch_datenreihe = smard.get_verbraucher(verbrauch_art)

	# Startzustand aus SMARD (prev_realized)
	previous_realisiert: Dict[ErzeugerArt, Datenreihe] = {}
	for art in max_available_datenreihen.keys():
		erzeuger = smard.get_erzeuger(art)
		previous_realisiert[art] = erzeuger.realisiert

	return calculate_realized_generation(
		max_available_datenreihen=max_available_datenreihen,
		verbrauch_datenreihe=verbrauch_datenreihe,
		smard=smard,
		previous_realisiert=previous_realisiert,
	)
