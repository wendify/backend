"""
Stack-Modell Algorithmus zur Erzeugungszuordnung

Dieses Modul implementiert den Algorithmus zur Berechnung der tatsächlich
realisierten Erzeugung aus der maximal verfügbaren Erzeugung je Zeitschritt
unter Berücksichtigung des Verbrauchs und der Regulierungsfähigkeit der Erzeuger.

Die maximal verfügbare Erzeugung entspricht installierte Leistung × normiertes Profil,
also bereits zeitlich aufgelöste MW pro Zeitschritt (z.B. 15 min), wie sie in den
Prognose-Zeitreihen des Ausbaupfads enthalten sind.

Der Algorithmus arbeitet sequentiell über die Zeit: Jeder Zeitschritt basiert
auf der realisierten Erzeugung des vorherigen Zeitschritts, nicht auf statischen
SMARD-Werten. Dies ermöglicht realistische Regelbewegungen (Ramp-Rates) für
konventionelle Erzeuger.

Pro Zeitschritt werden folgende Schritte durchgeführt:
1. Berechnung der MUSS-Erzeugung für regelbare Erzeuger (basierend auf vorherigem Schritt)
2. Hinzufügen der erneuerbaren Erzeuger (regulation = 0)
3. Auffüllen nach Priorität mit dynamischer Regelung (Ramp-Rate: 2 × regulation)
4. Prioritätenreihenfolge bei Unterdeckung

OPTIMIERT: Verwendet numpy-Arrays statt pandas für 50-100x Geschwindigkeitssteigerung.
"""

import logging
import time
from typing import Dict, List

import numpy as np
import pandas as pd

from core.datenreihe import Datenreihe
from core.erzeuger import Erzeuger
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


