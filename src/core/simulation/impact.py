from core.simulation.event import SimulationEvent
from core.simulation.parameter import ParamLevel, ParamName
from core.simulation.producer_weights import get_producer_weights
from core.types import ErzeugerArt


def _get_parameter_impact(param_name: ParamName, param_level: ParamLevel) -> float:
	"""Get the impact value for a parameter level.

	Returns a value between 0.0 and 1.0 representing the impact.
	For most parameters: higher level = higher impact (better conditions).
	For temp with PV: very high temp can slightly reduce efficiency.

	Args:
		param_name: The parameter name
		param_level: The discrete level of the parameter

	Returns:
		Normalized impact value (0.0 to 1.0)
	"""
	# Convert level to normalized value
	level_value = param_level.value / ParamLevel.high.value

	# For temperature: very high temps (>0.75) can reduce efficiency
	if param_name == ParamName.temp:
		if level_value > 0.75:
			# Slight efficiency reduction at very high temps
			level_value = 0.75 + (level_value - 0.75) * 0.5

	return level_value


def calculate_impact_factor(
	event: SimulationEvent,
	producer_type: ErzeugerArt,
) -> float:
	"""Calculate the impact factor for a producer based on an event.

	The impact factor is multiplied with the generated energy to get the
	realized energy after the event.

	Args:
		event: The simulation event affecting production
		producer_type: The type of energy producer

	Returns:
		Impact factor (typically between 0.0 and 2.0, where 1.0 means no change)
	"""
	weights = get_producer_weights(producer_type)

	# Calculate weighted parameter impact for each parameter
	weighted_impact_sum = 0.0
	weight_sum = 0.0

	for param_name in ParamName:
		weight = weights.get_weight(param_name)
		if weight == 0.0:
			continue  # Skip parameters that don't affect this producer

		event_level = event.get_param_value(param_name)

		# Get normalized impact value for this parameter level
		level_impact = _get_parameter_impact(param_name, event_level)

		# Baseline is 'okay' level (0.5)
		baseline_impact = 0.5

		# Calculate relative impact: how much better/worse than baseline
		# Value ranges from -0.5 (none) to +0.5 (high), centered at 0 (okay)
		relative_impact = level_impact - baseline_impact

		# Weight the impact by the producer's connection strength
		weighted_impact = relative_impact * weight
		weighted_impact_sum += weighted_impact
		weight_sum += weight

	# If no parameters affect this producer, no change
	if weight_sum == 0.0:
		return 1.0

	# Average the weighted impact
	# This gives us a value roughly between -0.5 and +0.5
	average_impact = weighted_impact_sum / weight_sum

	# Apply intensity scaling (allows partial event strength)
	scaled_impact = average_impact * event.intensity

	# Convert to multiplicative factor
	# scaled_impact ranges roughly from -0.5 to +0.5
	# So factor ranges from 0.5 to 1.5 (with intensity=1.0)
	# We allow a wider range: 0.0 to 2.0
	impact_factor = 1.0 + (scaled_impact * 2.0)

	# Clamp to reasonable bounds (0.0 to 2.0)
	return max(0.0, min(2.0, impact_factor))
