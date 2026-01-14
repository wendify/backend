import logging
from collections import defaultdict
from datetime import datetime, timedelta

import pandas
from pandas import DataFrame, DatetimeIndex, Series

from core.prognose.types import Ereignis, Installation, Verbrauch
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard
from core.setup.verbraucher import VerbraucherArt


# Ermittelt die Zeitauflösung (z.B. 15 Minuten) aus einem DataFrame
def get_time_step_from_dataframe(df: DataFrame) -> timedelta:
	# Brauchen mindestens 2 Zeilen um den Abstand zu berechnen
	if len(df) >= 2:
		first_time = df["Datum von"].iloc[0]
		second_time = df["Datum von"].iloc[1]
		time_step = second_time - first_time
		return time_step

	# Fallback: 15 Minuten wenn nicht genug Daten
	return timedelta(minutes=15)


# Erstellt ein durchgehendes Zeitraster von start_time bis end_time
def create_time_grid(start_time: datetime, end_time: datetime, time_step: timedelta) -> DataFrame:
	# Erzeuge alle "Datum von" Zeitpunkte
	# end_time - time_step weil der letzte Eintrag bei end_time endet, nicht startet
	all_start_times = pandas.date_range(start=start_time, end=end_time - time_step, freq=time_step)

	# Baue das DataFrame
	grid = DataFrame()
	grid["Datum von"] = all_start_times
	grid["Datum bis"] = all_start_times + time_step

	return grid


# Interpoliert Zielwerte linear über die Zeit
def interpolate_target_values(
	times: Series,
	baseline_time: datetime,
	baseline_value: float,
	target_points: list[Installation | Verbrauch],
) -> Series:
	# Schritt 1: Sammle alle Kontrollpunkte (Baseline + Ziele)
	control_times = [baseline_time]
	control_values = [float(baseline_value)]

	for point in target_points:
		control_times.append(point.datum)
		control_values.append(point.wert)

	# Schritt 2: Erstelle eine Series aus den Kontrollpunkten
	control_series = Series(control_values, index=pandas.to_datetime(control_times))
	control_series = control_series.sort_index()

	# Schritt 3: Erstelle einen Index der alle Zeitpunkte enthält
	target_index = DatetimeIndex(pandas.to_datetime(times))
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
	series_filled = series_on_target.ffill().bfill()

	return series_filled


# Erstellt ein normiertes Profil für die Prognose
def create_normalized_profile(
	base_df: DataFrame,
	column_name: str,
	target_times: Series,
	normalization_value: float,
) -> Series:
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


# Erstellt eine Zeitreihe der Ist-Werte mit Fortsetzung in die Zukunft
def create_baseline_series(
	base_df: DataFrame,
	column_name: str,
	target_times: Series,
	normalized_profile: Series,
	baseline_value: float,
) -> Series:
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


# Berechnet die finale Prognose
def calculate_prognosis(
	baseline_series: Series,
	target_values_series: Series,
	normalized_profile: Series,
	baseline_value: float,
) -> Series:
	# Schritt 1: Berechne das Delta (Unterschied zum Ausgangswert)
	delta_series = target_values_series - baseline_value

	# Schritt 2: Berechne die zusätzliche Erzeugung/Verbrauch
	additional_values = delta_series * normalized_profile

	# Schritt 3: Addiere zur Basis
	prognosis = baseline_series + additional_values

	return prognosis