def calculate_realized_generation(
	max_available_datenreihen: Dict[ErzeugerArt, Datenreihe],
	verbrauch_datenreihe: Datenreihe,
	smard: Smard,
	previous_realisiert: Dict[ErzeugerArt, Datenreihe] | None = None,
) -> Dict[ErzeugerArt, Datenreihe]:
	"""
	Berechnet die realisierte Erzeugung aus der maximal verfügbaren Erzeugung je Zeitschritt.

	Die Berechnung erfolgt sequentiell über die Zeit: Jeder Zeitschritt basiert auf der
	realisierten Erzeugung des vorherigen Zeitschritts, nicht auf statischen SMARD-Werten.
	Dies ermöglicht realistische Regelbewegungen (Ramp-Rates) für konventionelle Erzeuger.

	Die maximal verfügbare Erzeugung entspricht installierte Leistung × normiertes Profil,
	also bereits zeitlich aufgelöste MW pro Zeitschritt (z.B. 15 min).

	OPTIMIERT: Verwendet numpy-Arrays für schnelle Berechnung.

	Args:
		max_available_datenreihen: Dictionary mit maximal verfügbarer Erzeugung je ErzeugerArt
			(installiert × normiert, bereits in MW je Zeitschritt)
		verbrauch_datenreihe: Datenreihe mit dem Verbrauch/Bedarf
		smard: SMARD-Objekt für Regulation-Werte
		previous_realisiert: Optional: Vorherige realisierte Werte für Startzustand (SMARD)

	Returns:
		Dictionary mit realisierten Erzeugungen je ErzeugerArt
	"""
	# ==========================================================================
	# Schritt 1: Alle DataFrames auf gemeinsames Zeitraster bringen (pandas)
	# ==========================================================================
	
	# Entferne doppelte Zeitpunkte aus dem Verbrauch-Index
	verbrauch_indexed = verbrauch_datenreihe.df.set_index("Datum von")
	if verbrauch_indexed.index.has_duplicates:
		verbrauch_indexed = verbrauch_indexed.groupby(level=0).mean()
	
	time_index = verbrauch_indexed.index
	total_steps = len(time_index)
	
	# Verbrauch als Series
	verbrauch_series = verbrauch_indexed[verbrauch_datenreihe.art]
	
	# Maximal verfügbare Erzeugung je Erzeuger als DataFrame
	max_available_df = pd.DataFrame(index=time_index)
	for art, datenreihe in max_available_datenreihen.items():
		max_available_indexed = datenreihe.df.set_index("Datum von")
		if max_available_indexed.index.has_duplicates:
			max_available_indexed = max_available_indexed.groupby(level=0).mean()
		max_available_series = max_available_indexed[art]
		reindexed = max_available_series.reindex(time_index)
		max_available_df[art] = reindexed.ffill().fillna(0)
	
	# Liste der Erzeugerarten (stabile Reihenfolge)
	arts = list(max_available_datenreihen.keys())
	num_arts = len(arts)
	
	# Mapping: art -> index für schnellen Zugriff
	art_to_idx = {art: i for i, art in enumerate(arts)}
	
	# ==========================================================================
	# Schritt 2: Pre-compute regulation values (NUR EINMAL, nicht 17M mal!)
	# ==========================================================================
	
	# Regulation-Werte als numpy-Array (index entspricht art_to_idx)
	regulation_arr = np.zeros(num_arts, dtype=np.float64)
	for art in arts:
		erz = smard.get_erzeuger(art)
		regulation_arr[art_to_idx[art]] = erz.regulation
	
	# Pre-kategorisiere Erzeuger nach Regulationstyp
	# Indizes für erneuerbare Erzeuger (regulation == 0)
	renewable_indices = []
	for i, art in enumerate(arts):
		if regulation_arr[i] == 0.0:
			renewable_indices.append(i)
	
	# Indizes für MUSS-Erzeuger (0 < regulation < 1)
	muss_indices = []
	for i, art in enumerate(arts):
		if regulation_arr[i] > 0.0 and regulation_arr[i] < 1.0:
			muss_indices.append(i)
	
	# Indizes für Priority-Order (nur die, die in arts vorhanden sind)
	priority_indices = []
	for art in PRIORITY_ORDER:
		if art in art_to_idx:
			idx = art_to_idx[art]
			# Nur konventionelle (regulation > 0)
			if regulation_arr[idx] > 0.0:
				priority_indices.append(idx)
	
	# Indizes für Erzeuger außerhalb der Prioritätenliste (aber konventionell)
	priority_set = set(priority_indices)
	remaining_conv_indices = []
	for i in range(num_arts):
		if i not in priority_set and regulation_arr[i] > 0.0:
			remaining_conv_indices.append(i)
	
	# ==========================================================================
	# Schritt 3: Konvertiere pandas zu numpy-Arrays für schnelle Indizierung
	# ==========================================================================
	
	# max_available als 2D numpy array: shape (num_steps, num_arts)
	# Spaltenreihenfolge muss arts entsprechen
	max_available_arr = np.zeros((total_steps, num_arts), dtype=np.float64)
	for i, art in enumerate(arts):
		max_available_arr[:, i] = max_available_df[art].values
	
	# Verbrauch als 1D numpy array
	verbrauch_arr = verbrauch_series.values.astype(np.float64)
	
	# Startzustand prev_realized als numpy array
	prev_realized_arr = np.zeros(num_arts, dtype=np.float64)
	if previous_realisiert is not None:
		for art, datenreihe in previous_realisiert.items():
			if art in art_to_idx:
				idx = art_to_idx[art]
				previous_indexed = datenreihe.df.set_index("Datum von")
				if previous_indexed.index.has_duplicates:
					previous_indexed = previous_indexed.groupby(level=0).mean()
				previous_series = previous_indexed[art]
				# Letzter verfügbarer Wert
				if len(previous_series) > 0:
					prev_realized_arr[idx] = float(previous_series.iloc[-1])
	
	# ==========================================================================
	# Schritt 4: Pre-allocate result array
	# ==========================================================================
	
	result_arr = np.zeros((total_steps, num_arts), dtype=np.float64)
	
	# ==========================================================================
	# Schritt 5: Hauptschleife über alle Zeitschritte (optimiert)
	# ==========================================================================
	
	print(f"Berechne {total_steps} Zeitschritte (optimiert)...")
	loop_start = time.time()
	progress_interval = 50000  # Alle 50000 Zeitschritte Progress-Print
	
	# Temporäre Arrays für jeden Zeitschritt (einmal allokieren, wiederverwenden)
	muss_arr = np.zeros(num_arts, dtype=np.float64)
	erneuerbar_arr = np.zeros(num_arts, dtype=np.float64)
	konv_arr = np.zeros(num_arts, dtype=np.float64)
	
	for step_idx in range(total_steps):
		# Hole Daten für diesen Zeitschritt (direkte numpy-Indizierung)
		max_avail_t = max_available_arr[step_idx]
		demand_t = verbrauch_arr[step_idx]
		
		# Reset temporäre Arrays
		muss_arr.fill(0.0)
		erneuerbar_arr.fill(0.0)
		konv_arr.fill(0.0)
		
		# ---------------------------------------------------------------------
		# Schritt 5.1: MUSS-Erzeugung für Erzeuger mit 0 < regulation < 1
		# ---------------------------------------------------------------------
		current_stack = 0.0
		
		for idx in muss_indices:
			reg = regulation_arr[idx]
			base_prev = prev_realized_arr[idx]
			value = base_prev * (1.0 - reg)
			if value < 0.0:
				value = 0.0
			max_avail = max_avail_t[idx]
			if value > max_avail:
				value = max_avail
			muss_arr[idx] = value
			current_stack += value
		
		remaining = demand_t - current_stack
		
		# ---------------------------------------------------------------------
		# Schritt 5.2: Erneuerbare Erzeuger (regulation == 0)
		# ---------------------------------------------------------------------
		for idx in renewable_indices:
			if remaining <= 0.0:
				break
			avail = max_avail_t[idx]
			add = avail
			if add > remaining:
				add = remaining
			if add < 0.0:
				add = 0.0
			erneuerbar_arr[idx] = add
			current_stack += add
			remaining -= add
		
		# ---------------------------------------------------------------------
		# Schritt 5.3: Konventionelle nach Priorität auffüllen
		# ---------------------------------------------------------------------
		for idx in priority_indices:
			if remaining <= 0.0:
				break
			
			reg = regulation_arr[idx]
			if reg == 0.0:
				continue
			
			max_avail = max_avail_t[idx]
			base_prev = prev_realized_arr[idx]
			base_muss = muss_arr[idx]
			
			# Ramp-Rate
			max_delta_up = 2.0 * reg * max_avail
			
			# Kandidat: alter Wert + Ramp-Rate
			candidate = base_prev + max_delta_up
			if candidate > max_avail:
				candidate = max_avail
			
			# Target
			target = base_muss + remaining
			if target < base_muss:
				target = base_muss
			
			new_value = candidate
			if new_value > target:
				new_value = target
			if new_value < base_muss:
				new_value = base_muss
			
			additional = new_value - base_muss
			konv_arr[idx] = additional
			current_stack += additional
			remaining -= additional
		
		# ---------------------------------------------------------------------
		# Schritt 5.4: Verbleibende konventionelle Erzeuger
		# ---------------------------------------------------------------------
		for idx in remaining_conv_indices:
			if remaining <= 0.0:
				break
			
			reg = regulation_arr[idx]
			if reg == 0.0:
				continue
			
			max_avail = max_avail_t[idx]
			base_prev = prev_realized_arr[idx]
			base_muss = muss_arr[idx]
			
			max_delta_up = 2.0 * reg * max_avail
			candidate = base_prev + max_delta_up
			if candidate > max_avail:
				candidate = max_avail
			
			target = base_muss + remaining
			if target < base_muss:
				target = base_muss
			
			new_value = candidate
			if new_value > target:
				new_value = target
			if new_value < base_muss:
				new_value = base_muss
			
			additional = new_value - base_muss
			konv_arr[idx] = additional
			current_stack += additional
			remaining -= additional
		
		# ---------------------------------------------------------------------
		# Schritt 5.5: Ergebnis für diesen Zeitschritt zusammenführen
		# ---------------------------------------------------------------------
		for idx in range(num_arts):
			value = muss_arr[idx] + erneuerbar_arr[idx] + konv_arr[idx]
			if value < 0.0:
				value = 0.0
			result_arr[step_idx, idx] = value
			# Update prev_realized für nächsten Schritt
			prev_realized_arr[idx] = value
		
		# Progress-Print
		if (step_idx + 1) % progress_interval == 0:
			elapsed = time.time() - loop_start
			progress_pct = ((step_idx + 1) / total_steps) * 100
			avg_time_per_step = elapsed / (step_idx + 1)
			remaining_steps = total_steps - (step_idx + 1)
			estimated_remaining = avg_time_per_step * remaining_steps
			print(f"  Fortschritt: {step_idx + 1}/{total_steps} ({progress_pct:.1f}%) | "
			      f"Zeit: {elapsed:.1f}s | Verbleibend: {estimated_remaining:.1f}s")
	
	loop_end = time.time()
	loop_duration = loop_end - loop_start
	print(f"Berechnung abgeschlossen in {loop_duration:.2f} Sekunden")
	
	# ==========================================================================
	# Schritt 6: Konvertiere numpy result zurück zu Datenreihen (einmalig)
	# ==========================================================================
	
	result = {}
	datum_von = time_index.to_numpy()
	datum_bis = (time_index + pd.Timedelta(minutes=15)).to_numpy()
	
	for i, art in enumerate(arts):
		result_df = pd.DataFrame()
		result_df["Datum von"] = datum_von
		result_df["Datum bis"] = datum_bis
		result_df[art] = result_arr[:, i]
		result[art] = Datenreihe(art, result_df)
	
	return result


