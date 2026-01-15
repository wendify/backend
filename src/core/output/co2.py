from pandas import DataFrame
from plotly.graph_objects import Figure, Scatter

from core.output import common
from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard


# Baut Plot 3: CO2-Verbrauch
def build_plot(
	ausbaupfad: Ausbaupfad,
	co2_df: DataFrame,
	smard: Smard,
	default_resolution: str = "1 Woche",
) -> Figure:
	fig = Figure()

	# Prüfen, ob CO2-Daten vorhanden sind
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

	# Nur ErzeugerArt-Spalten mit nicht-null Gesamtwerten behalten
	producer_cols = sorted(
		[col for col in co2_df.columns if isinstance(col, ErzeugerArt) and co2_df[col].sum() > 0.0],
		key=lambda x: str(x.value) if hasattr(x, "value") else str(x),
	)

	if not producer_cols:
		fig.add_annotation(
			text="Keine CO2-Emissionen (nur erneuerbare Erzeuger)",
			xref="paper",
			yref="paper",
			x=0.5,
			y=0.5,
			showarrow=False,
		)
		return fig

	resolution_list = list(common.RESOLUTION_OPTIONS.keys())
	traces_per_res = len(producer_cols) + 1

	# Erzeuger-Traces und Gesamt-CO2 erstellen
	for idx, res in enumerate(resolution_list):
		df_r = common.resample_dataframe(co2_df, res)
		visible = res == default_resolution

		for art in producer_cols:
			fig.add_trace(
				Scatter(
					x=df_r.index,
					y=df_r[art],
					name=str(art.value) if hasattr(art, "value") else str(art),
					mode="lines",
					stackgroup=f"co2_{idx}",
					fillcolor=common.hex_to_rgba(common.GENERATOR_COLORS[art], 0.75),
					line=dict(
						width=0.5, color=common.hex_to_rgba(common.GENERATOR_COLORS[art], 0.9)
					),
					hovertemplate="%{y:,.2f} t CO2<extra>%{fullData.name}</extra>",
					visible=visible,
					legendgroup=f"{art}_{idx}",
					showlegend=visible,
				)
			)

		total_co2 = df_r[producer_cols].sum(axis=1)
		fig.add_trace(
			Scatter(
				x=total_co2.index,
				y=total_co2.values,
				name="Gesamt CO2",
				mode="lines",
				line=dict(color="black", width=3),
				hovertemplate="%{y:,.2f} t CO2<extra>Gesamt</extra>",
				visible=visible,
				legendgroup=f"total_{idx}",
				showlegend=visible,
			)
		)

	# Meilensteine hinzufügen
	common.add_vertical_markers(
		fig,
		smard_end=common.get_smard_end(smard),
		milestone_times=common.collect_milestone_times(ausbaupfad),
		rows=1,
	)

	# Layout und Dropdown-Menü
	fig.update_layout(
		title=f"CO2-Emissionen (Auflösung: {default_resolution})",
		xaxis_title="Zeit",
		yaxis_title="CO2-Emissionen [t]",
		**common.COMMON_LAYOUT,
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
				buttons=[
					dict(
						label=res,
						method="update",
						args=[
							{
								"visible": [
									r == i
									for i in range(len(resolution_list))
									for _ in range(traces_per_res)
								],
								"showlegend": [
									r == i
									for i in range(len(resolution_list))
									for _ in range(traces_per_res)
								],
							},
							{"title.text": f"CO2-Emissionen (Auflösung: {res})"},
						],
					)
					for r, res in enumerate(resolution_list)
				],
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
