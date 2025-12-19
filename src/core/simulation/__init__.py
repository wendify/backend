"""Simulation module for applying events like drought to energy production.

This module provides:
- Parameter definitions (temp, sun, rainfall, wind)
- Event types (e.g., drought)
- Producer-specific parameter weights
- Impact calculation and application to energy data
- CO2 emissions calculation
"""

from core.simulation.co2_calc import calculate_co2_emissions
from core.simulation.event import EventDatenpunkt, EventType, SimulationEvent, create_event_from_type
from core.simulation.impact import apply_event_to_energy, calculate_impact_factor
from core.simulation.parameter import ParamLevel, ParamName, ParamValue
from core.simulation.producer_weights import ProducerWeights, get_producer_weights
from core.simulation.simulator import Simulation, apply_events_to_realized, simulate_event

__all__ = [
	"EventDatenpunkt",
	"EventType",
	"SimulationEvent",
	"create_event_from_type",
	"ParamLevel",
	"ParamName",
	"ParamValue",
	"ProducerWeights",
	"get_producer_weights",
	"calculate_impact_factor",
	"apply_event_to_energy",
	"Simulation",
	"simulate_event",
	"apply_events_to_realized",
	"calculate_co2_emissions",
]
