"""
Plot 3: CO2 (absolut).

Input is `co2_df` produced by `core.simulation.co2.calculate_emissions`:
- index: 'Datum von'
- columns: ErzeugerArt
- values: t CO2 per time step

We visualize:
- stacked area: emissions by producer
- line: total emissions
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
	resample_dataframe,
)
from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard


def build_co2_plot(
	co2_df: DataFrame | None,
	ausbaupfad: Ausbaupfad,
	smard: Smard,
	default_resolution: str = "1 Woche",
) -> Figure:
	"""
	Build the CO2 (absolute) plot.

	Args:
		co2_df: DataFrame with t CO2 per time step (columns: ErzeugerArt).
		ausbaupfad: For milestone markers.
		smard: For 'end of history' marker.
		default_resolution: Initial dropdown selection.

	Returns:
		Plotly Figure.
	"""
	fig = Figure()

	if co2_df is None or co2_df.empty:
		fig.add_annotation(
			text="Keine CO2-Daten vorhanden",
			xref="paper",
			yref="paper",
			x=0.5,
			y=0.5,
			showarrow=False,
		)
		return fig

	# Keep only ErzeugerArt columns with non-zero totals
	cols: list[ErzeugerArt] = []
	for col in co2_df.columns:
		if isinstance(col, ErzeugerArt):
			total = float(co2_df[col].sum())
			if total > 0.0:
				cols.append(col)

	cols = sorted(cols, key=lambda x: str(x.value) if hasattr(x, "value") else str(x))

	if not cols:
		fig.add_annotation(
			text="Keine CO2-Emissionen (nur erneuerbare Erzeuger)",
			xref="paper",
			yref="paper",
			x=0.5,
			y=0.5,
			showarrow=False,
		)
		return fig

	color_map = get_color_map(cols)

	resolution_list = list(RESOLUTION_OPTIONS.keys())
	num_resolutions = len(resolution_list)
	num_producers = len(cols)

	for res_idx, res_name in enumerate(resolution_list):
		df_resampled = resample_dataframe(co2_df, res_name)

		is_visible = res_name == default_resolution
		show_in_legend = res_name == default_resolution

		# Stacked emissions per producer
		for art in cols:
			fig.add_trace(
				Scatter(
					x=df_resampled.index,
					y=df_resampled[art],
					name=str(art.value) if hasattr(art, "value") else str(art),
					mode="lines",
					stackgroup=f"co2_{res_idx}",
					fillcolor=hex_to_rgba(color_map[art], 0.75),
					line=dict(width=0.5, color=hex_to_rgba(color_map[art], 0.9)),
					hovertemplate="%{y:,.2f} t CO2<extra>%{fullData.name}</extra>",
					visible=is_visible,
					legendgroup=f"{art}_{res_idx}",
					showlegend=show_in_legend,
				)
			)

		# Total CO2 line
		total_co2 = df_resampled[cols].sum(axis=1)
		fig.add_trace(
			Scatter(
				x=total_co2.index,
				y=total_co2.values,
				name="Gesamt CO2",
				mode="lines",
				line=dict(color="black", width=3),
				hovertemplate="%{y:,.2f} t CO2<extra>Gesamt</extra>",
				visible=is_visible,
				legendgroup=f"total_{res_idx}",
				showlegend=show_in_legend,
			)
		)

	smard_end = get_smard_end(smard)
	milestones = collect_milestone_times(ausbaupfad)
	add_vertical_markers(fig, smard_end=smard_end, milestone_times=milestones, rows=1)

	fig.update_layout(
		title=f"CO2-Emissionen (Auflösung: {default_resolution})",
		xaxis_title="Zeit",
		yaxis_title="CO2-Emissionen [t]",
		**COMMON_LAYOUT,
	)

	traces_per_resolution = num_producers + 1
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
					{"title.text": f"CO2-Emissionen (Auflösung: {res_name})"},
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

