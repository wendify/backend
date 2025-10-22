import logging
from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd

import config
from core.datenreihe import Datenreihe
from core.prognose.datenpunkt import Datenpunkt
from core.setup.smard import Smard
from core.types import ErzeugerArt


def validate_datenpunkte(datenpunkte: list[Datenpunkt]) -> bool:
	if not isinstance(datenpunkte, list):
		raise ValueError("Datenpunkte ist keine Liste")

	if not all(isinstance(dp, Datenpunkt) for dp in datenpunkte):
		raise ValueError("Mindestens ein Eintrag ist kein Datenpunkt")

	return True


def ergaenze_erzeuger_datenpunkte(datenpunkte: list[Datenpunkt], smard: Smard) -> list[Datenpunkt]:
	vorhandene_arten = {dp.art for dp in datenpunkte}
	erwartete_arten = set(ErzeugerArt)
	fehlende = erwartete_arten - vorhandene_arten

	# max jahr finden in vorhandene Daten
	max_datetime: datetime = datetime.min

	# finde max wert
	for punkt in datenpunkte:
		if punkt.datetime > max_datetime:
			max_datetime = punkt.datetime

	if fehlende:
		if smard is None:
			raise ValueError(f"Fehlende ErzeugerArten: {fehlende} – kein smard übergeben")

		for art in fehlende:
			erzeuger = smard.get_erzeuger(art)
			# 1. Letzter Timestamp im Index
			letzter_zeitpunkt = erzeuger.installiert.df.index[-1]
			letzte_reihe = erzeuger.installiert.df.loc[letzter_zeitpunkt]
			letzter_installierter_wert = letzte_reihe[erzeuger.art]
			neuer_dp = Datenpunkt(
				art, datetime=max_datetime, installiert=float(letzter_installierter_wert)
			)
			datenpunkte.append(neuer_dp)

	return datenpunkte


def _determine_base_frequency(df: pd.DataFrame) -> timedelta:
	"""Ermittelt die Zeitauflösung aus einer bestehenden SMARD-Datenreihe.

	Warum: Wir wollen die Prognose auf dem gleichen Raster wie die SMARD-Daten
	(typisch 15 Minuten) berechnen, um problemlos `ENorm` und `Heute` zu
	kombinieren.
	"""
	if len(df) >= 2:
		return df["Datum von"].iloc[1] - df["Datum von"].iloc[0]
	# Fallback: 15 Minuten, falls nicht genug Zeilen vorhanden sind
	return timedelta(minutes=15)


def _build_time_grid(base_df: pd.DataFrame, end: datetime) -> pd.DataFrame:
	"""Erstellt ein durchgehendes Zeitraster [Datum von, Datum bis) bis `end`.

	Warum: Für die Multiplikation mit `ENorm` und die Addition zu `Heute`
	brauchen wir eine konsistente Timeline, die ggf. über die SMARD-Daten
	hinaus bis zum letzten Datenpunkt verlängert wird.
	"""
	start: datetime = base_df["Datum von"].iloc[0]
	freq: timedelta = _determine_base_frequency(base_df)

	# Erzeuge Liste der "Datum von"-Zeitpunkte
	times = pd.date_range(start=start, end=end - freq, freq=freq)
	grid = pd.DataFrame(
		{
			"Datum von": times,
		}
	)
	grid["Datum bis"] = grid["Datum von"] + freq
	return grid


def _extrapolate_enorm(
	base_df_enorm: pd.DataFrame,
	art: ErzeugerArt,
	target_times: pd.Series,
	mode: str,
) -> pd.Series:
	"""Erzeuge ENorm-Serie auf target_times mit frei wählbarer Extrapolation.

	mode:
	  - 'last': letzter bekannter Wert (ffill)
	  - 'daily': Tagesprofil (Mittelwert je Zeit-des-Tages über Historie)
	  - 'yearly': Jahresprofil (Mittelwert je Tag-des-Jahres und Zeit-des-Tages)
	"""
	base = base_df_enorm.set_index("Datum von")[art]
	# Sicherstellen, dass der Index eindeutig ist (Duplicates mitteln)
	if base.index.has_duplicates:
		base = base.groupby(level=0).mean().sort_index()
	else:
		base = base.sort_index()
	# Erst auf Zielzeiten reindizieren (innerhalb Historie ffill)
	series = base.reindex(target_times, method="ffill")

	last_time = base_df_enorm["Datum von"].iloc[-1]
	future_index = series.index[series.index > last_time]
	if len(future_index) == 0 or mode == "last":
		return series

	if mode == "daily":
		# Mittelwert je Zeit-des-Tages
		time_profile = base.groupby(base.index.map(lambda ts: ts.time())).mean()
		mapped = [float(time_profile.get(ts.time(), 0.0)) for ts in future_index]
		series.loc[future_index] = mapped
		return series

	if mode == "yearly":
		# Mittelwert je (Tag-des-Jahres, Zeit)
		def key(ts):
			return (ts.timetuple().tm_yday, ts.time())

		grouped = base.groupby(base.index.map(key)).mean()
		# Fallback-Profil nur nach Zeit-des-Tages
		time_profile = base.groupby(base.index.map(lambda x: x.time())).mean()

		def lookup(ts) -> float:
			k = (ts.timetuple().tm_yday, ts.time())
			if k in grouped:
				return float(grouped[k])
			# Fallback: nur Zeit-des-Tages
			return float(time_profile.get(ts.time(), 0.0))

		series.loc[future_index] = [lookup(ts) for ts in future_index]
		return series

	# Unbekannter Modus → default: last
	return series


