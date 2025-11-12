import enum

from core.simulation.parameter import ParamLevel, ParamName, ParamValue


class EventType(enum.StrEnum):
	"""Types of simulation events."""
	drought = "drought"


class SimulationEvent:
	"""Represents a simulation event with its parameter values."""
	
	def __init__(
		self,
		event_type: EventType,
		param_values: dict[ParamName, ParamValue],
		intensity: float = 1.0,
	) -> None:
		"""Initialize a simulation event.
		
		Args:
			event_type: The type of event (e.g., drought)
			param_values: Mapping from parameter names to their discrete levels
			intensity: Intensity/severity of the event (0.0 to 1.0, default 1.0)
		"""
		self.event_type = event_type
		self.param_values = param_values
		self.intensity = max(0.0, min(1.0, intensity))  # Clamp to [0, 1]
	
	def get_param_value(self, param: ParamName) -> ParamValue:
		"""Get the parameter value for a given parameter."""
		return self.param_values.get(param, ParamLevel.okay)


def create_event_from_type(event_type: EventType, intensity: float = 1.0) -> SimulationEvent:
	"""Create a simulation event based on event type with predefined parameter mappings.
	
	Args:
		event_type: The type of event
		intensity: Intensity of the event (0.0 to 1.0)
	
	Returns:
		SimulationEvent with appropriate parameter values
	"""
	event_configs: dict[EventType, dict[ParamName, ParamLevel]] = {
		EventType.drought: {
			ParamName.temp: ParamLevel.high,
			ParamName.sun: ParamLevel.high,
			ParamName.rainfall: ParamLevel.low,
			ParamName.wind: ParamLevel.low,
		},
	}
	
	base_params = event_configs.get(event_type, {})
	
	# Adjust parameter levels based on intensity
	adjusted_params: dict[ParamName, ParamValue] = {}
	for param_name, base_level in base_params.items():
		# Scale the level based on intensity
		# At intensity 0.0, move towards 'okay' (2)
		# At intensity 1.0, use the full base level
		if intensity < 1.0:
			okay_level = ParamLevel.okay
			adjusted_level_value = int(
				okay_level + (base_level - okay_level) * intensity
			)
			adjusted_params[param_name] = ParamLevel(
				max(ParamLevel.none, min(ParamLevel.high, adjusted_level_value))
			)
		else:
			adjusted_params[param_name] = base_level
	
	return SimulationEvent(event_type, adjusted_params, intensity)