def apply_stack_model_to_ausbaupfad(
	ausbaupfad: Ausbaupfad,
	smard: Smard,
	verbrauch_art: VerbraucherArt = VerbraucherArt.Netzlast,
) -> Dict[ErzeugerArt, Datenreihe]:
	"""
	Wendet den Stack-Modell-Algorithmus auf einen Ausbaupfad an.

	Verwendet die Prognose-Zeitreihen aus dem Ausbaupfad (installiert × normiert)
	als maximal verfügbare Erzeugung je Zeitschritt und konvertiert diese in
	realisierte Erzeugung unter Berücksichtigung des Verbrauchs und der Regulierungsfähigkeit.

	Args:
		ausbaupfad: Der Ausbaupfad mit Prognose-Datenreihen
		smard: SMARD-Objekt für Regulation-Werte
		verbrauch_art: Art des Verbrauchers (Standard: Netzlast)

	Returns:
		Dictionary mit realisierten Erzeugungen je ErzeugerArt
	"""
	# Schritt 1: Maximal verfügbare Erzeugung aus Prognose-Zeitreihen extrahieren
	max_available_datenreihen = {}
	
	for datenreihe in ausbaupfad.prognose_datenreihen:
		art = datenreihe.art
		df = datenreihe.df[["Datum von", "Datum bis", art]].copy()
		max_available_datenreihen[art] = Datenreihe(art, df)
	
	# Schritt 2: Hole Verbrauch-Datenreihe
	verbrauch_datenreihe = None
	if ausbaupfad.prognose_verbraucher_datenreihen:
		for dr in ausbaupfad.prognose_verbraucher_datenreihen:
			if dr.art == verbrauch_art:
				verbrauch_datenreihe = dr
				break
		
		if verbrauch_datenreihe is None and ausbaupfad.prognose_verbraucher_datenreihen:
			verbrauch_datenreihe = ausbaupfad.prognose_verbraucher_datenreihen[0]
	
	if verbrauch_datenreihe is None:
		verbrauch_datenreihe = smard.get_verbraucher(verbrauch_art)
	
	# Schritt 3: Hole vorherige realisierte Werte aus SMARD
	previous_realisiert = {}
	for art in max_available_datenreihen.keys():
		erzeuger = smard.get_erzeuger(art)
		previous_realisiert[art] = erzeuger.realisiert
	
	# Schritt 4: Wende Stack-Modell-Algorithmus an
	realisiert_datenreihen = calculate_realized_generation(
		max_available_datenreihen=max_available_datenreihen,
		verbrauch_datenreihe=verbrauch_datenreihe,
		smard=smard,
		previous_realisiert=previous_realisiert,
	)
	
	return realisiert_datenreihen
