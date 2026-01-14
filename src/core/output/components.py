"""
Reusable Plotly components for energy visualization.

Provides:
- Color mappings for generators
- Resolution options
- Vertical marker helpers
- Common styling
"""

import pandas
from pandas import DataFrame

from core.setup.erzeuger import ErzeugerArt

# =============================================================================
# Resolution Options
# =============================================================================

RESOLUTION_OPTIONS = {
	"15 min": None,  # Original resolution (no resampling)
	"1 Stunde": "h",  # Hourly
	"1 Tag": "D",  # Daily
	"1 Woche": "W",  # Weekly
}


def resample_dataframe(df: DataFrame, resolution: str) -> DataFrame:
	"""
	Resample a time-indexed DataFrame to a different resolution.

	Args:
		df: DataFrame with DatetimeIndex
		resolution: Key from RESOLUTION_OPTIONS (e.g., "1 Woche")

	Returns:
		Resampled DataFrame (mean aggregation)
	"""
	if df.empty:
		return df

	rule = RESOLUTION_OPTIONS.get(resolution)
	if rule is None:
		return df

	return df.resample(rule).mean()


# =============================================================================
# Color Mapping
# =============================================================================

# Predefined colors for generator types (consistent across all plots)
GENERATOR_COLORS = {
	ErzeugerArt.Photovoltaik: "#FFD700",  # Gold/Yellow
	ErzeugerArt.WindOnshore: "#4169E1",  # Royal Blue
	ErzeugerArt.WindOffshore: "#1E90FF",  # Dodger Blue
	ErzeugerArt.Wasserkraft: "#00CED1",  # Dark Turquoise
	ErzeugerArt.Biomasse: "#228B22",  # Forest Green
	ErzeugerArt.Pumpspeicher: "#9370DB",  # Medium Purple
	ErzeugerArt.SonstigeErneuerbare: "#32CD32",  # Lime Green
	ErzeugerArt.Erdgas: "#FF6347",  # Tomato Red
	ErzeugerArt.Steinkohle: "#2F4F4F",  # Dark Slate Gray
	ErzeugerArt.Braunkohle: "#8B4513",  # Saddle Brown
	ErzeugerArt.Kernenergie: "#FF00FF",  # Magenta
	ErzeugerArt.SonstigeKonventionelle: "#808080",  # Gray
}


def get_color(art: ErzeugerArt) -> str:
	"""Get the color for a generator type."""
	return GENERATOR_COLORS.get(art, "#999999")


def get_color_map(arts: list[ErzeugerArt]) -> dict[ErzeugerArt, str]:
	"""
	Get a color mapping for a list of generator types.

	Args:
		arts: List of ErzeugerArt values

	Returns:
		Dictionary mapping ErzeugerArt -> hex color string
	"""
	return {art: get_color(art) for art in arts}


# =============================================================================
# Plot Styling
# =============================================================================

# Common layout settings for all plots
COMMON_LAYOUT = {
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
	"margin": {"r": 220, "t": 100, "l": 80, "b": 60},  # Space for legend, title, and labels
}


def add_vertical_markers(
	fig,
	smard_end,
	datenpunkt_times: list,
) -> None:
	"""
	Add vertical marker lines to a Plotly figure.

	Args:
		fig: Plotly figure object
		smard_end: Timestamp marking end of historical data
		datenpunkt_times: List of forecast milestone timestamps
	"""
	# Convert pandas Timestamp to Python datetime if needed
	if hasattr(smard_end, "to_pydatetime"):
		smard_end_dt = smard_end.to_pydatetime()
	else:
		smard_end_dt = smard_end

	# Red dashed line for end of historical data
	fig.add_vline(
		x=smard_end_dt,
		line_dash="dash",
		line_color="red",
		line_width=2,
	)

	# Add annotation separately to avoid timestamp issues
	fig.add_annotation(
		x=smard_end_dt,
		y=1,
		yref="paper",
		text="Ende Historie",
		showarrow=False,
		yshift=10,
		font=dict(color="red"),
	)

	# Black dotted lines for forecast data points
	for i, t in enumerate(datenpunkt_times):
		# Convert pandas Timestamp to Python datetime if needed
		if hasattr(t, "to_pydatetime"):
			t_dt = t.to_pydatetime()
		else:
			t_dt = t

		fig.add_vline(
			x=t_dt,
			line_dash="dot",
			line_color="black",
			line_width=1,
			opacity=0.5,
		)

		# Only label the first one to avoid clutter
		if i == 0:
			fig.add_annotation(
				x=t_dt,
				y=1,
				yref="paper",
				text="Prognose-Punkte",
				showarrow=False,
				yshift=10,
				font=dict(color="black"),
			)


# =============================================================================
# Data Preparation Helpers
# =============================================================================


def merge_datenreihen_to_dataframe(datenreihen: list) -> DataFrame:
	"""
	Merge multiple Datenreihen into a single DataFrame.

	Args:
		datenreihen: List of Datenreihe objects

	Returns:
		DataFrame with time index and one column per Datenreihe
	"""
	if not datenreihen:
		return DataFrame()

	data_series_list = []
	for dr in datenreihen:
		series = dr.df.set_index("Datum von")[dr.art]
		data_series_list.append(series)

	merged_df = pandas.concat(data_series_list, axis=1).fillna(0)
	return merged_df


def prepare_plot_dataframes(
	ausbaupfad,
	realisiert_datenreihen: dict,
) -> tuple:
	"""
	Prepare all DataFrames needed for visualization.

	Args:
		ausbaupfad: Ausbaupfad object with prognose data
		realisiert_datenreihen: Dict of realized generation Datenreihen

	Returns:
		Tuple of (df_prognose, df_realisiert, columns)
	"""
	# Prognose data
	df_prognose = merge_datenreihen_to_dataframe(ausbaupfad.prognose_erzeuger)

	# Realized data
	realisiert_list = list(realisiert_datenreihen.values())
	df_realisiert = merge_datenreihen_to_dataframe(realisiert_list)

	# Sort columns for consistent ordering
	if not df_prognose.empty:
		cols = sorted(df_prognose.columns)
		df_prognose = df_prognose[cols]
	else:
		cols = []

	if not df_realisiert.empty:
		realisiert_cols = sorted(df_realisiert.columns)
		df_realisiert = df_realisiert[realisiert_cols]

	return df_prognose, df_realisiert, cols
