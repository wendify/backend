import logging

from pandas import DataFrame

from core.output import ausbau, co2, stack
from core.prognose.ausbaupfad import Ausbaupfad
from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt
from core.setup.smard import Smard


# Öffnet alle Plots im Browser, jeweils in einem Tab
def show_all(
	ausbaupfad: Ausbaupfad,
	realisiert: dict[ErzeugerArt, Datenreihe[ErzeugerArt]],
	co2_df: DataFrame,
	smard: Smard,
) -> None:
	# Plot 1
	logging.info("Plot 1 wird geöffnet: Übersicht Ausbaupfad")

	fig_ausbau = ausbau.build_plot(ausbaupfad, smard)
	fig_ausbau.show()

	# Plot 2
	logging.info("Plot 2 wird geöffnet: Stack-Modell")

	fig_stack = stack.build_plot(ausbaupfad, realisiert, smard)
	fig_stack.show()

	# Plot 3
	logging.info("Plot 3 wird geöffnet: CO2-Verbrauch")

	fig_co2 = co2.build_plot(ausbaupfad, co2_df, smard)
	fig_co2.show()
