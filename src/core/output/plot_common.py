"""
Shared helpers for Plotly output plots.

The goal of this module is to keep each plot builder small and readable:
- consistent colors and layout
- consistent time resolution resampling
- simple helpers to convert simulation data structures into DataFrames
"""

from __future__ import annotations

from datetime import datetime

import pandas
from pandas import DataFrame, Series

from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard

# =============================================================================
# Resolution Options
# =============================================================================

RESOLUTION_OPTIONS: dict[str, str | None] = {
	"15 min": None,  # original resolution (no resampling)
	"1 Stunde": "h",
	"1 Tag": "D",
	"1 Woche": "W",
}


def resample_dataframe(df: DataFrame, resolution_name: str) -> DataFrame:
	"""
	Resample a time-indexed DataFrame to a different resolution.

	Args:
		df: DataFrame with DatetimeIndex.
		resolution_name: Key from RESOLUTION_OPTIONS.

	Returns:
		Resampled DataFrame (mean aggregation). If df is empty or resolution is
		'15 min', the original df is returned.
	"""
	if df is None or df.empty:
		return DataFrame()

	rule = RESOLUTION_OPTIONS.get(resolution_name)
	if rule is None:
		return df

	return df.resample(rule).mean()


# =============================================================================
# Styling and Colors
# =============================================================================

GENERATOR_COLORS: dict[ErzeugerArt, str] = {
	ErzeugerArt.Photovoltaik: "#FFD700",
	ErzeugerArt.WindOnshore: "#4169E1",
	ErzeugerArt.WindOffshore: "#1E90FF",
	ErzeugerArt.Wasserkraft: "#00CED1",
	ErzeugerArt.Biomasse: "#228B22",
	ErzeugerArt.Pumpspeicher: "#9370DB",
	ErzeugerArt.SonstigeErneuerbare: "#32CD32",
	ErzeugerArt.Erdgas: "#FF6347",
	ErzeugerArt.Steinkohle: "#2F4F4F",
	ErzeugerArt.Braunkohle: "#8B4513",
	ErzeugerArt.Kernenergie: "#FF00FF",
	ErzeugerArt.SonstigeKonventionelle: "#808080",
}


def get_color(art: ErzeugerArt) -> str:
	"""Return the base hex color for the generator type."""
	return GENERATOR_COLORS.get(art, "#999999")


def get_color_map(arten: list[ErzeugerArt]) -> dict[ErzeugerArt, str]:
	"""Return a mapping ErzeugerArt -> hex color."""
	result: dict[ErzeugerArt, str] = {}
	for art in arten:
		result[art] = get_color(art)
	return result


def hex_to_rgba(hex_color: str, alpha: float) -> str:
	"""
	Convert a hex color (e.g. '#FF00AA') to an rgba(...) string.

	Args:
		hex_color: Color in '#RRGGBB' format.
		alpha: Opacity in [0, 1].
	"""
	color = hex_color.lstrip("#")
	if len(color) != 6:
		return f"rgba(153,153,153,{alpha})"

	r = int(color[0:2], 16)
	g = int(color[2:4], 16)
	b = int(color[4:6], 16)
	return f"rgba({r},{g},{b},{alpha})"


COMMON_LAYOUT: dict = {
	"template": "plotly_white",
	"hovermode": "x unified",
	"legend": {
		"orientation": "v",
		"yanchor": "top",
		"y": 1,
		"xanchor": "left",
		"x": 1.02,
		"bgcolor": "rgba(255,255,255,0.8)",
		"bordercolor": "rgba(0,0,0,0.2)",
		"borderwidth": 1,
	},
	"margin": {"r": 240, "t": 90, "l": 80, "b": 60},
}


# =============================================================================
# Markers (historical boundary + milestones)
# =============================================================================


