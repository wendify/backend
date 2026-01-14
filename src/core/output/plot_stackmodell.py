"""
Plot 2: Stackmodell (realisierte Erzeugung).

This plot shows the output of the stack model:
- stacked area: realized generation per ErzeugerArt
- line: total realized generation
- line: demand (Netzlast or first available consumer series)

It also provides a resolution dropdown (15 min / 1h / 1d / 1w).
"""

from __future__ import annotations

from pandas import DataFrame
from plotly.graph_objects import Figure, Scatter

from core.output.plot_common import (
	COMMON_LAYOUT,
	RESOLUTION_OPTIONS,
	add_vertical_markers,
	collect_milestone_times,
	get_color_map,
	get_smard_end,
	hex_to_rgba,
	merge_datenreihen_to_dataframe,
	resample_dataframe,
)
from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard
from core.setup.verbraucher import VerbraucherArt


def build_stackmodell_plot(
	ausbaupfad: Ausbaupfad,
	realisiert_datenreihen: dict[ErzeugerArt, Datenreihe],
	smard: Smard,
	default_resolution: str = "1 Woche",
) -> Figure:
	"""
	Build the stack model plot.

	Args:
		ausbaupfad: Expansion path (provides consumer series for demand line).
		realisiert_datenreihen: Output from `stack.apply_stack_model`.
		smard: SMARD data source (fallback for demand series).
		default_resolution: Initial dropdown selection.

	Returns:
		Plotly Figure.
	"""
	fig = Figure()

	# Convert realized generation to a DataFrame
	realisiert_list = []
	for dr in realisiert_datenreihen.values():
		realisiert_list.append(dr)
	df_realisiert = merge_datenreihen_to_dataframe(realisiert_list)

	if df_realisiert.empty:
		fig.add_annotation(
			text="Keine Stackmodell-Daten vorhanden",
			xref="paper",
			yref="paper",
			x=0.5,
			y=0.5,
			showarrow=False,
		)
		return fig

	cols = sorted(df_realisiert.columns)
	color_map = get_color_map(cols)

	# Demand series (prefer Netzlast prognosis, else first, else SMARD Netzlast)
	verbrauch_series = _get_demand_series(ausbaupfad=ausbaupfad, smard=smard)

	resolution_list = list(RESOLUTION_OPTIONS.keys())
	num_resolutions = len(resolution_list)
	num_generators = len(cols)

	for res_idx, res_name in enumerate(resolution_list):
		df_resampled = resample_dataframe(df_realisiert, res_name)

		is_visible = res_name == default_resolution
		show_in_legend = res_name == default_resolution

		# Stacked realized generation
		for art in cols:
			fig.add_trace(
				Scatter(
					x=df_resampled.index,
					y=df_resampled[art],
					name=str(art.value) if hasattr(art, "value") else str(art),
					mode="lines",
					stackgroup=f"realized_{res_idx}",
					fillcolor=hex_to_rgba(color_map[art], 0.75),
					line=dict(width=0.5, color=hex_to_rgba(color_map[art], 0.9)),
					hovertemplate="%{y:,.0f} MW<extra>%{fullData.name}</extra>",
					visible=is_visible,
					legendgroup=f"{art}_{res_idx}",
					showlegend=show_in_legend,
				)
			)

		# Total realized generation line
		total_realized = df_resampled[cols].sum(axis=1)
		fig.add_trace(
			Scatter(
				x=total_realized.index,
				y=total_realized.values,
				name="Gesamterzeugung (realisiert)",
				mode="lines",
				line=dict(color="darkgray", width=3),
				hovertemplate="%{y:,.0f} MW<extra>Gesamt</extra>",
				visible=is_visible,
				legendgroup=f"total_{res_idx}",
				showlegend=show_in_legend,
			)
		)

		# Demand line
		if verbrauch_series is not None and len(verbrauch_series) > 0:
			df_demand = DataFrame({"d": verbrauch_series})
			demand_resampled = resample_dataframe(df_demand, res_name)["d"]
			demand_plot = demand_resampled.reindex(df_resampled.index, method="ffill")

			fig.add_trace(
				Scatter(
					x=demand_plot.index,
					y=demand_plot.values,
					name="Verbrauch/Bedarf",
					mode="lines",
					line=dict(color="black", width=2, dash="dash"),
					hovertemplate="%{y:,.0f} MW<extra>Verbrauch</extra>",
					visible=is_visible,
					legendgroup=f"demand_{res_idx}",
					showlegend=show_in_legend,
				)
			)

	smard_end = get_smard_end(smard)
	milestones = collect_milestone_times(ausbaupfad)
	add_vertical_markers(fig, smard_end=smard_end, milestone_times=milestones, rows=1)

	fig.update_layout(
		title=f"Stackmodell: Realisierte Erzeugung (Auflösung: {default_resolution})",
		xaxis_title="Zeit",
		yaxis_title="Leistung [MW]",
		**COMMON_LAYOUT,
	)

	# Dropdown: we have N generator traces + total + demand per resolution
	has_demand = verbrauch_series is not None and len(verbrauch_series) > 0
	traces_per_resolution = num_generators + 1 + (1 if has_demand else 0)

	buttons = []
	for res_idx, res_name in enumerate(resolution_list):
		visible_list = []
		showlegend_list = []

		for r_idx in range(num_resolutions):
			for _ in range(traces_per_resolution):
				is_this = r_idx == res_idx
				visible_list.append(is_this)
				showlegend_list.append(is_this)

		buttons.append(
			dict(
				label=res_name,
				method="update",
				args=[
					{"visible": visible_list, "showlegend": showlegend_list},
					{"title.text": f"Stackmodell: Realisierte Erzeugung (Auflösung: {res_name})"},
				],
			)
		)

	fig.update_layout(
		updatemenus=[
			dict(
				type="dropdown",
				direction="down",
				x=0.02,
				y=1.02,
				showactive=True,
				active=resolution_list.index(default_resolution)
				if default_resolution in resolution_list
				else 0,
				buttons=buttons,
				bgcolor="rgba(255,255,255,0.9)",
				borderwidth=1,
			)
		],
		annotations=[
			dict(
				text="Auflösung:",
				x=-0.02,
				y=1.02,
				xref="paper",
				yref="paper",
				showarrow=False,
				font=dict(size=11),
			)
		],
	)

	return fig


def _get_demand_series(ausbaupfad: Ausbaupfad, smard: Smard):
	"""
	Get a demand (consumer) time series for plotting.

	Preference:
	1) ausbaupfad.prognose_verbraucher Netzlast
	2) ausbaupfad.prognose_verbraucher first entry
	3) SMARD Netzlast
	"""
	verbrauch_dr = None

	if hasattr(ausbaupfad, "prognose_verbraucher") and ausbaupfad.prognose_verbraucher:
		for dr in ausbaupfad.prognose_verbraucher:
			if dr.art == VerbraucherArt.Netzlast:
				verbrauch_dr = dr
				break

		if verbrauch_dr is None:
			verbrauch_dr = ausbaupfad.prognose_verbraucher[0]

	if verbrauch_dr is None:
		try:
			verbrauch_dr = smard.get_verbraucher(VerbraucherArt.Netzlast).verbraucht
		except Exception:
			return None

	series = verbrauch_dr.df.set_index("Datum von")[verbrauch_dr.art]
	if series.index.has_duplicates:
		series = series.groupby(level=0).mean()
	series = series.sort_index()
	return series

