import datetime
from typing import Dict, List

import pandas as pd

from core.datenreihe import Datenreihe
from core.simulation.event import EventDatenpunkt, EventType, SimulationEvent, create_event_from_type
from core.simulation.impact import apply_event_to_energy, calculate_impact_factor
from core.types import ErzeugerArt


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
		# Preserve the regulation value from the original erzeuger
		return Erzeuger(erzeuger.art, erzeuger.installiert, modified_realisiert, erzeuger.regulation)


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


def apply_events_to_realized(
	realisiert_datenreihen: Dict[ErzeugerArt, Datenreihe],
	events: List[EventDatenpunkt],
) -> Dict[ErzeugerArt, Datenreihe]:
	"""
	Wendet Events auf die realisierte Erzeugung an (nur im jeweiligen Zeitbereich).
	
	Für jeden EventDatenpunkt wird der Impact-Faktor auf alle Zeitpunkte
	innerhalb [datum_von, datum_bis) angewendet.
	
	Args:
		realisiert_datenreihen: Dict von ErzeugerArt zu Datenreihe mit realisierter Erzeugung
		events: Liste von EventDatenpunkt mit Zeitbereichen und Intensitäten
	
	Returns:
		Neues Dict mit modifizierten Datenreihen (Original bleibt unverändert)
	"""
	# Wenn keine Events, Original zurückgeben
	if not events:
		return realisiert_datenreihen
	
	# Kopie erstellen um Original nicht zu verändern
	ergebnis: Dict[ErzeugerArt, Datenreihe] = {}
	
	for erzeuger_art, original_datenreihe in realisiert_datenreihen.items():
		# DataFrame kopieren
		df = original_datenreihe.df.copy()
		
		# Für jeden Event
		for event in events:
			# SimulationEvent erstellen
			simulation_event = create_event_from_type(event.event_typ, event.intensitaet)
			
			# Zeitbereich filtern: datum_von <= Datum < datum_bis
			datum_spalte = df["Datum von"]
			
			# Maske für Zeitbereich erstellen
			in_zeitbereich = (datum_spalte >= event.datum_von) & (datum_spalte < event.datum_bis)
			
			# Anzahl betroffener Zeitschritte
			anzahl_betroffen = in_zeitbereich.sum()
			
			if anzahl_betroffen == 0:
				continue
			
			# Impact-Faktor EINMAL berechnen (ist konstant für Event + ErzeugerArt)
			impact_factor = calculate_impact_factor(simulation_event, erzeuger_art)
			
			# Vektorisiert multiplizieren (SCHNELL!)
			df.loc[in_zeitbereich, erzeuger_art] *= impact_factor
		
		# Neue Datenreihe erstellen
		ergebnis[erzeuger_art] = Datenreihe(erzeuger_art, df)
	
	return ergebnis
