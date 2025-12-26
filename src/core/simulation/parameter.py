import enum


class ParamName(enum.StrEnum):
	"""Names of simulation parameters."""

	temp = "temp"
	sun = "sun"
	rainfall = "rainfall"
	wind = "wind"


class ParamLevel(enum.IntEnum):
	"""Discrete levels for simulation parameters.

	Higher values typically mean more of the parameter (more temp, more sun, etc.).
	For rainfall and wind, higher values mean more precipitation/wind.
	"""

	none = 0
	low = 1
	okay = 2
	medium = 3
	high = 4