# Ergänzt Datenpunkte für Erzeuger-Arten die keine Datenpunkte haben
def ergaenze_erzeuger_datenpunkte(
	datenpunkte: list[Installation],
	smard: Smard,
) -> list[Installation]:
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
		if punkt.datum > latest_datetime:
			latest_datetime = punkt.datum

	# Schritt 5: Ergänze Datenpunkte für fehlende Arten
	if missing_types:
		for art in missing_types:
			# Hole den aktuellen Wert aus SMARD
			erzeuger = smard.get_erzeuger(art)
			installiert_df = erzeuger.installiert.df

			# Letzter bekannter Wert
			last_row = installiert_df.iloc[-1]
			last_installiert = float(last_row[art])

			# Erstelle neuen Datenpunkt
			new_punkt = Installation(latest_datetime, art, last_installiert)
			datenpunkte.append(new_punkt)

	# Schritt 6: Ergänze auch vorhandene Arten bis zum spätesten Datum
	for art in existing_types:
		# Finde alle Datenpunkte dieser Art
		punkte_dieser_art = [p for p in datenpunkte if p.art == art]

		# Sortiere nach Datum
		punkte_dieser_art.sort(key=lambda p: p.datum)

		# Finde den letzten Datenpunkt dieser Art
		last_punkt = punkte_dieser_art[-1]

		# Wenn er vor dem spätesten Datum endet, ergänze
		if last_punkt.datum < latest_datetime:
			new_punkt = Installation(latest_datetime, art, last_punkt.wert)
			datenpunkte.append(new_punkt)

	return datenpunkte


