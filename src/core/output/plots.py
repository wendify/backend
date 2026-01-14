"""
Public plotting API for the simulation output.

This module intentionally stays small:
- It defines the stable entry point `show_all(...)`.
- It delegates all plot building to dedicated builder modules.

Each plot is a Plotly `Figure` that opens in the browser via `Figure.show()`.
"""

from pandas import DataFrame

from core.output.plot_ausbaupfad import build_ausbaupfad_uebersicht_plot
from core.output.plot_co2 import build_co2_plot
from core.output.plot_stackmodell import build_stackmodell_plot
from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard


def show_all(
	ausbaupfad: Ausbaupfad,
	realisiert_datenreihen: dict[ErzeugerArt, Datenreihe],
	smard: Smard,
	co2_df: DataFrame | None = None,
	default_resolution: str = "1 Woche",
) -> None:
	"""
	Open all output plots in the browser (one tab per plot).

	Args:
		ausbaupfad: Processed expansion path (already contains prognosis data).
		realisiert_datenreihen: Realized generation output from the stack model.
		smard: SMARD data source (historical baselines).
		co2_df: Optional CO2 emissions DataFrame (index: 'Datum von', columns: ErzeugerArt).
		default_resolution: Initial resolution used for plots with resolution dropdown.
	"""
	print("Öffne Plots im Browser...")

	fig_ausbau = build_ausbaupfad_uebersicht_plot(ausbaupfad=ausbaupfad, smard=smard)
	fig_ausbau.show()

	fig_stack = build_stackmodell_plot(
		ausbaupfad=ausbaupfad,
		realisiert_datenreihen=realisiert_datenreihen,
		smard=smard,
		default_resolution=default_resolution,
	)
	fig_stack.show()

	fig_co2 = build_co2_plot(
		co2_df=co2_df,
		ausbaupfad=ausbaupfad,
		smard=smard,
		default_resolution=default_resolution,
	)
	fig_co2.show()

