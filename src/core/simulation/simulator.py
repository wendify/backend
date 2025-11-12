import datetime

from core.datenreihe import Datenreihe
from core.simulation.event import EventType, SimulationEvent, create_event_from_type
from core.simulation.impact import apply_event_to_energy
from core.types import ErzeugerArt

import pandas


class Simulation:
	"""Applies simulation events to energy production data."""
	
	def __init__(self, event: SimulationEvent) -> None:
		"""Initialize a simulation with an event.
		
		Args:
			event: The simulation event to apply
		"""
		self.event = event
	
	@classmethod
	def create_drought(cls, intensity: float = 1.0) -> "Simulation":
		"""Create a drought simulation event.
		
		Args:
			intensity: Intensity of the drought (0.0 to 1.0)
		
		Returns:
			Simulation instance with drought event
		"""
		event = create_event_from_type(EventType.drought, intensity)
		return cls(event)
	
	def apply_to_datenreihe(
		self,
		datenreihe: Datenreihe,
		producer_type: ErzeugerArt,
	) -> Datenreihe:
		"""Apply the simulation event to a Datenreihe.
		
		Args:
			datenreihe: The original data series
			producer_type: The type of producer this data represents
		
		Returns:
			New Datenreihe with event impacts applied
		"""
		df_copy = datenreihe.df.copy()
		
		# Apply impact factor to each value in the series
		for idx in df_copy.index:
			base_energy = df_copy.loc[idx, producer_type]
			realized_energy = apply_event_to_energy(base_energy, self.event, producer_type)
			df_copy.loc[idx, producer_type] = realized_energy
		
		return Datenreihe(producer_type, df_copy)
	
	def apply_to_erzeuger(self, erzeuger: "Erzeuger") -> "Erzeuger":
		"""Apply the simulation event to an Erzeuger's realized energy.
		
		This creates a new Erzeuger with modified realized energy based on the event.
		
		Args:
			erzeuger: The original energy producer
		
		Returns:
			New Erzeuger with event impacts applied to realized energy
		"""
		from core.erzeuger import Erzeuger  # Avoid circular import
		
		# Apply event to realized energy
		modified_realisiert = self.apply_to_datenreihe(erzeuger.realisiert, erzeuger.art)
		
		# Create new Erzeuger with modified realized energy
		# The normiert will be recalculated automatically
		return Erzeuger(erzeuger.art, erzeuger.installiert, modified_realisiert)


def simulate_event(
	event_type: EventType,
	intensity: float = 1.0,
	erzeuger: "Erzeuger | None" = None,
	datenreihe: Datenreihe | None = None,
) -> Simulation:
	"""Create and optionally apply a simulation event.
	
	Args:
		event_type: Type of event to create
		intensity: Intensity of the event (0.0 to 1.0)
		erzeuger: Optional Erzeuger to apply the event to immediately
		datenreihe: Optional Datenreihe to apply the event to immediately
	
	Returns:
		Simulation instance
	"""
	event = create_event_from_type(event_type, intensity)
	simulation = Simulation(event)
	
	# If erzeuger provided, return the modified erzeuger
	# For now, we just return the simulation object
	# The user can call apply_to_erzeuger or apply_to_datenreihe separately
	
	return simulation

