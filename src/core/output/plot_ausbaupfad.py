"""
Plot 1: Ausbaupfadübersicht.

This plot answers the question: "What is the scenario input?"
- Installed capacity targets per generator type (ErzeugerArt)
- Consumption targets per consumer type (VerbraucherArt)
- Markers: end of SMARD history + scenario milestone dates
"""

from __future__ import annotations

from datetime import timedelta

from plotly.graph_objects import Figure, Scatter
from plotly.subplots import make_subplots

from core.output.plot_common import (
	COMMON_LAYOUT,
	add_vertical_markers,
	collect_milestone_times,
	get_color,
	get_smard_end,
)
from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard
from core.setup.verbraucher import VerbraucherArt


def build_ausbaupfad_uebersicht_plot(ausbaupfad: Ausbaupfad, smard: Smard) -> Figure:
	"""
	Build the Ausbaupfad overview plot.

	Args:
		ausbaupfad: Processed expansion path (contains .installiert/.verbraucht).
		smard: SMARD data source (baseline values).

	Returns:
		Plotly Figure (subplots: installed capacity and demand targets).
	"""
	fig = make_subplots(
		rows=2,
		cols=1,
		shared_xaxes=True,
		vertical_spacing=0.12,
		subplot_titles=("Installierte Leistung (Ziele)", "Verbrauch / Bedarf (Ziele)"),
	)

	smard_end = get_smard_end(smard)
	milestone_times = collect_milestone_times(ausbaupfad)

	_plot_installed_capacity(fig=fig, ausbaupfad=ausbaupfad, smard=smard, smard_end=smard_end, milestone_times=milestone_times)
	_plot_consumption_targets(fig=fig, ausbaupfad=ausbaupfad, smard=smard, smard_end=smard_end, milestone_times=milestone_times)

	add_vertical_markers(fig, smard_end=smard_end, milestone_times=milestone_times, rows=2)

	fig.update_xaxes(title_text="Zeit", row=2, col=1)
	fig.update_yaxes(title_text="Leistung [MW]", row=1, col=1)
	fig.update_yaxes(title_text="Leistung [MW]", row=2, col=1)

	fig.update_layout(
		title=f"Ausbaupfadübersicht: {ausbaupfad.name}",
		**COMMON_LAYOUT,
	)

	return fig


def _plot_installed_capacity(
	fig: Figure,
	ausbaupfad: Ausbaupfad,
	smard: Smard,
	smard_end,
	milestone_times,
) -> None:
	"""
	Add installed-capacity traces (targets) to the top subplot.
	"""
	plot_start = smard_end - timedelta(days=365)
	plot_end = smard_end + timedelta(days=365 * 5)
	if milestone_times:
		plot_end = max(milestone_times)

	for art in ErzeugerArt:
		try:
			erz = smard.get_erzeuger(art)
			last_time = erz.installiert.df["Datum von"].iloc[-1]
			last_val = float(erz.installiert.werte.iloc[-1])
		except Exception:
			continue

		# All scenario target points for this generator type
		points = ausbaupfad.get_erzeuger(art)
		points.sort(key=lambda p: p.datum)

		x_points = [last_time]
		y_points = [last_val]

		for p in points:
			x_points.append(p.datum)
			y_points.append(float(p.wert))

		# If there are no targets, draw a constant baseline line for context.
		if len(x_points) == 1:
			x_points = [plot_start, plot_end]
			y_points = [last_val, last_val]

		fig.add_trace(
			Scatter(
				x=x_points,
				y=y_points,
				name=str(art.value) if hasattr(art, "value") else str(art),
				mode="lines+markers" if len(points) > 0 else "lines",
				line=dict(color=get_color(art), width=2),
				marker=dict(size=7),
				hovertemplate="%{y:,.0f} MW<extra>%{fullData.name}</extra>",
			),
			row=1,
			col=1,
		)


def _plot_consumption_targets(
	fig: Figure,
	ausbaupfad: Ausbaupfad,
	smard: Smard,
	smard_end,
	milestone_times,
) -> None:
	"""
	Add consumption target traces to the bottom subplot.
	"""
	# Which consumer types exist in the scenario?
	consumer_types: list[VerbraucherArt] = []
	seen: set[VerbraucherArt] = set()

	if hasattr(ausbaupfad, "verbraucht"):
		for v in ausbaupfad.verbraucht:
			if v.art not in seen:
				seen.add(v.art)
				consumer_types.append(v.art)

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
			# Use mean as baseline (same baseline concept used in prognosis creation)
			baseline_val = float(hist_df[art].mean())
		except Exception:
			continue

		points = []
		for p in ausbaupfad.verbraucht:
			if p.art == art:
				points.append(p)
		points.sort(key=lambda p: p.datum)

		x_points = [last_time]
		y_points = [baseline_val]
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

