from datetime import datetime, timedelta

from plotly.graph_objects import Figure, Scatter
from plotly.subplots import make_subplots

from core.output import common
from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard


# Baut Plot 1: Übersicht Ausbaupfad
def build_plot(ausbaupfad: Ausbaupfad, smard: Smard) -> Figure:
	fig = make_subplots(
		rows=2,
		cols=1,
		shared_xaxes=True,
		vertical_spacing=0.12,
		subplot_titles=("Installierte Leistung (Ziele)", "Verbrauch / Bedarf (Ziele)"),
	)

	smard_end = common.get_smard_end(smard)
	milestone_times = common.collect_milestone_times(ausbaupfad)

	_plot_installed_capacity(fig, ausbaupfad, smard, smard_end, milestone_times)
	_plot_consumption_targets(fig, ausbaupfad, smard)

	common.add_vertical_markers(fig, smard_end=smard_end, milestone_times=milestone_times, rows=2)

	# Achsenbeschriftungen
	fig.update_xaxes(title_text="Zeit", row=2, col=1)
	fig.update_yaxes(title_text="Leistung [MW]", row=1, col=1)
	fig.update_yaxes(title_text="Energie [MWh]", row=2, col=1)

	fig.update_layout(title=f"Ausbaupfadübersicht: {ausbaupfad.name}", **common.COMMON_LAYOUT)
	return fig


# Baut Subplot 1: Übersicht Installationen
def _plot_installed_capacity(
	fig: Figure,
	ausbaupfad: Ausbaupfad,
	smard: Smard,
	smard_end: datetime,
	milestone_times: list[datetime],
) -> None:
	plot_start = smard_end - timedelta(days=365)
	plot_end = max(milestone_times) if milestone_times else smard_end + timedelta(days=365 * 5)

	for art in ErzeugerArt:
		try:
			erz = smard.get_erzeuger(art)
			last_time = erz.installiert.df["Datum von"].iloc[-1]
			last_val = float(erz.installiert.werte.iloc[-1])
		except Exception:
			continue

		# Alle Szenario-Zielpunkte für diesen Erzeuger
		points = sorted(ausbaupfad.get_erzeuger(art), key=lambda p: p.datum)
		x_points, y_points = [last_time], [last_val]

		for p in points:
			x_points.append(p.datum)
			y_points.append(float(p.wert))

		# Falls keine Zielpunkte vorhanden, konstante Linie zeichnen
		if len(x_points) == 1:
			x_points, y_points = [plot_start, plot_end], [last_val, last_val]

		fig.add_trace(
			Scatter(
				x=x_points,
				y=y_points,
				name=str(art.value) if hasattr(art, "value") else str(art),
				mode="lines+markers" if points else "lines",
				line=dict(color=common.GENERATOR_COLORS[art], width=2),
				marker=dict(size=7),
				hovertemplate="%{y:,.0f} MW<extra>%{fullData.name}</extra>",
			),
			row=1,
			col=1,
		)


# Baut Subplot 2: Übersicht Verbräuche
def _plot_consumption_targets(fig: Figure, ausbaupfad: Ausbaupfad, smard: Smard) -> None:
	# Verbraucher-Typen im Szenario ermitteln
	consumer_types = list({v.art for v in ausbaupfad.verbraucht})
	if not consumer_types:
		fig.add_annotation(
			text="Keine Verbrauchs-Zielpunkte vorhanden",
			xref="paper",
			yref="paper",
			x=0.5,
			y=0.18,
			showarrow=False,
		)
		return

	for art in consumer_types:
		try:
			verbraucher = smard.get_verbraucher(art)
			hist_df = verbraucher.verbraucht.df
			last_time = hist_df["Datum von"].iloc[-1]
			baseline_val = float(hist_df[art].mean())
		except Exception:
			continue

		# Zielpunkte für diesen Verbraucher sammeln
		points = sorted(
			[p for p in ausbaupfad.verbraucht if p.art == art],
			key=lambda p: p.datum,
		)
		x_points, y_points = [last_time], [baseline_val]

		for p in points:
			x_points.append(p.datum)
			y_points.append(float(p.wert))

		fig.add_trace(
			Scatter(
				x=x_points,
				y=y_points,
				name=str(art.value) if hasattr(art, "value") else str(art),
				mode="lines+markers",
				line=dict(color="black", width=2, dash="dash"),
				marker=dict(size=7),
				hovertemplate="%{y:,.0f} MW<extra>%{fullData.name}</extra>",
				showlegend=True,
			),
			row=2,
			col=1,
		)
