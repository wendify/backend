"""
Visualization module - Plotly-based interactive plots for energy data.

All plots open in the browser with full interactivity:
- Hover info with MW values
- Zoom/Pan controls
- Generator filtering via legend clicks
- Resolution dropdown selector

Main entry point: show_all_plots()
"""

from core.visualization.components import (
	GENERATOR_COLORS,
	RESOLUTION_OPTIONS,
	get_color,
	get_color_map,
	merge_datenreihen_to_dataframe,
	resample_dataframe,
)
from core.visualization.plots import (
	create_comparison_stackplot,
	create_curtailment_plot,
	create_installed_capacity_plot,
	create_prognose_stackplot,
	create_realized_stackplot,
	create_single_generator_plot,
	create_surplus_plot,
	show_all_plots,
)

__all__ = [
	# Main function
	"show_all_plots",
	# Individual plot creators
	"create_prognose_stackplot",
	"create_installed_capacity_plot",
	"create_realized_stackplot",
	"create_surplus_plot",
	"create_comparison_stackplot",
	"create_curtailment_plot",
	"create_single_generator_plot",
	# Helper functions
	"resample_dataframe",
	"merge_datenreihen_to_dataframe",
	"get_color",
	"get_color_map",
	# Constants
	"RESOLUTION_OPTIONS",
	"GENERATOR_COLORS",
]