def _ensure_unique_datetime_index(series: pd.Series) -> pd.Series:
	"""Sorgt für eindeutige Zeitindizes, indem Duplikate gemittelt werden."""
	if series.index.has_duplicates:
		return series.groupby(level=0).mean().sort_index()
	return series.sort_index()


def _interpolate_absolute_installiert(
	times: pd.Series,
	baseline_time: datetime,
	baseline_installiert: float,
	dps_sorted: list[Datenpunkt],
) -> pd.Series:
	"""Erzeugt eine Zeitreihe absolut installierter Leistung, vollständig
	vektorisiert mit pandas.

	Warum: Statt pythonischer Schleifen werden die Kontrollpunkte (Baseline
	+ Ziel-Datenpunkte) als Zeitreihe angelegt, auf das Zielraster reindiziert
	und mit `interpolate(method="time")` linear über die Zeit gefüllt. Ränder
	werden per ffill/bfill konstant gehalten.
	"""
	control_times: list[datetime] = [baseline_time] + [dp.datetime for dp in dps_sorted]
	control_values: list[float] = [float(baseline_installiert)] + [
		float(dp.installiert) for dp in dps_sorted
	]

	control = pd.Series(control_values, index=pd.to_datetime(control_times)).sort_index()
	target_index = pd.DatetimeIndex(pd.to_datetime(times))
	union_index = target_index.union(control.index)

	# Interpolation auf vereinheitlichtem Index; anschließend auf das Zielraster zurück
	interpolated = (
		control.reindex(union_index)
		.sort_index()
		.interpolate(method="time")
		.reindex(target_index)
		.ffill()
		.bfill()
	)

	return interpolated


