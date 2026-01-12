"""
CO2-Emissions Calculation Module.

This module calculates CO2 emissions for each energy producer based on
their realized generation (from the stack model) and their emission factors.
"""

from pandas import DataFrame

from core.setup.datenreihe import Datenreihe
from core.setup.erzeuger import ErzeugerArt


def calculate_co2_emissions(
	realisiert_datenreihen: dict[ErzeugerArt, Datenreihe],
) -> DataFrame:
	"""
	Calculate CO2 emissions for each producer based on realized generation.

	The calculation converts power (MW) to energy (MWh) using the time step
	duration, then multiplies by the CO2 emission factor (tonnes/MWh).

	Formula for each time step:
		CO2 [tonnes] = Power [MW] × Time_Step [hours] × CO2_Factor [t/MWh]

	Args:
		realisiert_datenreihen: Dictionary mapping ErzeugerArt to Datenreihe
			containing the realized generation in MW.

	Returns:
		DataFrame with:
			- Index: "Datum von" timestamps
			- Columns: One column per ErzeugerArt with CO2 emissions in tonnes
	"""
	if not realisiert_datenreihen:
		return DataFrame()

	# Get one Datenreihe to extract the time index
	first_datenreihe = next(iter(realisiert_datenreihen.values()))
	first_df = first_datenreihe.df

	# Use "Datum von" as index
	time_index = first_df["Datum von"]

	# Calculate time step duration in hours
	# Typically 15 minutes = 0.25 hours
	if len(time_index) >= 2:
		time_step_hours = (time_index.iloc[1] - time_index.iloc[0]).total_seconds() / 3600
	else:
		# Default to 15 minutes if we can't determine
		time_step_hours = 0.25

	# Create result DataFrame
	result_df = DataFrame()
	result_df["Datum von"] = time_index
	result_df = result_df.set_index("Datum von")

	# Calculate CO2 for each producer
	for art, datenreihe in realisiert_datenreihen.items():
		# Get the CO2 factor for this producer type
		co2_factor = art.emissionen

		# Get the realized power values (MW)
		power_mw = datenreihe.df[art].values

		# Calculate CO2 emissions: MW × hours × t/MWh = tonnes
		co2_tonnes = power_mw * time_step_hours * co2_factor

		# Add to result DataFrame
		result_df[art] = co2_tonnes

	return result_df
