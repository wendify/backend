# Standard library imports
import datetime
from typing import Any

import pandas as pd


def merge_datenreihen(datenreihen: list) -> pd.DataFrame:
    """
    Merge multiple Datenreihen into a single DataFrame.
    
    Each Datenreihe's values are added as a column named after its 'art'.
    The index is set to 'Datum von' (start timestamp).
    Missing values are filled with 0.
    
    Args:
        datenreihen: List of Datenreihe objects to merge
        
    Returns:
        DataFrame with time index and one column per Datenreihe
    """
    if not datenreihen:
        return pd.DataFrame()
    
    # Extract each Datenreihe as a Series with time index
    data_series_list = []
    for dr in datenreihen:
        # Get the DataFrame, set "Datum von" as index, extract the value column
        series = dr.df.set_index("Datum von")[dr.art]
        data_series_list.append(series)
    
    # Merge all series into one DataFrame (outer join on time index)
    merged_df = pd.concat(data_series_list, axis=1)
    
    # Fill missing values with 0
    merged_df = merged_df.fillna(0)
    
    return merged_df


def resample_dataframe(df: pd.DataFrame, resolution: str) -> pd.DataFrame:
    """
    Resample a time-indexed DataFrame to a different resolution.
    
    Args:
        df: DataFrame with a DatetimeIndex
        resolution: One of "15min", "1h", "1d", "1w" (or None for no resampling)
        
    Returns:
        Resampled DataFrame (using mean aggregation)
    """
    if resolution is None:
        return df
    
    # Map human-readable names to pandas resample rules
    resolution_map = {
        "15min": None,  # No resampling needed (original resolution)
        "1h": "h",
        "1d": "D",
        "1w": "W",
    }
    
    rule = resolution_map.get(resolution)
    if rule is None:
        return df
    
    # Resample using mean (average power over the period)
    resampled = df.resample(rule).mean()
    return resampled


def get_color_map(column_names: list) -> dict:
    """
    Create a consistent color mapping for column names.
    
    Uses matplotlib's 'tab20' colormap to assign a unique color to each name.
    The same name will always get the same color.
    
    Args:
        column_names: List of column names (e.g., ErzeugerArt values)
        
    Returns:
        Dictionary mapping column name -> color tuple
    """
    try:
        from matplotlib import pyplot as plt
    except ModuleNotFoundError:
        # Return empty dict if matplotlib is not installed
        return {}
    
    cmap = plt.get_cmap("tab20")
    
    color_map = {}
    for i, name in enumerate(column_names):
        # Use modulo to wrap around if more than 20 names
        color_map[name] = cmap(i % 20)
    
    return color_map


def create_stackplot(
    df: pd.DataFrame,
    title: str = "Stackplot",
    xlabel: str = "Zeit",
    ylabel: str = "Leistung [MW]",
    color_map: dict | None = None,
    figsize: tuple = (12, 6),
) -> tuple[Any, Any]:
    """
    Create a stacked area plot from a DataFrame.
    
    Each column in the DataFrame becomes a stacked area.
    
    Args:
        df: DataFrame with time index and value columns
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        color_map: Optional dict mapping column names to colors
        figsize: Figure size as (width, height)
        
    Returns:
        Tuple of (figure, axes) matplotlib objects
    """
    try:
        from matplotlib import pyplot as plt
    except ModuleNotFoundError:
        raise ImportError("matplotlib is required for plotting")
    
    # Create figure and axes
    fig, ax = plt.subplots(figsize=figsize)
    
    if df.empty:
        ax.set_title(title)
        return fig, ax
    
    # Get column names (sorted for consistent order)
    columns = sorted(df.columns)
    
    # Prepare colors
    if color_map is None:
        color_map = get_color_map(columns)
    colors = [color_map.get(col, None) for col in columns]
    
    # Prepare data for stackplot
    x = df.index
    y = [df[col] for col in columns]
    
    # Create the stacked area plot
    ax.stackplot(x, y, labels=columns, colors=colors, alpha=0.8)
    
    # Add labels and legend
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(loc="upper left", bbox_to_anchor=(1.05, 1.0), borderaxespad=0.0)
    ax.grid(True, linestyle="--", alpha=0.5)
    
    return fig, ax


