from pandas import DataFrame, Series
from plotly.graph_objects import Figure, Scatter

from core.output import common
from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard
from core.setup.verbraucher import VerbraucherArt


# Baut Plot 2: Stack-Modell
def build_plot(
	ausbaupfad: Ausbaupfad,
	realisiert_datenreihen: dict[ErzeugerArt, Datenreihe[ErzeugerArt]],
	smard: Smard,
	default_resolution: str = "1 Woche",
) -> Figure:
	fig = Figure()

	# Realisierte Erzeugung in DataFrame konvertieren
	df_realisiert = common.merge_datenreihen_to_dataframe(list(realisiert_datenreihen.values()))
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
	verbrauch_series = _get_demand_series(ausbaupfad, smard)

	resolution_list = list(common.RESOLUTION_OPTIONS.keys())
	num_resolutions = len(resolution_list)
	num_generators = len(cols)

	for res_idx, res_name in enumerate(resolution_list):
		df_resampled = common.resample_dataframe(df_realisiert, res_name)
		visible = show_in_legend = res_name == default_resolution

		# Gestapelte reale Erzeugung
		for art in cols:
			fig.add_trace(
				Scatter(
					x=df_resampled.index,
					y=df_resampled[art],
					name=str(art.value) if hasattr(art, "value") else str(art),
					mode="lines",
					stackgroup=f"realized_{res_idx}",
					fillcolor=common.hex_to_rgba(common.GENERATOR_COLORS[art], 0.75),
					line=dict(
						width=0.5, color=common.hex_to_rgba(common.GENERATOR_COLORS[art], 0.9)
					),
					hovertemplate="%{y:,.0f} MW<extra>%{fullData.name}</extra>",
					visible=visible,
					legendgroup=f"{art}_{res_idx}",
					showlegend=show_in_legend,
				)
			)

		# Gesamt realisierte Erzeugung
		total_realized = df_resampled[cols].sum(axis=1)
		fig.add_trace(
			Scatter(
				x=total_realized.index,
				y=total_realized.values,
				name="Gesamterzeugung (realisiert)",
				mode="lines",
				line=dict(color="darkgray", width=3),
				hovertemplate="%{y:,.0f} MW<extra>Gesamt</extra>",
				visible=visible,
				legendgroup=f"total_{res_idx}",
				showlegend=show_in_legend,
			)
		)

		# Verbrauchs-/Bedarfsreihe
		if verbrauch_series is not None and not verbrauch_series.empty:
			demand_resampled = common.resample_dataframe(
				DataFrame({"d": verbrauch_series}), res_name
			)["d"]
			demand_plot = demand_resampled.reindex(df_resampled.index, method="ffill")

			fig.add_trace(
				Scatter(
					x=demand_plot.index,
					y=demand_plot.values,
					name="Verbrauch/Bedarf",
					mode="lines",
					line=dict(color="black", width=2, dash="dash"),
					hovertemplate="%{y:,.0f} MW<extra>Verbrauch</extra>",
					visible=visible,
					legendgroup=f"demand_{res_idx}",
					showlegend=show_in_legend,
				)
			)

	# Meilensteine hinzufügen
	smard_end = common.get_smard_end(smard)
	milestones = common.collect_milestone_times(ausbaupfad)
	common.add_vertical_markers(fig, smard_end=smard_end, milestone_times=milestones, rows=1)

	# Layout
	fig.update_layout(
		title=f"Stackmodell: Realisierte Erzeugung (Auflösung: {default_resolution})",
		xaxis_title="Zeit",
		yaxis_title="Energie [MWh]",
		**common.COMMON_LAYOUT,
	)

	# Dropdown-Menü für Auflösungen
	has_demand = verbrauch_series is not None and not verbrauch_series.empty
	traces_per_resolution = num_generators + 1 + (1 if has_demand else 0)

	buttons = [
		dict(
			label=res_name,
			method="update",
			args=[
				{
					"visible": [
						r_idx == res_idx
						for r_idx in range(num_resolutions)
						for _ in range(traces_per_resolution)
					],
					"showlegend": [
						r_idx == res_idx
						for r_idx in range(num_resolutions)
						for _ in range(traces_per_resolution)
					],
				},
				{"title.text": f"Stackmodell: Realisierte Erzeugung (Auflösung: {res_name})"},
			],
		)
		for res_idx, res_name in enumerate(resolution_list)
	]

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


# Holt die Verbraucherreihe für den Plot
def _get_demand_series(ausbaupfad: Ausbaupfad, smard: Smard) -> Series | None:
	verbrauch_dr = None

	# Prognoseverbraucher bevorzugt
	prognosen = ausbaupfad.prognose_verbraucher
	if prognosen:
		verbrauch_dr = next(
			(dr for dr in prognosen if dr.art == VerbraucherArt.Netzlast), prognosen[0]
		)

	# Falls keine Prognose, SMARD-Daten nutzen
	if verbrauch_dr is None:
		try:
			verbrauch_dr = smard.get_verbraucher(VerbraucherArt.Netzlast).verbraucht
		except Exception:
			return None

	series = verbrauch_dr.df.set_index("Datum von")[verbrauch_dr.art]
	if series.index.has_duplicates:
		series = series.groupby(level=0).mean()
	return series.sort_index()
