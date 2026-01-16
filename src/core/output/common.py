from datetime import datetime

import pandas
from pandas import DataFrame, Series
from plotly.graph_objects import Figure

from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard

# Auflösungen für Plots 2 und 3
RESOLUTION_OPTIONS: dict[str, str | None] = {
	"15 min": None,
	"1 Stunde": "h",
	"1 Tag": "D",
	"1 Woche": "W",
}


# Ändert die Auflösung eines DataFrames
def resample_dataframe(df: DataFrame, resolution_name: str) -> DataFrame:
	rule = RESOLUTION_OPTIONS.get(resolution_name)

	if rule is None:
		return df

	return df.resample(rule).mean()


# Farben für die einzelnen Graphen pro Erzeuger
GENERATOR_COLORS: dict[ErzeugerArt, str] = {
	ErzeugerArt.Biomasse: "#228B22",
	ErzeugerArt.Braunkohle: "#8B4513",
	ErzeugerArt.Erdgas: "#FF6347",
	ErzeugerArt.Kernenergie: "#FF00FF",
	ErzeugerArt.Photovoltaik: "#FFD700",
	ErzeugerArt.Pumpspeicher: "#9370DB",
	ErzeugerArt.SonstigeErneuerbare: "#32CD32",
	ErzeugerArt.SonstigeKonventionelle: "#808080",
	ErzeugerArt.Steinkohle: "#2F4F4F",
	ErzeugerArt.Wasserkraft: "#00CED1",
	ErzeugerArt.WindOffshore: "#1E90FF",
	ErzeugerArt.WindOnshore: "#4169E1",
}


# Konvertiert eine Hex-Farbe in eine RGBA-Farbe
def hex_to_rgba(color: str, alpha: float) -> str:
	r = int(color[1:3], 16)
	g = int(color[3:5], 16)
	b = int(color[5:7], 16)

	return f"rgba({r},{g},{b},{alpha})"


# Das Standardlayout für alle Plots
COMMON_LAYOUT: dict[str, object] = {
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


# Fügt Markierungen zu Plots hinzu
def add_vertical_markers(
	fig: Figure,
	smard_end: datetime,
	milestone_times: list[datetime],
	rows: int = 1,
) -> None:
	for row in range(1, rows + 1):
		fig.add_vline(
			x=smard_end,
			line_dash="dash",
			line_color="red",
			line_width=2,
			row=row,
			col=1,
		)

	fig.add_annotation(
		x=smard_end,
		y=1,
		yref="paper",
		text="Ende Historie",
		showarrow=False,
		yshift=10,
		font=dict(color="red"),
	)

	label_added = False
	for t in milestone_times:
		for row in range(1, rows + 1):
			fig.add_vline(
				x=t,
				line_dash="dot",
				line_color="black",
				line_width=1,
				opacity=0.5,
				row=row,
				col=1,
			)

		if not label_added:
			fig.add_annotation(
				x=t,
				y=1,
				yref="paper",
				text="Prognose-Punkte",
				showarrow=False,
				yshift=10,
				font=dict(color="black"),
			)
			label_added = True


# Kombiniert Datenreihen in ein einziges Dataframe
def merge_datenreihen_to_dataframe(datenreihen: list[Datenreihe]) -> DataFrame:
	if not datenreihen:
		return DataFrame()

	series_list: list[Series] = []
	for dr in datenreihen:
		series = dr.df.set_index("Datum von")[dr.art]

		if series.index.has_duplicates:
			series = series.groupby(level=0).mean()

		series_list.append(series.sort_index())

	return pandas.concat(series_list, axis=1).fillna(0.0)


# Bereitet DataFrames zur Nutzung von Plots vor
def prepare_plot_dataframes(
	ausbaupfad: Ausbaupfad,
	realisiert_datenreihen: dict[ErzeugerArt, Datenreihe[ErzeugerArt]],
) -> tuple[DataFrame, DataFrame, list[ErzeugerArt]]:
	df_prognose = merge_datenreihen_to_dataframe(ausbaupfad.prognose_erzeuger)
	df_realisiert = merge_datenreihen_to_dataframe(realisiert_datenreihen.values())

	cols = sorted(df_prognose.columns)

	if cols:
		df_prognose = df_prognose[cols]

	if not df_realisiert.empty:
		df_realisiert = df_realisiert[sorted(df_realisiert.columns)]

	return df_prognose, df_realisiert, cols


# Holt den Endzeitpunkt der SMARD-Daten
def get_smard_end(smard: Smard) -> datetime:
	for art in ErzeugerArt:
		try:
			return smard.get_erzeuger(art).realisiert.anfang.iloc[-1]
		except Exception:
			continue

	return datetime.now()


# Holt alle Zeitpunkte von Eingaben im Ausbaupfad
def collect_milestone_times(ausbaupfad: Ausbaupfad) -> list[datetime]:
	times: set[datetime] = set()

	for dp in ausbaupfad.installiert:
		times.add(dp.datum)

	for dp in ausbaupfad.verbraucht:
		times.add(dp.datum)

	return sorted(times)