def add_vertical_markers(fig, smard_end: datetime, milestone_times: list[datetime], rows: int = 1) -> None:
	"""
	Add vertical marker lines to a Plotly figure.

	Args:
		fig: Plotly Figure or subplot Figure.
		smard_end: End date of historical data (red dashed line).
		milestone_times: Times of scenario milestones (black dotted lines).
		rows: For subplots: number of rows to apply markers to.
	"""
	# Plotly sometimes receives pandas Timestamps; make them python datetimes.
	if hasattr(smard_end, "to_pydatetime"):
		smard_end_dt = smard_end.to_pydatetime()
	else:
		smard_end_dt = smard_end

	for row in range(1, rows + 1):
		fig.add_vline(
			x=smard_end_dt,
			line_dash="dash",
			line_color="red",
			line_width=2,
			row=row,
			col=1,
		)

	# Label only once (top subplot / single plot)
	fig.add_annotation(
		x=smard_end_dt,
		y=1,
		yref="paper",
		text="Ende Historie",
		showarrow=False,
		yshift=10,
		font=dict(color="red"),
	)

	first_label_done = False
	for t in milestone_times:
		if hasattr(t, "to_pydatetime"):
			t_dt = t.to_pydatetime()
		else:
			t_dt = t

		for row in range(1, rows + 1):
			fig.add_vline(
				x=t_dt,
				line_dash="dot",
				line_color="black",
				line_width=1,
				opacity=0.5,
				row=row,
				col=1,
			)

		if not first_label_done:
			fig.add_annotation(
				x=t_dt,
				y=1,
				yref="paper",
				text="Prognose-Punkte",
				showarrow=False,
				yshift=10,
				font=dict(color="black"),
			)
			first_label_done = True


# =============================================================================
# DataFrame preparation
# =============================================================================


def merge_datenreihen_to_dataframe(datenreihen: list[Datenreihe]) -> DataFrame:
	"""
	Merge multiple Datenreihen into a single DataFrame.

	The result index is 'Datum von', columns are the `Datenreihe.art` values.

	Args:
		datenreihen: List of Datenreihe objects.

	Returns:
		DataFrame with DatetimeIndex.
	"""
	if not datenreihen:
		return DataFrame()

	data_series_list: list[Series] = []
	for dr in datenreihen:
		series = dr.df.set_index("Datum von")[dr.art]

		# Ensure unique index
		if series.index.has_duplicates:
			series = series.groupby(level=0).mean()

		series = series.sort_index()
		data_series_list.append(series)

	if not data_series_list:
		return DataFrame()

	df = pandas.concat(data_series_list, axis=1).fillna(0.0)
	return df


def prepare_plot_dataframes(
	ausbaupfad: Ausbaupfad,
	realisiert_datenreihen: dict[ErzeugerArt, Datenreihe],
) -> tuple[DataFrame, DataFrame, list[ErzeugerArt]]:
	"""
	Prepare the core DataFrames used by multiple plots.

	Args:
		ausbaupfad: Expansion path object with prognosis data.
		realisiert_datenreihen: Dict of realized generation Datenreihen.

	Returns:
		(df_prognose, df_realisiert, cols)
	"""
	df_prognose = merge_datenreihen_to_dataframe(ausbaupfad.prognose_erzeuger)

	realisiert_list = []
	for dr in realisiert_datenreihen.values():
		realisiert_list.append(dr)
	df_realisiert = merge_datenreihen_to_dataframe(realisiert_list)

	cols: list[ErzeugerArt] = []
	if not df_prognose.empty:
		cols = sorted(df_prognose.columns)
		df_prognose = df_prognose[cols]

	if not df_realisiert.empty:
		real_cols = sorted(df_realisiert.columns)
		df_realisiert = df_realisiert[real_cols]

	return df_prognose, df_realisiert, cols


def get_smard_end(smard: Smard) -> datetime:
	"""
	Get a robust 'end of history' timestamp from SMARD.

	We try a few generator series until one works.
	"""
	for art in ErzeugerArt:
		try:
			erz = smard.get_erzeuger(art)
			return erz.realisiert.df["Datum von"].iloc[-1]
		except Exception:
			continue

	# Fallback: now (should practically never happen)
	return datetime.now()


def collect_milestone_times(ausbaupfad: Ausbaupfad) -> list[datetime]:
	"""
	Collect unique milestone times from the Ausbaupfad inputs.

	We use both installed-capacity targets and consumption targets.
	"""
	times_set: set[datetime] = set()

	if hasattr(ausbaupfad, "installiert"):
		for dp in ausbaupfad.installiert:
			times_set.add(dp.datum)

	if hasattr(ausbaupfad, "verbraucht"):
		for dp in ausbaupfad.verbraucht:
			times_set.add(dp.datum)

	return sorted(times_set)

