from core.setup.erzeuger import ErzeugerArt
from core.simulation.parameter import ParamName


class ProducerWeights:
	"""Defines how each producer is connected to simulation parameters."""

	def __init__(self, weights: dict[ParamName, float]) -> None:
		"""Initialize producer weights.

		Args:
			weights: Mapping from parameter names to weight values.
				  Weight values indicate the strength of connection (typically 0.0 to 1.0).
		"""
		self.weights = weights

	def get_weight(self, param: ParamName) -> float:
		"""Get the weight for a given parameter."""
		return self.weights.get(param, 0.0)


# Predefined weights for each producer type
PRODUCER_WEIGHTS: dict[ErzeugerArt, ProducerWeights] = {
	ErzeugerArt.Photovoltaik: ProducerWeights(
		{
			ParamName.temp: 0.6,  # High temp slightly reduces efficiency but increases energy
			ParamName.sun: 1.0,  # Very high dependency on sun
			ParamName.rainfall: 0.0,  # No dependency on rainfall
			ParamName.wind: 0.0,  # No dependency on wind
		}
	),
	ErzeugerArt.WindOffshore: ProducerWeights(
		{
			ParamName.temp: 0.0,
			ParamName.sun: 0.0,
			ParamName.rainfall: 0.0,
			ParamName.wind: 1.0,  # High dependency on wind
		}
	),
	ErzeugerArt.WindOnshore: ProducerWeights(
		{
			ParamName.temp: 0.0,
			ParamName.sun: 0.0,
			ParamName.rainfall: 0.0,
			ParamName.wind: 1.0,  # High dependency on wind
		}
	),
	ErzeugerArt.Wasserkraft: ProducerWeights(
		{
			ParamName.temp: 0.3,  # Higher temp can reduce water availability
			ParamName.sun: 0.0,
			ParamName.rainfall: 0.8,  # High dependency on rainfall
			ParamName.wind: 0.0,
		}
	),
	ErzeugerArt.Biomasse: ProducerWeights(
		{
			ParamName.temp: 0.4,
			ParamName.sun: 0.5,
			ParamName.rainfall: 0.6,
			ParamName.wind: 0.1,
		}
	),
	ErzeugerArt.Pumpspeicher: ProducerWeights(
		{
			ParamName.temp: 0.2,
			ParamName.sun: 0.0,
			ParamName.rainfall: 0.5,  # Some dependency on water availability
			ParamName.wind: 0.0,
		}
	),
	ErzeugerArt.SonstigeErneuerbare: ProducerWeights(
		{
			ParamName.temp: 0.3,
			ParamName.sun: 0.4,
			ParamName.rainfall: 0.3,
			ParamName.wind: 0.3,
		}
	),
	# Conventional energy sources are less affected by weather
	ErzeugerArt.Braunkohle: ProducerWeights(
		{
			ParamName.temp: 0.1,  # Cooling water availability
			ParamName.sun: 0.0,
			ParamName.rainfall: 0.1,
			ParamName.wind: 0.0,
		}
	),
	ErzeugerArt.Steinkohle: ProducerWeights(
		{
			ParamName.temp: 0.1,
			ParamName.sun: 0.0,
			ParamName.rainfall: 0.1,
			ParamName.wind: 0.0,
		}
	),
	ErzeugerArt.Erdgas: ProducerWeights(
		{
			ParamName.temp: 0.1,
			ParamName.sun: 0.0,
			ParamName.rainfall: 0.1,
			ParamName.wind: 0.0,
		}
	),
	ErzeugerArt.Kernenergie: ProducerWeights(
		{
			ParamName.temp: 0.2,  # Cooling water availability
			ParamName.sun: 0.0,
			ParamName.rainfall: 0.2,
			ParamName.wind: 0.0,
		}
	),
	ErzeugerArt.SonstigeKonventionelle: ProducerWeights(
		{
			ParamName.temp: 0.1,
			ParamName.sun: 0.0,
			ParamName.rainfall: 0.1,
			ParamName.wind: 0.0,
		}
	),
}


def get_producer_weights(producer_type: ErzeugerArt) -> ProducerWeights:
	"""Get the parameter weights for a given producer type."""
	return PRODUCER_WEIGHTS.get(
		producer_type,
		ProducerWeights({}),  # Default: no weights
	)
