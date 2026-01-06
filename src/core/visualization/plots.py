"""
Plotly-based interactive plots for energy prognosis visualization.

All plots open in the browser with full interactivity:
- Hover info with values
- Zoom/Pan
- Generator filtering via legend clicks
- Resolution selection via dropdown
"""

import datetime
from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go

from core.prognose.ausbaupfad import Ausbaupfad
from core.prognose.loader import Installation
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard
from core.visualization.components import (
	COMMON_LAYOUT,
	RESOLUTION_OPTIONS,
	add_vertical_markers,
	get_color_map,
	prepare_plot_dataframes,
	resample_dataframe,
)


def show_all_plots(
	ausbaupfad: Ausbaupfad,
	realisiert_datenreihen: Dict[ErzeugerArt, Datenreihe],
	datenpunkte: List[Installation],
	smard: Smard,
	co2_df: pd.DataFrame = None,
	default_resolution: str = "1 Woche",
	debug_art: ErzeugerArt = ErzeugerArt.Steinkohle,
) -> None:
	"""
	Show all prognosis plots in the browser.

	Args:
		ausbaupfad: The expansion path with forecast data
		realisiert_datenreihen: Realized generation from stack model
		datenpunkte: Scenario data points
		smard: SMARD data source
		co2_df: DataFrame with CO2 emissions per producer (optional)
		default_resolution: Default time resolution for plots
		debug_art: Producer type for debug plot
	"""
	df_prognose, df_realisiert, cols = prepare_plot_dataframes(ausbaupfad, realisiert_datenreihen)

	if df_prognose.empty:
		print("Keine Prognosedaten vorhanden.")
		return

	pv = smard.get_erzeuger(ErzeugerArt.Photovoltaik)
	smard_end = pv.realisiert.df["Datum von"].iloc[-1]
	dp_times = sorted({dp.datum for dp in datenpunkte})

	print("Öffne Plots im Browser...")

	# fig1 = create_prognose_stackplot(
	# 	df_prognose, cols, smard_end, dp_times, default_resolution
	# )
	# fig1.show()

	fig2 = create_installed_capacity_plot(ausbaupfad, datenpunkte, smard, cols, smard_end, dp_times)
	fig2.show()

	if not df_realisiert.empty:
		fig3 = create_realized_stackplot(
			df_realisiert,
			ausbaupfad,
			smard_end,
			dp_times,
			default_resolution,
			df_prognose=df_prognose,
		)
		fig3.show()

	# Plot 4: Surplus/Deficit Plot (VOR Abregelung!)
	fig4 = create_surplus_plot(df_prognose, ausbaupfad, smard_end, dp_times, default_resolution)
	fig4.show()

	# Plot 5: Vergleich Max verfügbar vs Realisiert vs Verbrauch
	if not df_realisiert.empty:
		fig5 = create_comparison_stackplot(
			df_prognose, df_realisiert, ausbaupfad, smard_end, dp_times, default_resolution
		)
		fig5.show()

	# Plot 6: Abregelung / Curtailment
	if not df_realisiert.empty:
		fig6 = create_curtailment_plot(
			df_prognose, df_realisiert, ausbaupfad, smard_end, dp_times, default_resolution
		)
		fig6.show()

	# Plot 7: Einzelner Generator (Prognose vs Realisiert)
	if not df_realisiert.empty and debug_art in df_prognose.columns:
		fig7 = create_single_generator_plot(
			df_prognose,
			df_realisiert,
			debug_art,
			ausbaupfad,
			smard_end,
			dp_times,
			default_resolution,
		)
		fig7.show()

	# Plot 8: CO2-Emissionen
	if co2_df is not None and not co2_df.empty:
		fig8 = create_co2_plot(co2_df, smard_end, dp_times, default_resolution)
		fig8.show()


