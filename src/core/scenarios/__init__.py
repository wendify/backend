"""
Scenarios module - contains predefined energy transition scenarios.

Each scenario defines:
- Erzeuger-Datenpunkte (generator capacity milestones)
- Verbraucher-Datenpunkte (consumption forecasts)

Szenarien werden aus CSV-Dateien geladen.
Jedes Szenario liegt in einem eigenen Ordner mit:
- erzeuger.csv
- verbraucher.csv
"""

from core.scenarios.scenario_loader import list_scenarios, load_scenario

__all__ = ["load_scenario", "list_scenarios"]