def create_prognose_datenreihen(datenpunkte: list[Datenpunkt], smard: Smard) -> list[Datenreihe]:
	"""Erzeugt finale Prognose-Datenreihen je ErzeugerArt.

	Warum: Dies bündelt den im Plan vorgesehenen Rechenweg:
	1) Datenpunkte gruppieren und zu einer absoluten Ausbau-Zielkurve interpolieren
	2) Delta zur heutigen installierten Leistung bilden
	3) Delta mit `ENorm` multiplizieren (liefert zusätzliche Erzeugung)
	4) Mit heutiger Erzeugung (`Heute`) addieren → Prognose
	"""
	if smard is None:
		raise ValueError("Smard darf nicht None sein")

	# Gruppiere Datenpunkte nach ErzeugerArt
	gruppiert: dict[ErzeugerArt, list[Datenpunkt]] = defaultdict(list)
	for dp in datenpunkte:
		gruppiert[dp.art].append(dp)

	result: list[Datenreihe] = []

	for art in ErzeugerArt:
		dps = gruppiert.get(art, [])
		dps.sort(key=lambda dp: dp.datetime)

		erzeuger = smard.get_erzeuger(art)
		base_df_enorm = erzeuger.normiert.df.copy()
		base_df_heute = erzeuger.realisiert.df.copy()
		base_df_installiert = erzeuger.installiert.df.copy()

		# Basiswerte
		baseline_time: datetime = base_df_installiert["Datum von"].iloc[-1]
		baseline_installiert: float = float(base_df_installiert[art].iloc[-1])

		# Ziel-Horizont: bis zum letzten Datenpunkt, mindestens bis Ende der vorhandenen Daten
		horizon_dp: datetime = (
			dps[-1].datetime if len(dps) > 0 else base_df_enorm["Datum bis"].iloc[-1]
		)
		horizon: datetime = max(horizon_dp, base_df_enorm["Datum bis"].iloc[-1])

		# Einheitliches Zeitraster erzeugen und ENorm/Heute darauf legen
		grid = _build_time_grid(base_df_enorm, end=horizon)
		freq = _determine_base_frequency(base_df_enorm)

		# ENorm auf das Grid abbilden mit konfigurierbarer Extrapolation
		enorm_series = _extrapolate_enorm(
			base_df_enorm=base_df_enorm,
			art=art,
			target_times=grid["Datum von"],
			mode=getattr(config, "ENORM_EXTRAPOLATION_MODE", "daily"),
		)

		# Heute (realisierte Erzeugung) auf das Grid; Zukunft = ENorm * baseline_installiert
		heute_series_base = base_df_heute.set_index("Datum von")[art]
		heute_series_base = _ensure_unique_datetime_index(heute_series_base)
		heute_series = heute_series_base.reindex(grid["Datum von"], method="ffill")
		last_real_time: datetime = heute_series_base.index[-1]
		# Index-basierte Auswahl, damit die Zuordnung exakt auf den Zeitstempeln passiert
		future_index = heute_series.index[heute_series.index > last_real_time]
		# Für Zeiten nach dem letzten Realwert verwenden wir als Basis die
		# typische Lastform ENorm multipliziert mit der Basis-Installationsleistung
		heute_series.loc[future_index] = enorm_series.loc[future_index] * baseline_installiert

		# Interpolation absolute installierte Leistung und Delta zur Basis
		abs_installiert_series = _interpolate_absolute_installiert(
			times=grid["Datum von"],
			baseline_time=baseline_time,
			baseline_installiert=baseline_installiert,
			dps_sorted=dps,
		)
		delta_installiert_series = abs_installiert_series - baseline_installiert

		# Ausbau-Erzeugung = DeltaInstalliert * ENorm
		ausbau_erzeugung_series = delta_installiert_series * enorm_series

		# Finale Prognose = Basis (Heute bzw. ENorm*Baseline) + Ausbau-Erzeugung
		# Dies entspricht ENorm * (BaselineInstalliert + DeltaInstalliert)
		prognose_series = heute_series + ausbau_erzeugung_series

		df = pd.DataFrame(
			{
				"Datum von": grid["Datum von"],
				"Datum bis": grid["Datum bis"],
				art: prognose_series.values,
			}
		)
		result.append(Datenreihe(art, df))

	return result


class Ausbaupfad:
	def __init__(self, datenpunkte: list[Datenpunkt], smard: Smard | None = None):
		if not validate_datenpunkte(datenpunkte):
			logging.error("Validierung fehlgeschlagen!")
			raise ValueError("Validierung fehlgeschlagen!")

		# Ergänze Datenpunkte für fehlende ErzeugerArten (anhand aller Erzeuger aus Smard)
		datenpunkte = ergaenze_erzeuger_datenpunkte(datenpunkte, smard)
		self.datenpunkte = datenpunkte

		# Finale Prognose-Datenreihen je ErzeugerArt erzeugen
		self.prognose_datenreihen: list[Datenreihe] = create_prognose_datenreihen(
			self.datenpunkte, smard
		)
		# Optional: weitere post-Processing-Schritte könnten hier folgen

	def interpolate_datenpunkte(self) -> None:
		"""(Veraltet) Platzhalter der alten Planung. Logik erfolgt nun in
		`create_prognose_datenreihen`. Diese Methode bleibt aus API-Gründen
		bestehen."""

	def get_erzeuger(self, art: ErzeugerArt) -> list[Datenpunkt]:
		"""Gibt die übergebenen Datenpunkte für eine ErzeugerArt zurück.

		Warum: Hilfsfunktion, um z. B. im UI die Eingabepunkte pro Art
		anzuzeigen. Für Prognosedaten nutze `get_prognose_datenreihe`.
		"""
		return [dp for dp in self.datenpunkte if dp.art == art]

	def get_prognose_datenreihe(self, art: ErzeugerArt) -> Datenreihe | None:
		"""Gibt die finale Prognose-Datenreihe für eine ErzeugerArt zurück.

		Warum: Dies ist der in der Planung vorgesehene Output je Erzeuger, der
		bereits `Heute + (Interpolierter Ausbau × ENorm)` enthält.
		"""
		for dr in self.prognose_datenreihen:
			if dr.art == art:
				return dr
		return None