def create_prognose_stackplot(
	df: pd.DataFrame,
	cols: List[ErzeugerArt],
	smard_end,
	dp_times: List,
	resolution: str,
) -> go.Figure:
	fig = go.Figure()
	color_map = get_color_map(cols)

	resolution_list = list(RESOLUTION_OPTIONS.keys())
	num_resolutions = len(resolution_list)

	for res_idx, res_name in enumerate(resolution_list):
		df_resampled = resample_dataframe(df, res_name)
		is_visible = res_name == resolution
		show_in_legend = res_name == resolution

		for col in cols:
			col_name = str(col.value) if hasattr(col, "value") else str(col)
			fig.add_trace(
				go.Scatter(
					x=df_resampled.index,
					y=df_resampled[col],
					name=col_name,
					mode="lines",
					stackgroup=f"generation_{res_idx}",
					fillcolor=color_map[col],
					line=dict(width=0.5, color=color_map[col]),
					hovertemplate="%{y:,.0f} MW<extra>%{fullData.name}</extra>",
					visible=is_visible,
					legendgroup=f"{col}_{res_idx}",
					showlegend=show_in_legend,
				)
			)

	add_vertical_markers(fig, smard_end, dp_times)

	fig.update_layout(
		title=f"Prognose: Stromerzeugung (Auflösung: {resolution})",
		xaxis_title="Zeit",
		yaxis_title="Leistung [MW]",
		**COMMON_LAYOUT,
	)

	num_generators = len(cols)
	buttons = []

	for res_idx, res_name in enumerate(resolution_list):
		visibility = []
		showlegend_list = []
		for r_idx in range(num_resolutions):
			for _ in range(num_generators):
				visibility.append(r_idx == res_idx)
				showlegend_list.append(r_idx == res_idx)

		buttons.append(
			dict(
				label=res_name,
				method="update",
				args=[
					{"visible": visibility, "showlegend": showlegend_list},
					{"title.text": f"Prognose: Stromerzeugung (Auflösung: {res_name})"},
				],
			)
		)

	fig.update_layout(
		updatemenus=[
			dict(
				type="dropdown",
				direction="down",
				x=0.0,
				y=1.15,
				showactive=True,
				active=resolution_list.index(resolution),
				buttons=buttons,
			)
		],
		annotations=[
			dict(
				text="Auflösung:",
				x=-0.05,
				y=1.15,
				xref="paper",
				yref="paper",
				showarrow=False,
			)
		],
	)

	return fig


def create_installed_capacity_plot(
	ausbaupfad: Ausbaupfad,
	datenpunkte: List[Installation],
	smard: Smard,
	cols: List[ErzeugerArt],
	smard_end,
	dp_times: List,
) -> go.Figure:
	# unverändert (wie bei dir)
	fig = go.Figure()
	color_map = get_color_map(cols)

	plot_start = smard_end - datetime.timedelta(days=365)
	plot_end = max(dp_times) if dp_times else smard_end + datetime.timedelta(days=365 * 5)

	for art in cols:
		dps = ausbaupfad.get_erzeuger(art)

		try:
			erz = smard.get_erzeuger(art)
			last_smard_time = erz.installiert.df["Datum von"].iloc[-1]
			last_smard_val = erz.installiert.werte.iloc[-1]
		except Exception:
			continue

		if not dps:
			fig.add_trace(
				go.Scatter(
					x=[plot_start, plot_end],
					y=[last_smard_val, last_smard_val],
					name=str(art.value) if hasattr(art, "value") else str(art),
					mode="lines",
					line=dict(color=color_map[art], width=2),
					hovertemplate="%{y:,.0f} MW<extra>%{fullData.name}</extra>",
				)
			)
		else:
			x_points = [last_smard_time]
			y_points = [last_smard_val]

			for dp in sorted(dps, key=lambda d: d.datum):
				x_points.append(dp.datum)
				y_points.append(dp.wert)

			fig.add_trace(
				go.Scatter(
					x=x_points,
					y=y_points,
					name=str(art.value) if hasattr(art, "value") else str(art),
					mode="lines+markers",
					line=dict(color=color_map[art], width=2),
					marker=dict(size=8),
					hovertemplate="%{y:,.0f} MW<extra>%{fullData.name}</extra>",
				)
			)

	add_vertical_markers(fig, smard_end, dp_times)

	fig.update_layout(
		title="Installierte Leistung (Ausbaupfad)",
		xaxis_title="Zeit",
		yaxis_title="Installierte Leistung [MW]",
		**COMMON_LAYOUT,
	)

	return fig