def create_lineplot(
    df: pd.DataFrame,
    title: str = "Liniendiagramm",
    xlabel: str = "Zeit",
    ylabel: str = "Wert",
    color_map: dict | None = None,
    figsize: tuple = (12, 6),
    show_markers: bool = True,
) -> tuple[Any, Any]:
    """
    Create a line plot from a DataFrame.
    
    Each column in the DataFrame becomes a line.
    
    Args:
        df: DataFrame with time index and value columns
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        color_map: Optional dict mapping column names to colors
        figsize: Figure size as (width, height)
        show_markers: Whether to show markers at data points
        
    Returns:
        Tuple of (figure, axes) matplotlib objects
    """
    try:
        from matplotlib import pyplot as plt
    except ModuleNotFoundError:
        raise ImportError("matplotlib is required for plotting")
    
    # Create figure and axes
    fig, ax = plt.subplots(figsize=figsize)
    
    if df.empty:
        ax.set_title(title)
        return fig, ax
    
    # Get column names (sorted for consistent order)
    columns = sorted(df.columns)
    
    # Prepare colors
    if color_map is None:
        color_map = get_color_map(columns)
    
    # Plot each column as a line
    for col in columns:
        color = color_map.get(col, None)
        marker = "o" if show_markers else None
        ax.plot(df.index, df[col], label=col, color=color, linewidth=2, marker=marker)
    
    # Add labels and legend
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    ax.grid(True, linestyle="--", alpha=0.3)
    
    # Adjust layout to make room for legend
    fig.tight_layout()
    
    return fig, ax


def add_vertical_line(
    ax: Any,
    x_value: datetime.datetime,
    color: str = "red",
    linestyle: str = "--",
    linewidth: float = 1.5,
    label: str | None = None,
    alpha: float = 1.0,
) -> None:
    """
    Add a vertical line to a plot.
    
    Useful for marking important time points (e.g., end of historical data).
    
    Args:
        ax: Matplotlib axes object
        x_value: X position (datetime) for the vertical line
        color: Line color
        linestyle: Line style (e.g., "--", ":", "-")
        linewidth: Line width
        label: Optional label for the legend
        alpha: Transparency (0-1)
    """
    ax.axvline(
        x=x_value,
        color=color,
        linestyle=linestyle,
        linewidth=linewidth,
        label=label,
        alpha=alpha,
    )


def add_multiple_vertical_lines(
    ax: Any,
    x_values: list[datetime.datetime],
    color: str = "black",
    linestyle: str = ":",
    linewidth: float = 1.0,
    alpha: float = 0.7,
) -> None:
    """
    Add multiple vertical lines to a plot.
    
    Useful for marking forecast data points or milestones.
    
    Args:
        ax: Matplotlib axes object
        x_values: List of X positions (datetimes) for the vertical lines
        color: Line color
        linestyle: Line style
        linewidth: Line width
        alpha: Transparency
    """
    for x in x_values:
        ax.axvline(
            x=x,
            color=color,
            linestyle=linestyle,
            linewidth=linewidth,
            alpha=alpha,
        )


def filter_columns(df: pd.DataFrame, visible_columns: list) -> pd.DataFrame:
    """
    Filter a DataFrame to only include specified columns.
    
    Args:
        df: DataFrame with multiple columns
        visible_columns: List of column names to keep
        
    Returns:
        DataFrame with only the specified columns
    """
    # Only keep columns that exist in the DataFrame
    existing_columns = [col for col in visible_columns if col in df.columns]
    return df[existing_columns]


def get_time_range(
    start: datetime.datetime,
    end: datetime.datetime,
    freq: str = "D",
) -> pd.DatetimeIndex:
    """
    Create a time range for plotting.
    
    Args:
        start: Start datetime
        end: End datetime
        freq: Frequency string (e.g., "D" for daily, "h" for hourly)
        
    Returns:
        DatetimeIndex with the time range
    """
    return pd.date_range(start=start, end=end, freq=freq)


def show_plots() -> None:
    """
    Display all open matplotlib plots.
    
    Call this after creating all plots to show them.
    """
    try:
        from matplotlib import pyplot as plt
    except ModuleNotFoundError:
        return
    
    plt.show()

