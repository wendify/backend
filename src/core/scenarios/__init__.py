"""
Scenarios module - contains predefined energy transition scenarios.

Each scenario defines:
- Erzeuger-Datenpunkte (generator capacity milestones)
- Verbraucher-Datenpunkte (consumption forecasts)
"""

from core.scenarios.default import create_default_scenario

__all__ = ["create_default_scenario"]