def create_realized_stackplot(
	df: pd.DataFrame,
	ausbaupfad: Ausbaupfad,
	smard_end,
	dp_times: List,
	resolution: str,
	df_prognose: pd.DataFrame = None,
) -> go.Figure:
	"""
	Realisierte Erzeugung (Stack-Modell Output) + Linien:
	- Gesamterzeugung (realisiert)
	- Bedarf
	- Überschuss NACH Abregelung = realisiert - Bedarf
	- optional Überschuss VOR Abregelung = max_verfügbar - Bedarf (gestrichelt)
	"""
	fig = go.Figure()

	cols = sorted(df.columns)
	color_map = get_color_map(cols)

	verbrauch_series = None
	if ausbaupfad.prognose_verbraucher:
		verbrauch_dr = ausbaupfad.prognose_verbraucher[0]
		verbrauch_series = verbrauch_dr.df.set_index("Datum von")[verbrauch_dr.art]

	resolution_list = list(RESOLUTION_OPTIONS.keys())
	num_resolutions = len(resolution_list)
	num_generators = len(cols)

	has_demand = verbrauch_series is not None
	has_surplus_after = has_demand
	has_surplus_before = (df_prognose is not None) and has_demand

	for res_idx, res_name in enumerate(resolution_list):
		df_resampled = resample_dataframe(df, res_name)

		is_visible = res_name == resolution
		show_in_legend = res_name == resolution

		# Stacks
		for col in cols:
			col_name = str(col.value) if hasattr(col, "value") else str(col)
			fig.add_trace(
				go.Scatter(
					x=df_resampled.index,
					y=df_resampled[col],
					name=col_name,
					mode="lines",
					stackgroup=f"realized_{res_idx}",
					fillcolor=color_map[col],
					line=dict(width=0.5, color=color_map[col]),
					hovertemplate="%{y:,.0f} MW<extra>%{fullData.name}</extra>",
					visible=is_visible,
					legendgroup=f"{col}_{res_idx}",
					showlegend=show_in_legend,
				)
			)

		# Total realized
		total_realized = df_resampled[cols].sum(axis=1)
		fig.add_trace(
			go.Scatter(
				x=df_resampled.index,
				y=total_realized,
				name="Gesamterzeugung (realisiert)",
				mode="lines",
				line=dict(color="darkgray", width=3),
				hovertemplate="%{y:,.0f} MW<extra>Gesamt</extra>",
				visible=is_visible,
				legendgroup=f"total_{res_idx}",
				showlegend=show_in_legend,
			)
		)

		# Demand + Surplus lines
		if has_demand:
			verbrauch_resampled = resample_dataframe(
				pd.DataFrame({"v": verbrauch_series}), res_name
			)["v"]
			verbrauch_plot = verbrauch_resampled.reindex(df_resampled.index, method="ffill")

			fig.add_trace(
				go.Scatter(
					x=verbrauch_plot.index,
					y=verbrauch_plot.values,
					name="Verbrauch/Bedarf",
					mode="lines",
					line=dict(color="black", width=2, dash="dash"),
					hovertemplate="%{y:,.0f} MW<extra>Verbrauch</extra>",
					visible=is_visible,
					legendgroup=f"demand_{res_idx}",
					showlegend=show_in_legend,
				)
			)

			# Überschuss NACH Abregelung (realisiert - demand)
			surplus_after = total_realized - verbrauch_plot
			fig.add_trace(
				go.Scatter(
					x=surplus_after.index,
					y=surplus_after.values,
					name="Überschuss (nach Abregelung)",
					mode="lines",
					line=dict(color="red", width=2),
					hovertemplate="%{y:,.0f} MW<extra>Überschuss nach</extra>",
					visible=is_visible,
					legendgroup=f"surplus_after_{res_idx}",
					showlegend=show_in_legend,
				)
			)

			# Optional: Überschuss VOR Abregelung (max verfügbar - demand)
			if has_surplus_before:
				df_prognose_resampled = resample_dataframe(df_prognose, res_name)
				prognose_cols = [c for c in df_prognose.columns if c in cols]
				max_available_total = df_prognose_resampled[prognose_cols].sum(axis=1)
				max_available_aligned = max_available_total.reindex(
					df_resampled.index, method="ffill"
				)
				surplus_before = max_available_aligned - verbrauch_plot

				fig.add_trace(
					go.Scatter(
						x=surplus_before.index,
						y=surplus_before.values,
						name="Überschuss (vor Abregelung)",
						mode="lines",
						line=dict(color="darkred", width=1, dash="dot"),
						hovertemplate="%{y:,.0f} MW<extra>Überschuss vor</extra>",
						visible=is_visible,
						legendgroup=f"surplus_before_{res_idx}",
						showlegend=show_in_legend,
					)
				)

	add_vertical_markers(fig, smard_end, dp_times)

	fig.update_layout(
		title=f"Realisierte Erzeugung nach Stack-Modell (Auflösung: {resolution})",
		xaxis_title="Zeit",
		yaxis_title="Leistung [MW]",
		**COMMON_LAYOUT,
	)

	# Trace-Zählung pro Resolution:
	traces_per_resolution = (
		num_generators
		+ 1  # total realized
		+ (1 if has_demand else 0)
		+ (1 if has_surplus_after else 0)
		+ (1 if has_surplus_before else 0)
	)

	buttons = []
	for res_idx, res_name in enumerate(resolution_list):
		visibility = []
		showlegend_list = []
		for r_idx in range(num_resolutions):
			for _ in range(traces_per_resolution):
				visibility.append(r_idx == res_idx)
				showlegend_list.append(r_idx == res_idx)

		buttons.append(
			dict(
				label=res_name,
				method="update",
				args=[
					{"visible": visibility, "showlegend": showlegend_list},
					{
						"title.text": f"Realisierte Erzeugung nach Stack-Modell (Auflösung: {res_name})"
					},
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
				active=resolution_list.index(resolution),
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


def create_surplus_plot(
	df_prognose: pd.DataFrame,
	ausbaupfad: Ausbaupfad,
	smard_end,
	dp_times: List,
	resolution: str,
) -> go.Figure:
	"""
	Überschuss/Unterdeckung VOR Abregelung: (max verfügbar - demand)
	"""
	fig = go.Figure()

	verbrauch_series = None
	if ausbaupfad.prognose_verbraucher:
		verbrauch_dr = ausbaupfad.prognose_verbraucher[0]
		verbrauch_series = verbrauch_dr.df.set_index("Datum von")[verbrauch_dr.art]

	if verbrauch_series is None:
		fig.add_annotation(
			text="Keine Verbrauchsdaten verfügbar",
			xref="paper",
			yref="paper",
			x=0.5,
			y=0.5,
			showarrow=False,
		)
		return fig

	cols = sorted(df_prognose.columns)
	resolution_list = list(RESOLUTION_OPTIONS.keys())

	for res_idx, res_name in enumerate(resolution_list):
		df_resampled = resample_dataframe(df_prognose, res_name)
		verbrauch_resampled = resample_dataframe(pd.DataFrame({"v": verbrauch_series}), res_name)[
			"v"
		]

		common_index = df_resampled.index.intersection(verbrauch_resampled.index)
		df_aligned = df_resampled.loc[common_index]
		verbrauch_aligned = verbrauch_resampled.loc[common_index]

		max_available = df_aligned[cols].sum(axis=1)
		surplus = max_available - verbrauch_aligned

		surplus_pos = surplus.clip(lower=0)
		surplus_neg = surplus.clip(upper=0)

		is_visible = res_name == resolution
		show_in_legend = res_name == resolution

		fig.add_trace(
			go.Scatter(
				x=surplus_pos.index,
				y=surplus_pos.values,
				name="Überschuss (vor Abregelung)",
				mode="lines",
				fill="tozeroy",
				fillcolor="rgba(0, 200, 0, 0.3)",
				line=dict(color="green", width=1),
				hovertemplate="%{y:,.0f} MW<extra>Überschuss vor</extra>",
				visible=is_visible,
				legendgroup=f"surplus_pos_{res_idx}",
				showlegend=show_in_legend,
			)
		)

		fig.add_trace(
			go.Scatter(
				x=surplus_neg.index,
				y=surplus_neg.values,
				name="Unterdeckung (vor Abregelung)",
				mode="lines",
				fill="tozeroy",
				fillcolor="rgba(200, 0, 0, 0.3)",
				line=dict(color="red", width=1),
				hovertemplate="%{y:,.0f} MW<extra>Unterdeckung</extra>",
				visible=is_visible,
				legendgroup=f"surplus_neg_{res_idx}",
				showlegend=show_in_legend,
			)
		)

		fig.add_trace(
			go.Scatter(
				x=surplus.index,
				y=surplus.values,
				name="Netto (vor Abregelung)",
				mode="lines",
				line=dict(color="darkblue", width=2),
				hovertemplate="%{y:,.0f} MW<extra>Netto</extra>",
				visible=is_visible,
				legendgroup=f"surplus_line_{res_idx}",
				showlegend=show_in_legend,
			)
		)

	fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
	add_vertical_markers(fig, smard_end, dp_times)

	fig.update_layout(
		title=f"Überschuss / Unterdeckung VOR Abregelung (Auflösung: {resolution})",
		xaxis_title="Zeit",
		yaxis_title="Leistung [MW]",
		**COMMON_LAYOUT,
	)

	traces_per_resolution = 3
	buttons = []
	for res_idx, res_name in enumerate(resolution_list):
		visibility = []
		showlegend_list = []
		for r_idx in range(len(resolution_list)):
			for _ in range(traces_per_resolution):
				visibility.append(r_idx == res_idx)
				showlegend_list.append(r_idx == res_idx)

		buttons.append(
			dict(
				label=res_name,
				method="update",
				args=[
					{"visible": visibility, "showlegend": showlegend_list},
					{
						"title.text": f"Überschuss / Unterdeckung VOR Abregelung (Auflösung: {res_name})"
					},
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
				active=resolution_list.index(resolution),
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


def create_single_generator_plot(
	df_prognose: pd.DataFrame,
	df_realisiert: pd.DataFrame,
	art: ErzeugerArt,
	ausbaupfad: Ausbaupfad,
	smard_end,
	dp_times: List,
	resolution: str,
) -> go.Figure:
	"""
	Vergleich Prognose vs Realisiert für einen einzelnen Generator.
	"""
	fig = go.Figure()

	if art not in df_prognose.columns or art not in df_realisiert.columns:
		fig.add_annotation(
			text=f"Keine Daten für {art} verfügbar",
			xref="paper",
			yref="paper",
			x=0.5,
			y=0.5,
			showarrow=False,
		)
		return fig

	resolution_list = list(RESOLUTION_OPTIONS.keys())
	num_resolutions = len(resolution_list)

	for res_idx, res_name in enumerate(resolution_list):
		df_prognose_resampled = resample_dataframe(df_prognose, res_name)
		df_realisiert_resampled = resample_dataframe(df_realisiert, res_name)

		is_visible = res_name == resolution
		show_in_legend = res_name == resolution

		# Prognose (max verfügbar)
		fig.add_trace(
			go.Scatter(
				x=df_prognose_resampled.index,
				y=df_prognose_resampled[art],
				name="Prognose (max. verfügbar)",
				mode="lines",
				line=dict(color="blue", width=2, dash="dash"),
				hovertemplate="%{y:,.0f} MW<extra>Prognose</extra>",
				visible=is_visible,
				legendgroup=f"prognose_{res_idx}",
				showlegend=show_in_legend,
			)
		)

		# Realisiert
		fig.add_trace(
			go.Scatter(
				x=df_realisiert_resampled.index,
				y=df_realisiert_resampled[art],
				name="Realisiert",
				mode="lines",
				line=dict(color="green", width=2),
				hovertemplate="%{y:,.0f} MW<extra>Realisiert</extra>",
				visible=is_visible,
				legendgroup=f"realisiert_{res_idx}",
				showlegend=show_in_legend,
			)
		)

		# Abregelung (Differenz)
		curtailment = df_prognose_resampled[art] - df_realisiert_resampled[art]
		curtailment[curtailment < 0] = 0

		fig.add_trace(
			go.Scatter(
				x=curtailment.index,
				y=curtailment.values,
				name="Abregelung",
				mode="lines",
				line=dict(width=0),
				fill="tozeroy",
				fillcolor="rgba(255,0,0,0.3)",
				hovertemplate="%{y:,.0f} MW<extra>Abregelung</extra>",
				visible=is_visible,
				legendgroup=f"curtailment_{res_idx}",
				showlegend=show_in_legend,
			)
		)

	add_vertical_markers(fig, smard_end, dp_times)

	art_name = str(art.value) if hasattr(art, "value") else str(art)
	fig.update_layout(
		title=f"{art_name}: Prognose vs Realisiert (Auflösung: {resolution})",
		xaxis_title="Zeit",
		yaxis_title="Leistung [MW]",
		**COMMON_LAYOUT,
	)

	# Resolution buttons
	traces_per_resolution = 3
	buttons = []
	for res_idx, res_name in enumerate(resolution_list):
		visibility = []
		showlegend_list = []
		for r_idx in range(num_resolutions):
			for t_idx in range(traces_per_resolution):
				visibility.append(r_idx == res_idx)
				showlegend_list.append(r_idx == res_idx)

		buttons.append(
			dict(
				label=res_name,
				method="update",
				args=[
					{"visible": visibility, "showlegend": showlegend_list},
					{"title.text": f"{art_name}: Prognose vs Realisiert (Auflösung: {res_name})"},
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
				active=resolution_list.index(resolution),
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


def create_curtailment_plot(
	df_prognose: pd.DataFrame,
	df_realisiert: pd.DataFrame,
	ausbaupfad: Ausbaupfad,
	smard_end,
	dp_times: List,
	resolution: str,
) -> go.Figure:
	"""
	Abregelung / Curtailment: Differenz zwischen max verfügbar und realisiert.
	"""
	fig = go.Figure()

	cols = sorted(df_prognose.columns)
	resolution_list = list(RESOLUTION_OPTIONS.keys())
	num_resolutions = len(resolution_list)

	for res_idx, res_name in enumerate(resolution_list):
		df_prognose_resampled = resample_dataframe(df_prognose, res_name)
		df_realisiert_resampled = resample_dataframe(df_realisiert, res_name)

		is_visible = res_name == resolution
		show_in_legend = res_name == resolution

		# Gesamte Abregelung
		total_max_available = df_prognose_resampled[cols].sum(axis=1)
		total_realized = df_realisiert_resampled[cols].sum(axis=1)
		total_curtailment = total_max_available - total_realized
		total_curtailment[total_curtailment < 0] = 0

		# Max verfügbar Linie
		fig.add_trace(
			go.Scatter(
				x=total_max_available.index,
				y=total_max_available.values,
				name="Max. verfügbar (Prognose)",
				mode="lines",
				line=dict(color="blue", width=2),
				hovertemplate="%{y:,.0f} MW<extra>Max. verfügbar</extra>",
				visible=is_visible,
				legendgroup=f"max_avail_{res_idx}",
				showlegend=show_in_legend,
			)
		)

		# Realisiert Linie
		fig.add_trace(
			go.Scatter(
				x=total_realized.index,
				y=total_realized.values,
				name="Realisiert (Stack-Modell)",
				mode="lines",
				line=dict(color="green", width=2),
				hovertemplate="%{y:,.0f} MW<extra>Realisiert</extra>",
				visible=is_visible,
				legendgroup=f"realized_{res_idx}",
				showlegend=show_in_legend,
			)
		)

		# Abregelung Fläche
		fig.add_trace(
			go.Scatter(
				x=total_curtailment.index,
				y=total_curtailment.values,
				name="Abregelung (Curtailment)",
				mode="lines",
				line=dict(width=0),
				fill="tozeroy",
				fillcolor="rgba(255,0,0,0.3)",
				hovertemplate="%{y:,.0f} MW<extra>Abregelung</extra>",
				visible=is_visible,
				legendgroup=f"curtailment_area_{res_idx}",
				showlegend=show_in_legend,
			)
		)

		# Abregelung Linie
		fig.add_trace(
			go.Scatter(
				x=total_curtailment.index,
				y=total_curtailment.values,
				name="Abregelung (MW)",
				mode="lines",
				line=dict(color="red", width=2, dash="dot"),
				hovertemplate="%{y:,.0f} MW<extra>Abregelung</extra>",
				visible=is_visible,
				legendgroup=f"curtailment_line_{res_idx}",
				showlegend=show_in_legend,
			)
		)

	add_vertical_markers(fig, smard_end, dp_times)

	fig.update_layout(
		title=f"Abregelung / Curtailment (Auflösung: {resolution})",
		xaxis_title="Zeit",
		yaxis_title="Leistung [MW]",
		**COMMON_LAYOUT,
	)

	# Resolution buttons
	traces_per_resolution = 4
	buttons = []
	for res_idx, res_name in enumerate(resolution_list):
		visibility = []
		showlegend_list = []
		for r_idx in range(num_resolutions):
			for t_idx in range(traces_per_resolution):
				visibility.append(r_idx == res_idx)
				showlegend_list.append(r_idx == res_idx)

		buttons.append(
			dict(
				label=res_name,
				method="update",
				args=[
					{"visible": visibility, "showlegend": showlegend_list},
					{"title.text": f"Abregelung / Curtailment (Auflösung: {res_name})"},
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
				active=resolution_list.index(resolution),
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


def create_comparison_stackplot(
	df_prognose: pd.DataFrame,
	df_realisiert: pd.DataFrame,
	ausbaupfad: Ausbaupfad,
	smard_end,
	dp_times: List,
	resolution: str,
) -> go.Figure:
	"""
	Vergleich: Max. verfügbar vs. Realisiert vs. Verbrauch.
	"""
	fig = go.Figure()

	cols = sorted(df_prognose.columns)
	color_map = get_color_map(cols)

	verbrauch_series = None
	if ausbaupfad.prognose_verbraucher:
		verbrauch_dr = ausbaupfad.prognose_verbraucher[0]
		verbrauch_series = verbrauch_dr.df.set_index("Datum von")[verbrauch_dr.art]

	resolution_list = list(RESOLUTION_OPTIONS.keys())
	num_resolutions = len(resolution_list)
	num_generators = len(cols)

	for res_idx, res_name in enumerate(resolution_list):
		df_prognose_resampled = resample_dataframe(df_prognose, res_name)
		df_realisiert_resampled = resample_dataframe(df_realisiert, res_name)

		is_visible = res_name == resolution
		show_in_legend = res_name == resolution

		# Max verfügbar (Prognose) - gestapelt, halbtransparent
		for col in cols:
			col_name = str(col.value) if hasattr(col, "value") else str(col)
			fig.add_trace(
				go.Scatter(
					x=df_prognose_resampled.index,
					y=df_prognose_resampled[col],
					name=f"Max. verfügbar: {col_name}",
					mode="lines",
					stackgroup=f"max_avail_{res_idx}",
					fillcolor=color_map[col].replace("1)", "0.5)"),
					line=dict(width=0.5, color=color_map[col].replace("1)", "0.5)")),
					hovertemplate="%{y:,.0f} MW<extra>Max. verfügbar: %{fullData.name}</extra>",
					visible=is_visible,
					legendgroup=f"max_avail_{col}_{res_idx}",
					showlegend=show_in_legend,
				)
			)

		# Gesamterzeugung realisiert (Linie)
		total_realized = df_realisiert_resampled[cols].sum(axis=1)
		fig.add_trace(
			go.Scatter(
				x=total_realized.index,
				y=total_realized.values,
				name="Gesamterzeugung (Realisiert)",
				mode="lines",
				line=dict(color="orange", width=3, dash="dot"),
				hovertemplate="%{y:,.0f} MW<extra>Gesamterzeugung (Realisiert)</extra>",
				visible=is_visible,
				legendgroup=f"total_realized_{res_idx}",
				showlegend=show_in_legend,
			)
		)

		# Verbrauch (Linie)
		if verbrauch_series is not None:
			verbrauch_resampled = resample_dataframe(
				pd.DataFrame({"v": verbrauch_series}), res_name
			)["v"]
			verbrauch_plot = verbrauch_resampled.reindex(
				df_prognose_resampled.index, method="ffill"
			)

			fig.add_trace(
				go.Scatter(
					x=verbrauch_plot.index,
					y=verbrauch_plot.values,
					name="Verbrauch/Bedarf",
					mode="lines",
					line=dict(color="black", width=2, dash="dash"),
					hovertemplate="%{y:,.0f} MW<extra>Verbrauch</extra>",
					visible=is_visible,
					legendgroup=f"demand_{res_idx}",
					showlegend=show_in_legend,
				)
			)

	add_vertical_markers(fig, smard_end, dp_times)

	fig.update_layout(
		title=f"Vergleich: Max. verfügbar vs. Realisiert vs. Verbrauch (Auflösung: {resolution})",
		xaxis_title="Zeit",
		yaxis_title="Leistung [MW]",
		**COMMON_LAYOUT,
	)

	# Resolution buttons
	traces_per_resolution = num_generators + 1 + (1 if verbrauch_series is not None else 0)
	buttons = []
	for res_idx, res_name in enumerate(resolution_list):
		visibility = []
		showlegend_list = []
		for r_idx in range(num_resolutions):
			for t_idx in range(traces_per_resolution):
				visibility.append(r_idx == res_idx)
				showlegend_list.append(r_idx == res_idx)

		buttons.append(
			dict(
				label=res_name,
				method="update",
				args=[
					{"visible": visibility, "showlegend": showlegend_list},
					{
						"title.text": f"Vergleich: Max. verfügbar vs. Realisiert vs. Verbrauch (Auflösung: {res_name})"
					},
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
				active=resolution_list.index(resolution),
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


def create_co2_plot(
	co2_df: pd.DataFrame,
	smard_end,
	dp_times: List,
	resolution: str,
) -> go.Figure:
	"""
	Create a CO2 emissions plot showing emissions per producer and total.

	Shows a stacked area chart with CO2 emissions for each producer type,
	plus a line showing total CO2 emissions over time.

	Args:
		co2_df: DataFrame with CO2 emissions per producer (columns) in tonnes
		smard_end: End date of SMARD historical data
		dp_times: List of scenario data point timestamps
		resolution: Default resolution for the plot

	Returns:
		Plotly Figure with CO2 emissions visualization
	"""
	fig = go.Figure()

	# Get columns (ErzeugerArt types) - filter out those with zero emissions
	all_cols = [col for col in co2_df.columns if isinstance(col, ErzeugerArt)]

	# Only include producers that have non-zero CO2 emissions
	cols = []
	for col in all_cols:
		total_co2 = co2_df[col].sum()
		if total_co2 > 0:
			cols.append(col)

	# Sort columns for consistent ordering
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

		is_visible = res_name == resolution
		show_in_legend = res_name == resolution

		# Stacked area for each producer
		for col in cols:
			col_name = str(col.value) if hasattr(col, "value") else str(col)
			fig.add_trace(
				go.Scatter(
					x=df_resampled.index,
					y=df_resampled[col],
					name=col_name,
					mode="lines",
					stackgroup=f"co2_{res_idx}",
					fillcolor=color_map[col],
					line=dict(width=0.5, color=color_map[col]),
					hovertemplate="%{y:,.2f} t CO2<extra>%{fullData.name}</extra>",
					visible=is_visible,
					legendgroup=f"{col}_{res_idx}",
					showlegend=show_in_legend,
				)
			)

		# Total CO2 line
		total_co2 = df_resampled[cols].sum(axis=1)
		fig.add_trace(
			go.Scatter(
				x=total_co2.index,
				y=total_co2.values,
				name="Gesamt CO2",
				mode="lines",
				line=dict(color="black", width=3),
				hovertemplate="%{y:,.2f} t CO2<extra>Gesamt</extra>",
				visible=is_visible,
				legendgroup=f"total_co2_{res_idx}",
				showlegend=show_in_legend,
			)
		)

	add_vertical_markers(fig, smard_end, dp_times)

	fig.update_layout(
		title=f"CO2-Emissionen nach Erzeuger (Auflösung: {resolution})",
		xaxis_title="Zeit",
		yaxis_title="CO2-Emissionen [Tonnen]",
		**COMMON_LAYOUT,
	)

	# Resolution dropdown buttons
	traces_per_resolution = num_producers + 1  # producers + total line
	buttons = []

	for res_idx, res_name in enumerate(resolution_list):
		visibility = []
		showlegend_list = []
		for r_idx in range(num_resolutions):
			for _ in range(traces_per_resolution):
				visibility.append(r_idx == res_idx)
				showlegend_list.append(r_idx == res_idx)

		buttons.append(
			dict(
				label=res_name,
				method="update",
				args=[
					{"visible": visibility, "showlegend": showlegend_list},
					{"title.text": f"CO2-Emissionen nach Erzeuger (Auflösung: {res_name})"},
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
				active=resolution_list.index(resolution),
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
