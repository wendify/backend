"""
Ausbaupfad - Prognose für Erzeuger und Verbraucher

Dieses Modul berechnet Prognosen für die Stromerzeugung und den Stromverbrauch
basierend auf Datenpunkten, die Zielwerte für die Zukunft definieren.

Die Grundidee:
- Wir haben historische Daten (z.B. wie viel Strom wurde mit Wind erzeugt)
- Wir haben Ziel-Datenpunkte (z.B. "Im Jahr 2030 sollen 100 GW Wind installiert sein")
- Wir interpolieren linear zwischen heute und den Zielwerten
- Wir berechnen die Prognose: Normiertes Profil * Installierte Leistung
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd

import config
from core.datenreihe import Datenreihe
from core.prognose.datenpunkt import ErzeugerDatenpunkt, VerbraucherDatenpunkt
from core.setup.smard import Smard
from core.types import ErzeugerArt

# =============================================================================
# VALIDIERUNG
# =============================================================================


def validate_datenpunkte(datenpunkte: list[ErzeugerDatenpunkt]) -> bool:
	"""
	Prüft, ob die Datenpunkte-Liste gültig ist.

	Args:
		datenpunkte: Liste von ErzeugerDatenpunkt-Objekten

	Returns:
		True wenn gültig

	Raises:
		ValueError: Wenn die Liste ungültig ist
	"""
	# Prüfe: Ist es überhaupt eine Liste?
	if not isinstance(datenpunkte, list):
		raise ValueError("Datenpunkte ist keine Liste")

	# Prüfe: Sind alle Einträge ErzeugerDatenpunkt?
	for punkt in datenpunkte:
		if not isinstance(punkt, ErzeugerDatenpunkt):
			raise ValueError("Mindestens ein Eintrag ist kein ErzeugerDatenpunkt")

	return True


# =============================================================================
# HILFSFUNKTIONEN FÜR ZEITRASTER
# =============================================================================


def get_time_step_from_dataframe(df: pd.DataFrame) -> timedelta:
	"""
	Ermittelt die Zeitauflösung (z.B. 15 Minuten) aus einem DataFrame.

	Warum: Wir wollen die Prognose auf dem gleichen Zeitraster wie die
	historischen SMARD-Daten berechnen.

	Args:
		df: DataFrame mit "Datum von" Spalte

	Returns:
		timedelta: Der Zeitabstand zwischen zwei Zeilen (z.B. 15 Minuten)
	"""
	# Brauchen mindestens 2 Zeilen um den Abstand zu berechnen
	if len(df) >= 2:
		first_time = df["Datum von"].iloc[0]
		second_time = df["Datum von"].iloc[1]
		time_step = second_time - first_time
		return time_step

	# Fallback: 15 Minuten wenn nicht genug Daten
	return timedelta(minutes=15)


def create_time_grid(
	start_time: datetime, end_time: datetime, time_step: timedelta
) -> pd.DataFrame:
	"""
	Erstellt ein durchgehendes Zeitraster von start_time bis end_time.

	Beispiel: Bei 15-Minuten-Schritten von 00:00 bis 01:00:
	- Datum von: 00:00, 00:15, 00:30, 00:45
	- Datum bis: 00:15, 00:30, 00:45, 01:00

	Args:
		start_time: Startzeit des Rasters
		end_time: Endzeit des Rasters
		time_step: Zeitschritt (z.B. 15 Minuten)

	Returns:
		DataFrame mit "Datum von" und "Datum bis" Spalten
	"""
	# Erzeuge alle "Datum von" Zeitpunkte
	# end_time - time_step weil der letzte Eintrag bei end_time endet, nicht startet
	all_start_times = pd.date_range(start=start_time, end=end_time - time_step, freq=time_step)

	# Baue das DataFrame
	grid = pd.DataFrame()
	grid["Datum von"] = all_start_times
	grid["Datum bis"] = all_start_times + time_step

	return grid


# =============================================================================
# INTERPOLATION FÜR ZIELPFADE
# =============================================================================


def interpolate_target_values(
	times: pd.Series,
	baseline_time: datetime,
	baseline_value: float,
	target_points: list,  # ErzeugerDatenpunkt oder VerbraucherDatenpunkt
	value_getter,  # Funktion um den Wert aus einem Datenpunkt zu holen
) -> pd.Series:
	"""
	Interpoliert Zielwerte linear über die Zeit.

	Beispiel:
	- Baseline (heute): 50 GW installiert am 01.01.2024
	- Ziel: 100 GW am 01.01.2030
	- Ergebnis: Lineare Steigerung von 50 auf 100 GW

	Diese Funktion funktioniert für Erzeuger (installiert) und Verbraucher (verbraucht).

	Args:
		times: Zeitpunkte für die wir Werte berechnen wollen
		baseline_time: Zeitpunkt des Ausgangswerts
		baseline_value: Ausgangswert (z.B. heute installierte Leistung)
		target_points: Liste von Datenpunkten mit Zielwerten
		value_getter: Funktion die den Wert aus einem Datenpunkt extrahiert

	Returns:
		pd.Series mit interpolierten Werten für jeden Zeitpunkt
	"""
	# Schritt 1: Sammle alle Kontrollpunkte (Baseline + Ziele)
	control_times = [baseline_time]
	control_values = [float(baseline_value)]

	for point in target_points:
		control_times.append(point.datetime)
		control_values.append(float(value_getter(point)))

	# Schritt 2: Erstelle eine Series aus den Kontrollpunkten
	control_series = pd.Series(control_values, index=pd.to_datetime(control_times))
	control_series = control_series.sort_index()

	# Schritt 3: Erstelle einen Index der alle Zeitpunkte enthält
	target_index = pd.DatetimeIndex(pd.to_datetime(times))
	combined_index = target_index.union(control_series.index)

	# Schritt 4: Interpoliere linear über die Zeit
	# - Erst auf den kombinierten Index bringen
	# - Dann interpolieren
	# - Dann auf den Ziel-Index beschränken
	series_on_combined = control_series.reindex(combined_index)
	series_sorted = series_on_combined.sort_index()
	series_interpolated = series_sorted.interpolate(method="time")
	series_on_target = series_interpolated.reindex(target_index)

	# Schritt 5: Fülle Lücken am Rand
	# ffill = Forward Fill (letzter bekannter Wert nach vorne)
	# bfill = Backward Fill (nächster bekannter Wert nach hinten)
	series_filled = series_on_target.ffill().bfill()

	return series_filled


# =============================================================================
# NORMIERTES PROFIL (ENorm / VNorm)
# =============================================================================


def create_normalized_profile(
	base_df: pd.DataFrame,
	column_name: str,
	target_times: pd.Series,
	normalization_value: float,
	extrapolation_mode: str,
) -> pd.Series:
	"""
	Erstellt ein normiertes Profil für die Prognose.

	Was ist ein normiertes Profil?
	- Normierter Wert = Ist-Wert / Normierungswert
	- Bei Erzeugern: Erzeugung / Installierte Leistung
	- Bei Verbrauchern: Verbrauch / Mittelwert(Verbrauch)

	Das Profil zeigt die typische "Form" (z.B. Solaranlage mittags mehr als nachts).

	Extrapolationsmodi für die Zukunft:
	- "last": Letzter bekannter Wert wird fortgeschrieben
	- "daily": Tagesprofil (Mittelwert je Uhrzeit über alle Tage)
	- "yearly": Jahresprofil (Mittelwert je Tag-im-Jahr und Uhrzeit)

	Args:
		base_df: Historische Daten mit "Datum von" Spalte
		column_name: Name der Werte-Spalte
		target_times: Zeitpunkte für die wir das Profil brauchen
		normalization_value: Wert durch den geteilt wird (z.B. installierte Leistung)
		extrapolation_mode: "last", "daily" oder "yearly"

	Returns:
		pd.Series mit normierten Werten für jeden Zeitpunkt
	"""
	# Schritt 1: Hole die Werte und normiere sie
	base_series = base_df.set_index("Datum von")[column_name]

	# Vermeide Division durch 0
	if normalization_value == 0:
		normalization_value = 1.0

	normalized_base = base_series / normalization_value

	# Schritt 2: Stelle sicher, dass der Index eindeutig ist
	if normalized_base.index.has_duplicates:
		# Bei Duplikaten: Mittelwert nehmen
		normalized_base = normalized_base.groupby(level=0).mean()

	normalized_base = normalized_base.sort_index()

	# Schritt 3: Auf die Zielzeiten abbilden
	# method="ffill" = Forward Fill für Zeitpunkte die nicht exakt passen
	result_series = normalized_base.reindex(target_times, method="ffill")

	# Schritt 4: Finde den letzten bekannten Zeitpunkt
	last_known_time = base_df["Datum von"].iloc[-1]

	# Schritt 5: Finde alle Zeitpunkte die in der Zukunft liegen
	future_mask = result_series.index > last_known_time
	future_times = result_series.index[future_mask]

	# Wenn keine Zukunftswerte nötig oder Modus "last": fertig
	if len(future_times) == 0:
		return result_series

	if extrapolation_mode == "last":
		# Bei "last" bleiben die ffill-Werte stehen
		return result_series

	# Schritt 6: Extrapoliere die Zukunftswerte
	if extrapolation_mode == "daily":
		# Berechne Durchschnittswerte für jede Uhrzeit
		result_series = _extrapolate_with_daily_profile(
			result_series, normalized_base, future_times
		)

	elif extrapolation_mode == "yearly":
		# Berechne Durchschnittswerte für jeden Tag-im-Jahr + Uhrzeit
		result_series = _extrapolate_with_yearly_profile(
			result_series, normalized_base, future_times
		)

	return result_series


def _extrapolate_with_daily_profile(
	result_series: pd.Series,
	normalized_base: pd.Series,
	future_times: pd.DatetimeIndex,
) -> pd.Series:
	"""
	Füllt Zukunftswerte mit dem Tagesprofil.

	Das Tagesprofil ist der Mittelwert für jede Uhrzeit über alle Tage.
	Beispiel: Mittags ist immer mehr Solar-Erzeugung als nachts.
	"""

	# Berechne Mittelwert für jede Uhrzeit
	def get_time_of_day(timestamp):
		return timestamp.time()

	daily_profile = normalized_base.groupby(normalized_base.index.map(get_time_of_day)).mean()

	# Setze die Werte für jeden Zukunfts-Zeitpunkt
	future_values = []
	for timestamp in future_times:
		time_of_day = timestamp.time()
		profile_value = daily_profile.get(time_of_day, 1.0)
		future_values.append(float(profile_value))

	result_series.loc[future_times] = future_values
	return result_series


def _extrapolate_with_yearly_profile(
	result_series: pd.Series,
	normalized_base: pd.Series,
	future_times: pd.DatetimeIndex,
) -> pd.Series:
	"""
	Füllt Zukunftswerte mit dem Jahresprofil.

	Das Jahresprofil berücksichtigt sowohl den Tag-im-Jahr als auch die Uhrzeit.
	Beispiel: Im Juli mittags mehr Solar als im Dezember mittags.
	"""

	# Schlüssel: (Tag-im-Jahr, Uhrzeit)
	def get_day_and_time(timestamp):
		day_of_year = timestamp.timetuple().tm_yday
		time_of_day = timestamp.time()
		return (day_of_year, time_of_day)

	# Berechne Mittelwert für jede (Tag-im-Jahr, Uhrzeit) Kombination
	yearly_profile = normalized_base.groupby(normalized_base.index.map(get_day_and_time)).mean()

	# Fallback: Nur Tagesprofil wenn keine Jahres-Daten vorhanden
	def get_time_of_day(timestamp):
		return timestamp.time()

	daily_profile = normalized_base.groupby(normalized_base.index.map(get_time_of_day)).mean()

	# Setze die Werte für jeden Zukunfts-Zeitpunkt
	future_values = []
	for timestamp in future_times:
		key = get_day_and_time(timestamp)

		if key in yearly_profile.index:
			# Jahresprofil hat einen Wert für diesen Tag und diese Uhrzeit
			value = float(yearly_profile[key])
		else:
			# Fallback: Nur Tagesprofil verwenden
			time_of_day = timestamp.time()
			value = float(daily_profile.get(time_of_day, 1.0))

		future_values.append(value)

	result_series.loc[future_times] = future_values
	return result_series


# =============================================================================
# HEUTIGE WERTE MIT ZUKUNFTS-FORTSETZUNG
# =============================================================================


def create_baseline_series(
	base_df: pd.DataFrame,
	column_name: str,
	target_times: pd.Series,
	normalized_profile: pd.Series,
	baseline_value: float,
) -> pd.Series:
	"""
	Erstellt eine Zeitreihe der Ist-Werte mit Fortsetzung in die Zukunft.

	Für die Vergangenheit: Echte historische Werte
	Für die Zukunft: Normiertes Profil * Baseline-Wert

	Args:
		base_df: Historische Daten
		column_name: Name der Werte-Spalte
		target_times: Alle Zeitpunkte für die wir Werte brauchen
		normalized_profile: Das normierte Profil für die Zukunft
		baseline_value: Der Ausgangswert (z.B. installierte Leistung)

	Returns:
		pd.Series mit Werten für alle Zeitpunkte
	"""
	# Schritt 1: Hole die historischen Werte
	historical_series = base_df.set_index("Datum von")[column_name]

	# Schritt 2: Stelle eindeutigen Index sicher
	if historical_series.index.has_duplicates:
		historical_series = historical_series.groupby(level=0).mean()
	historical_series = historical_series.sort_index()

	# Schritt 3: Auf Zielzeiten abbilden
	result_series = historical_series.reindex(target_times, method="ffill")

	# Schritt 4: Finde den letzten historischen Zeitpunkt
	last_historical_time = historical_series.index[-1]

	# Schritt 5: Setze Zukunftswerte = Profil * Baseline
	future_mask = result_series.index > last_historical_time
	future_times = result_series.index[future_mask]

	if len(future_times) > 0:
		future_values = normalized_profile.loc[future_times] * baseline_value
		result_series.loc[future_times] = future_values

	return result_series


# =============================================================================
# PROGNOSE-BERECHNUNG
# =============================================================================


def calculate_prognosis(
	baseline_series: pd.Series,
	target_values_series: pd.Series,
	normalized_profile: pd.Series,
	baseline_value: float,
) -> pd.Series:
	"""
	Berechnet die finale Prognose.

	Die Formel:
	Prognose = Heute + (Ziel - Baseline) * Profil

	Wobei:
	- Heute = Die aktuellen/historischen Werte
	- Ziel = Interpolierter Zielwert (z.B. installierte Leistung)
	- Baseline = Der Ausgangswert von heute
	- Profil = Das normierte Profil

	Beispiel für Solar:
	- Heute: 50 GW installiert, erzeugt 20 GW
	- Ziel 2030: 100 GW installiert
	- Delta: 50 GW mehr
	- Prognose mittags: 20 GW + 50 GW * 0.8 (Profil) = 60 GW

	Args:
		baseline_series: Heutige/historische Werte
		target_values_series: Interpolierte Zielwerte
		normalized_profile: Normiertes Profil
		baseline_value: Ausgangswert von heute

	Returns:
		pd.Series mit der Prognose
	"""
	# Schritt 1: Berechne das Delta (Unterschied zum Ausgangswert)
	delta_series = target_values_series - baseline_value

	# Schritt 2: Berechne die zusätzliche Erzeugung/Verbrauch
	additional_values = delta_series * normalized_profile

	# Schritt 3: Addiere zur Basis
	prognosis = baseline_series + additional_values

	return prognosis


# =============================================================================
# ERZEUGER: ERGÄNZE FEHLENDE ARTEN
# =============================================================================


def ergaenze_erzeuger_datenpunkte(
	datenpunkte: list[ErzeugerDatenpunkt],
	smard: Smard,
) -> list[ErzeugerDatenpunkt]:
	"""
	Ergänzt Datenpunkte für Erzeuger-Arten die keine Datenpunkte haben.

	Wenn z.B. nur Solar-Datenpunkte übergeben wurden, werden für alle
	anderen Arten (Wind, Kohle, etc.) automatisch Datenpunkte erstellt,
	die den aktuellen Ist-Stand fortschreiben.

	Args:
		datenpunkte: Vorhandene Datenpunkte
		smard: SMARD-Datenobjekt

	Returns:
		Ergänzte Liste von Datenpunkten
	"""
	# Bei leerer Liste: nichts zu tun
	if not datenpunkte:
		return datenpunkte

	# Schritt 1: Finde welche Arten bereits Datenpunkte haben
	existing_types = set()
	for punkt in datenpunkte:
		existing_types.add(punkt.art)

	# Schritt 2: Finde alle möglichen Arten
	all_types = set(ErzeugerArt)

	# Schritt 3: Finde fehlende Arten
	missing_types = all_types - existing_types

	# Schritt 4: Finde das späteste Datum in den vorhandenen Datenpunkten
	latest_datetime = datetime.min
	for punkt in datenpunkte:
		if punkt.datetime > latest_datetime:
			latest_datetime = punkt.datetime

	# Schritt 5: Ergänze Datenpunkte für fehlende Arten
	if missing_types:
		if smard is None:
			raise ValueError(f"Fehlende ErzeugerArten: {missing_types} – kein smard übergeben")

		for art in missing_types:
			# Hole den aktuellen Wert aus SMARD
			erzeuger = smard.get_erzeuger(art)
			installiert_df = erzeuger.installiert.df

			# Letzter bekannter Wert
			last_row = installiert_df.iloc[-1]
			last_installiert = float(last_row[art])

			# Erstelle neuen Datenpunkt
			new_punkt = ErzeugerDatenpunkt(
				art=art,
				datetime=latest_datetime,
				installiert=last_installiert,
			)
			datenpunkte.append(new_punkt)

	# Schritt 6: Ergänze auch vorhandene Arten bis zum spätesten Datum
	# (falls ein Erzeuger früher endet als andere)
	for art in existing_types:
		# Finde alle Datenpunkte dieser Art
		punkte_dieser_art = [p for p in datenpunkte if p.art == art]

		# Sortiere nach Datum
		punkte_dieser_art.sort(key=lambda p: p.datetime)

		# Finde den letzten Datenpunkt dieser Art
		last_punkt = punkte_dieser_art[-1]

		# Wenn er vor dem spätesten Datum endet, ergänze
		if last_punkt.datetime < latest_datetime:
			new_punkt = ErzeugerDatenpunkt(
				art=art,
				datetime=latest_datetime,
				installiert=last_punkt.installiert,
			)
			datenpunkte.append(new_punkt)

	return datenpunkte


# =============================================================================
# HAUPTFUNKTION: ERZEUGER-PROGNOSE
# =============================================================================


def create_prognose_datenreihen(
	datenpunkte: list[ErzeugerDatenpunkt],
	smard: Smard,
) -> list[Datenreihe]:
	"""
	Erzeugt Prognose-Datenreihen für alle Erzeuger-Arten.

	Der Rechenweg:
	1. Datenpunkte nach Erzeuger-Art gruppieren
	2. Für jede Art: Zielwerte linear interpolieren
	3. Delta zur heutigen installierten Leistung berechnen
	4. Delta mit normiertem Profil multiplizieren
	5. Mit heutiger Erzeugung addieren = Prognose

	Args:
		datenpunkte: Liste von ErzeugerDatenpunkt
		smard: SMARD-Datenobjekt

	Returns:
		Liste von Datenreihe-Objekten mit der Prognose je Art
	"""
	# Bei leerer Liste: nichts zu tun
	if not datenpunkte:
		return []

	if smard is None:
		raise ValueError("Smard darf nicht None sein")

	# Schritt 1: Gruppiere Datenpunkte nach Art
	grouped_points = defaultdict(list)
	for punkt in datenpunkte:
		grouped_points[punkt.art].append(punkt)

	# Schritt 2: Erstelle Prognose für jede Erzeuger-Art
	result = []

	for art in ErzeugerArt:
		# Hole die Datenpunkte für diese Art (sortiert nach Datum)
		points_for_this_type = grouped_points.get(art, [])
		points_for_this_type.sort(key=lambda p: p.datetime)

		# Hole die historischen Daten aus SMARD
		erzeuger = smard.get_erzeuger(art)
		normalized_df = erzeuger.normiert.df.copy()
		realized_df = erzeuger.realisiert.df.copy()
		installed_df = erzeuger.installiert.df.copy()

		# Hole Baseline-Werte (letzter bekannter Stand)
		baseline_time = installed_df["Datum von"].iloc[-1]
		baseline_installed = float(installed_df[art].iloc[-1])

		# Bestimme den Zeithorizont (bis zum letzten Datenpunkt oder Ende der Daten)
		if len(points_for_this_type) > 0:
			last_target_time = points_for_this_type[-1].datetime
		else:
			last_target_time = normalized_df["Datum bis"].iloc[-1]

		end_of_data = normalized_df["Datum bis"].iloc[-1]
		horizon_end = max(last_target_time, end_of_data)

		# Erstelle das Zeitraster
		start_time = normalized_df["Datum von"].iloc[0]
		time_step = get_time_step_from_dataframe(normalized_df)
		time_grid = create_time_grid(start_time, horizon_end, time_step)

		# Hole den Extrapolationsmodus aus der Config
		extrapolation_mode = getattr(config, "ENORM_EXTRAPOLATION_MODE", "daily")

		# Interpoliere die Zielwerte (installierte Leistung)
		target_installed_series = interpolate_target_values(
			times=time_grid["Datum von"],
			baseline_time=baseline_time,
			baseline_value=baseline_installed,
			target_points=points_for_this_type,
			value_getter=lambda p: p.installiert,
		)

		# Unterscheide zwischen Erneuerbaren (regulation = 0) und Regelbaren (regulation > 0)
		if erzeuger.regulation == 0.0:
			# Erneuerbare: Verwende normiertes Profil (ENorm)
			# (Erzeugung abhängig von Wetter/Tageszeit)
			normalized_profile = create_normalized_profile(
				base_df=normalized_df,
				column_name=art,
				target_times=time_grid["Datum von"],
				normalization_value=1.0,  # Bereits normiert
				extrapolation_mode=extrapolation_mode,
			)

			# Erstelle die Basis-Zeitreihe (heutige Werte + Zukunft = Profil * Baseline)
			baseline_series = create_baseline_series(
				base_df=realized_df,
				column_name=art,
				target_times=time_grid["Datum von"],
				normalized_profile=normalized_profile,
				baseline_value=baseline_installed,
			)

			# Berechne die finale Prognose mit Profil
			prognosis_series = calculate_prognosis(
				baseline_series=baseline_series,
				target_values_series=target_installed_series,
				normalized_profile=normalized_profile,
				baseline_value=baseline_installed,
			)
		else:
			# Regelbare Erzeuger: Verwende installierte Leistung direkt
			# (Keine Profil-Anwendung, da Stack-Modell die Regelung übernimmt)
			prognosis_series = target_installed_series

		# Erstelle das Ergebnis-DataFrame
		result_df = pd.DataFrame()
		result_df["Datum von"] = time_grid["Datum von"]
		result_df["Datum bis"] = time_grid["Datum bis"]
		result_df[art] = prognosis_series.values

		# Füge zur Ergebnisliste hinzu
		result.append(Datenreihe(art, result_df))

	return result


# =============================================================================
# HAUPTFUNKTION: VERBRAUCHER-PROGNOSE
# =============================================================================


def create_prognose_verbraucher_datenreihen(
	datenpunkte: list[VerbraucherDatenpunkt],
	smard: Smard,
) -> list[Datenreihe]:
	"""
	Erzeugt Prognose-Datenreihen für Verbraucher-Arten.

	Der Rechenweg ist analog zu Erzeugern:
	1. Datenpunkte nach Verbraucher-Art gruppieren
	2. Für jede Art: Zielwerte linear interpolieren
	3. Delta zum heutigen mittleren Verbrauch berechnen
	4. Delta mit normiertem Profil multiplizieren
	5. Mit heutigem Verbrauch addieren = Prognose

	WICHTIG: Nur Arten mit expliziten Datenpunkten werden verarbeitet!

	Args:
		datenpunkte: Liste von VerbraucherDatenpunkt
		smard: SMARD-Datenobjekt

	Returns:
		Liste von Datenreihe-Objekten mit der Prognose je Art
	"""
	# Bei leerer Liste: nichts zu tun
	if not datenpunkte:
		return []

	if smard is None:
		raise ValueError("Smard darf nicht None sein")

	# Schritt 1: Gruppiere Datenpunkte nach Art
	grouped_points = defaultdict(list)
	for punkt in datenpunkte:
		grouped_points[punkt.art].append(punkt)

	# Schritt 2: Erstelle Prognose nur für Arten mit Datenpunkten
	result = []

	for art in grouped_points.keys():
		# Hole die Datenpunkte für diese Art (sortiert nach Datum)
		points_for_this_type = grouped_points[art]
		points_for_this_type.sort(key=lambda p: p.datetime)

		# Hole die historischen Daten aus SMARD
		verbraucher = smard.get_verbraucher(art)
		consumption_df = verbraucher.df.copy()

		# Hole Baseline-Werte
		baseline_time = consumption_df["Datum von"].iloc[-1]
		# Für Verbraucher: Mittelwert als Baseline (anders als bei Erzeugern)
		baseline_consumption = float(consumption_df[art].mean())
		if baseline_consumption == 0:
			baseline_consumption = 1.0

		# Bestimme den Zeithorizont
		if len(points_for_this_type) > 0:
			last_target_time = points_for_this_type[-1].datetime
		else:
			last_target_time = consumption_df["Datum bis"].iloc[-1]

		end_of_data = consumption_df["Datum bis"].iloc[-1]
		horizon_end = max(last_target_time, end_of_data)

		# Erstelle das Zeitraster
		start_time = consumption_df["Datum von"].iloc[0]
		time_step = get_time_step_from_dataframe(consumption_df)
		time_grid = create_time_grid(start_time, horizon_end, time_step)

		# Hole den Extrapolationsmodus aus der Config
		extrapolation_mode = getattr(config, "ENORM_EXTRAPOLATION_MODE", "yearly")

		# Erstelle das normierte Profil (VNorm)
		# Für Verbraucher: Verbrauch / Mittelwert(Verbrauch)
		normalized_profile = create_normalized_profile(
			base_df=consumption_df,
			column_name=art,
			target_times=time_grid["Datum von"],
			normalization_value=baseline_consumption,
			extrapolation_mode=extrapolation_mode,
		)

		# Erstelle die Basis-Zeitreihe (heutige Werte + Zukunft = Profil * Baseline)
		baseline_series = create_baseline_series(
			base_df=consumption_df,
			column_name=art,
			target_times=time_grid["Datum von"],
			normalized_profile=normalized_profile,
			baseline_value=baseline_consumption,
		)

		# Interpoliere die Zielwerte (Verbrauchswert)
		target_consumption_series = interpolate_target_values(
			times=time_grid["Datum von"],
			baseline_time=baseline_time,
			baseline_value=baseline_consumption,
			target_points=points_for_this_type,
			value_getter=lambda p: p.verbraucht,
		)

		# Berechne die finale Prognose
		prognosis_series = calculate_prognosis(
			baseline_series=baseline_series,
			target_values_series=target_consumption_series,
			normalized_profile=normalized_profile,
			baseline_value=baseline_consumption,
		)

		# Erstelle das Ergebnis-DataFrame
		result_df = pd.DataFrame()
		result_df["Datum von"] = time_grid["Datum von"]
		result_df["Datum bis"] = time_grid["Datum bis"]
		result_df[art] = prognosis_series.values

		# Füge zur Ergebnisliste hinzu
		result.append(Datenreihe(art, result_df))

	return result


# =============================================================================
# HAUPTKLASSE: AUSBAUPFAD
# =============================================================================


class Ausbaupfad:
	"""
	Verwaltet den Ausbaupfad für Erzeuger und Verbraucher.

	Ein Ausbaupfad beschreibt, wie sich die installierte Leistung (bei Erzeugern)
	bzw. der Verbrauch (bei Verbrauchern) über die Zeit entwickeln soll.

	Beispiel:
	- Heute: 50 GW Photovoltaik installiert
	- 2030: 100 GW Photovoltaik geplant
	- Der Ausbaupfad interpoliert dazwischen und berechnet die Prognose
	"""

	def __init__(
		self,
		erzeuger_datenpunkte: list[ErzeugerDatenpunkt],
		verbraucher_datenpunkte: list[VerbraucherDatenpunkt],
		smard: Smard | None = None,
	) -> None:
		"""
		Initialisiert den Ausbaupfad.

		Args:
			erzeuger_datenpunkte: Liste von Ziel-Datenpunkten für Erzeuger
			verbraucher_datenpunkte: Liste von Ziel-Datenpunkten für Verbraucher
			smard: SMARD-Datenobjekt mit historischen Daten
		"""
		# Validiere die Eingabe
		if not validate_datenpunkte(erzeuger_datenpunkte):
			logging.error("Validierung fehlgeschlagen!")
			raise ValueError("Validierung fehlgeschlagen!")

		# Ergänze fehlende Erzeuger-Arten
		self.datenpunkte = ergaenze_erzeuger_datenpunkte(erzeuger_datenpunkte, smard)

		# Speichere Verbraucher-Datenpunkte
		self.verbraucher_datenpunkte = verbraucher_datenpunkte

		# Erstelle Prognose-Datenreihen für Erzeuger
		self.prognose_datenreihen: list[Datenreihe] = create_prognose_datenreihen(
			self.datenpunkte,
			smard,
		)

		# Erstelle Prognose-Datenreihen für Verbraucher
		self.prognose_verbraucher_datenreihen: list[Datenreihe] = (
			create_prognose_verbraucher_datenreihen(
				self.verbraucher_datenpunkte,
				smard,
			)
		)

	def get_erzeuger(self, art: ErzeugerArt) -> list[ErzeugerDatenpunkt]:
		"""
		Gibt die Eingabe-Datenpunkte für eine Erzeuger-Art zurück.

		Nützlich um z.B. im UI die eingegebenen Zielwerte anzuzeigen.

		Args:
			art: Die gewünschte Erzeuger-Art

		Returns:
			Liste der Datenpunkte für diese Art
		"""
		result = []
		for punkt in self.datenpunkte:
			if punkt.art == art:
				result.append(punkt)
		return result