# Erzeugt Prognose-Datenreihen für alle Erzeuger-Arten
def create_prognose_erzeuger(
	datenpunkte: list[Installation],
	smard: Smard,
) -> list[Datenreihe[ErzeugerArt]]:
	# Bei leerer Liste: nichts zu tun
	if not datenpunkte:
		return []

	# Schritt 1: Gruppiere Datenpunkte nach Art
	grouped_points: defaultdict[ErzeugerArt, list[Installation]] = defaultdict(list)
	for punkt in datenpunkte:
		grouped_points[punkt.art].append(punkt)

	# Schritt 2: Erstelle Prognose für jede Erzeuger-Art
	result = []

	for art in ErzeugerArt:
		# Hole die Datenpunkte für diese Art (sortiert nach Datum)
		points_for_this_type = grouped_points.get(art, [])
		points_for_this_type.sort(key=lambda p: p.datum)

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
			last_target_time = points_for_this_type[-1].datum
		else:
			last_target_time = normalized_df["Datum bis"].iloc[-1]

		end_of_data = normalized_df["Datum bis"].iloc[-1]
		horizon_end = max(last_target_time, end_of_data)

		# Erstelle das Zeitraster
		start_time = normalized_df["Datum von"].iloc[0]
		time_step = get_time_step_from_dataframe(normalized_df)
		time_grid = create_time_grid(start_time, horizon_end, time_step)

		# Interpoliere die Zielwerte (installierte Leistung)
		target_installed_series = interpolate_target_values(
			times=time_grid["Datum von"],
			baseline_time=baseline_time,
			baseline_value=baseline_installed,
			target_points=points_for_this_type,
		)

		# Unterscheide zwischen Erneuerbaren (regulation = 0) und Regelbaren (regulation > 0)
		if erzeuger.art.regulierung == 0.0:
			# Erneuerbare: Verwende normiertes Profil (ENorm)
			# (Erzeugung abhängig von Wetter/Tageszeit)
			normalized_profile = create_normalized_profile(
				base_df=normalized_df,
				column_name=art,
				target_times=time_grid["Datum von"],
				normalization_value=1.0,  # Bereits normiert
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
		result_df = DataFrame()
		result_df["Datum von"] = time_grid["Datum von"]
		result_df["Datum bis"] = time_grid["Datum bis"]
		result_df[art] = prognosis_series.values

		# Füge zur Ergebnisliste hinzu
		result.append(Datenreihe(art, result_df))

	return result


# Erzeugt Prognose-Datenreihen für Verbraucher-Arten
def create_prognose_verbraucher(
	datenpunkte: list[Verbrauch],
	smard: Smard,
) -> list[Datenreihe[VerbraucherArt]]:
	# Bei leerer Liste: nichts zu tun
	if not datenpunkte:
		return []

	# Schritt 1: Gruppiere Datenpunkte nach Art
	grouped_points: defaultdict[VerbraucherArt, list[Verbrauch]] = defaultdict(list)
	for punkt in datenpunkte:
		grouped_points[punkt.art].append(punkt)

	# Schritt 2: Erstelle Prognose nur für Arten mit Datenpunkten
	result = []

	for art in grouped_points.keys():
		# Hole die Datenpunkte für diese Art (sortiert nach Datum)
		points_for_this_type = grouped_points[art]
		points_for_this_type.sort(key=lambda p: p.datum)

		# Hole die historischen Daten aus SMARD
		verbraucher = smard.get_verbraucher(art)
		consumption_df = verbraucher.verbraucht.df.copy()

		# Hole Baseline-Werte
		baseline_time = consumption_df["Datum von"].iloc[-1]
		# Für Verbraucher: Mittelwert als Baseline (anders als bei Erzeugern)
		baseline_consumption = float(consumption_df[art].mean())
		if baseline_consumption == 0:
			baseline_consumption = 1.0

		# Bestimme den Zeithorizont
		if len(points_for_this_type) > 0:
			last_target_time = points_for_this_type[-1].datum
		else:
			last_target_time = consumption_df["Datum bis"].iloc[-1]

		end_of_data = consumption_df["Datum bis"].iloc[-1]
		horizon_end = max(last_target_time, end_of_data)

		# Erstelle das Zeitraster
		start_time = consumption_df["Datum von"].iloc[0]
		time_step = get_time_step_from_dataframe(consumption_df)
		time_grid = create_time_grid(start_time, horizon_end, time_step)

		# Erstelle das normierte Profil (VNorm)
		# Für Verbraucher: Verbrauch / Mittelwert(Verbrauch)
		normalized_profile = create_normalized_profile(
			base_df=consumption_df,
			column_name=art,
			target_times=time_grid["Datum von"],
			normalization_value=baseline_consumption,
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
		)

		# Berechne die finale Prognose
		prognosis_series = calculate_prognosis(
			baseline_series=baseline_series,
			target_values_series=target_consumption_series,
			normalized_profile=normalized_profile,
			baseline_value=baseline_consumption,
		)

		# Erstelle das Ergebnis-DataFrame
		result_df = DataFrame()
		result_df["Datum von"] = time_grid["Datum von"]
		result_df["Datum bis"] = time_grid["Datum bis"]
		result_df[art] = prognosis_series.values

		# Füge zur Ergebnisliste hinzu
		result.append(Datenreihe(art, result_df))

	return result


# Ein aus den CSV-Dateien gelesener Ausbaupfad
class Ausbaupfad:
	def __init__(
		self,
		name: str,
		ereignisse: list[Ereignis],
		installiert: list[Installation],
		verbraucht: list[Verbrauch],
	) -> None:
		# Name des Ausbaupfades = Ordnername
		self.name = name

		# Rohe Daten vorerst speichern
		self.ereignisse = ereignisse
		self.installiert = installiert
		self.verbraucht = verbraucht

	# Verarbeitet diesen Ausbaupfad
	def process(self, smard: Smard) -> None:
		logging.info(f"Ausbaupfad wird verarbeitet: {self.name}")

		# Ergänze fehlende Erzeuger-Arten
		self.installiert = ergaenze_erzeuger_datenpunkte(self.installiert, smard)

		# Erstelle Prognose-Datenreihen für Erzeuger
		self.prognose_erzeuger = create_prognose_erzeuger(self.installiert, smard)

		# Erstelle Prognose-Datenreihen für Verbraucher
		self.prognose_verbraucher = create_prognose_verbraucher(self.verbraucht, smard)

	# Holt den Erzeuger mit der angegebenen Art
	def get_erzeuger(self, art: ErzeugerArt) -> list[Installation]:
		return [punkt for punkt in self.installiert if punkt.art == art]
