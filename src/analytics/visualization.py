"""Analytics Visualization Module for Dashboard-Ready Charts.

This module converts Phase 6.1 query results into matplotlib/seaborn charts
saved as PNG files. Each function corresponds to one analytical business
question and follows the same pattern as the export module: call a Phase 6.1
query, transform via pandas, plot, save, return metadata.

All charts use the non-interactive Agg backend so they can be generated on
servers and CI environments without a display. Charts are saved to a
configurable output directory (default: reports/generated/plots/).

Supported chart types:
- Executive summary KPI stat tiles
- Bar charts (horizontal and vertical)
- Line charts (time series)
- Pie / donut charts (proportions)
- Grouped bar charts (comparisons)

Design Principles:
- Each function calls exactly one Phase 6.1 query (no SQL duplication)
- Shared style helper for consistent aesthetics
- Returns metadata dict (filename, path, size_bytes, rows, figure_type)
- Gracefully handles empty datasets with a "No data" message on the plot
- No hardcoded business values — titles and labels come from the data
"""

import os
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend — must be set before pyplot import

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import seaborn as sns

# Default output directory for generated plots
DEFAULT_PLOTS_DIR = Path("reports/generated/plots")

# Consistent color palette across all charts
PALETTE = sns.color_palette("husl", 8)

# Suppress matplotlib font-manager warnings on Windows CI environments
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")


# ---------------------------------------------------------------------------
# Shared style helper
# ---------------------------------------------------------------------------

def _apply_style():
    """Apply a consistent seaborn/matplotlib style to the current figure.

    Sets:
    - seaborn-whitegrid background
    - 10pt base font size
    - tight layout defaults
    - axis tick label formatting
    """
    sns.set_theme(style="whitegrid", font_scale=1.0)
    plt.rcParams.update({
        "figure.dpi": 120,
        "savefig.dpi": 120,
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.autolayout": True,
    })


def _ensure_output_dir(output_dir: Path) -> Path:
    """Ensure the output directory exists."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    return out.resolve()


def _build_plot_metadata(
    filename: str,
    output_path: Path,
    row_count: int,
    figure_type: str,
    source_function: str,
) -> dict[str, Any]:
    """Build metadata dict for a generated plot."""
    file_size = os.path.getsize(output_path) if output_path.exists() else 0
    return {
        "filename": filename,
        "path": str(output_path),
        "format": "png",
        "size_bytes": file_size,
        "rows": row_count,
        "figure_type": figure_type,
        "source_function": source_function,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _save_figure(fig: plt.Figure, output_path: Path) -> None:
    """Save a matplotlib figure to a PNG file and close it."""
    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def _empty_plot(title: str, output_dir: Path, filename: str) -> dict[str, Any]:
    """Return a metadata dict and save a 'No data' placeholder figure."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.text(0.5, 0.5, "No data available", ha="center", va="center",
            fontsize=14, color="gray", transform=ax.transAxes)
    ax.set_title(title)
    ax.set_axis_off()
    output_path = Path(output_dir) / filename
    _save_figure(fig, output_path)
    return _build_plot_metadata(filename, output_path, 0, "empty", "N/A")


# ---------------------------------------------------------------------------
# Chart functions
# ---------------------------------------------------------------------------

def plot_executive_summary(
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Generate KPI stat tiles from the executive summary.

    Creates a 2×2 grid of large-number stat tiles showing headline metrics:
    total applications, total events, average events per app, and average
    processing days.

    Source: get_executive_summary()

    Returns:
        Metadata dict with filename, path, size_bytes, etc.
    """
    from src.analytics.queries import get_executive_summary

    data = get_executive_summary()
    out_dir = _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR)
    filename = "executive_summary.png"

    _apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(10, 6))
    fig.suptitle("Executive Summary — BPI Loan Applications", fontsize=15, y=1.02)

    tiles = [
        ("Total Applications", f"{data['total_applications']:,}", axes[0, 0]),
        ("Total Events", f"{data['total_events']:,}", axes[0, 1]),
        ("Avg Events / App", f"{data['avg_events_per_app']:.1f}", axes[1, 0]),
        ("Avg Processing Days", f"{data['avg_processing_days']:.1f}", axes[1, 1]),
    ]

    for label, value, ax in tiles:
        ax.set_axis_off()
        ax.text(0.5, 0.6, value, ha="center", va="center",
                fontsize=28, fontweight="bold", color=PALETTE[0], transform=ax.transAxes)
        ax.text(0.5, 0.2, label, ha="center", va="center",
                fontsize=11, color="#555", transform=ax.transAxes)

    output_path = out_dir / filename
    _save_figure(fig, output_path)
    return _build_plot_metadata(filename, output_path, 1, "kpi_tiles", "get_executive_summary")


def plot_application_volume_by_type(
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Horizontal bar chart of application count by type (New credit vs Limit raise).

    Source: get_application_volume_by_type()

    Returns:
        Metadata dict with filename, path, size_bytes, etc.
    """
    from src.analytics.queries import get_application_volume_by_type

    data = get_application_volume_by_type()
    if not data:
        return _empty_plot("Application Volume by Type",
                           _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR),
                           "application_volume_by_type.png")

    out_dir = _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR)
    filename = "application_volume_by_type.png"
    df = pd.DataFrame(data)

    _apply_style()
    fig, ax = plt.subplots(figsize=(8, 3.5))
    bars = ax.barh(
        df["application_type"],
        df["application_count"],
        color=[PALETTE[i] for i in range(len(df))],
        edgecolor="white",
        height=0.5,
    )
    ax.set_xlabel("Number of Applications")
    ax.set_title("Application Volume by Type")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # Value labels on bars
    for bar in bars:
        width = bar.get_width()
        ax.text(width + max(df["application_count"]) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{int(width):,}", ha="left", va="center", fontsize=10)

    ax.set_xlim(0, max(df["application_count"]) * 1.12)
    sns.despine(left=True)

    output_path = out_dir / filename
    _save_figure(fig, output_path)
    return _build_plot_metadata(filename, output_path, len(df), "bar", "get_application_volume_by_type")


def plot_application_volume_over_time(
    output_dir: Path | str | None = None,
    granularity: str = "monthly",
) -> dict[str, Any]:
    """Line chart of application volume over time.

    Source: get_application_volume_over_time(granularity)

    Args:
        granularity: 'monthly' (default) or 'daily'.

    Returns:
        Metadata dict with filename, path, size_bytes, etc.
    """
    from src.analytics.queries import get_application_volume_over_time

    data = get_application_volume_over_time(granularity=granularity)
    if not data:
        return _empty_plot(f"Application Volume Over Time ({granularity})",
                           _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR),
                           f"application_volume_over_time_{granularity}.png")

    out_dir = _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR)
    filename = f"application_volume_over_time_{granularity}.png"
    df = pd.DataFrame(data)

    _apply_style()
    fig, ax1 = plt.subplots(figsize=(10, 5))

    x_col = "year_month" if granularity == "monthly" else "date"
    y_col = "applications" if granularity == "monthly" else "applications_started"

    ax1.plot(df[x_col], df[y_col], marker="o", linewidth=2, color=PALETTE[0], label="Applications")
    ax1.set_xlabel("Period")
    ax1.set_ylabel("Applications Started")
    ax1.set_title(f"Application Volume Over Time ({granularity.capitalize()})")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    plt.xticks(rotation=45, ha="right")

    # Secondary axis for total events (monthly only)
    if granularity == "monthly" and "total_events" in df.columns:
        ax2 = ax1.twinx()
        ax2.plot(df[x_col], df["total_events"], marker="s", linewidth=1.5,
                 color=PALETTE[3], alpha=0.7, linestyle="--", label="Events")
        ax2.set_ylabel("Total Events")
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
        # Combined legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
    else:
        ax1.legend()

    sns.despine()
    output_path = out_dir / filename
    _save_figure(fig, output_path)
    return _build_plot_metadata(filename, output_path, len(df), "line", "get_application_volume_over_time")


def plot_activity_summary(
    output_dir: Path | str | None = None,
    top_n: int = 10,
) -> dict[str, Any]:
    """Horizontal bar chart of top activities by event count.

    Source: get_activity_summary()

    Args:
        top_n: Number of top activities to show (default 10).

    Returns:
        Metadata dict with filename, path, size_bytes, etc.
    """
    from src.analytics.queries import get_activity_summary

    data = get_activity_summary()
    if not data:
        return _empty_plot("Top Activities by Event Count",
                           _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR),
                           "activity_summary.png")

    out_dir = _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR)
    filename = "activity_summary.png"
    df = pd.DataFrame(data).head(top_n)

    if len(df) == 0:
        _apply_style()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                fontsize=14, color="gray", transform=ax.transAxes)
        ax.set_title(f"Top {top_n} Activities by Event Count")
        ax.set_axis_off()
        output_path = out_dir / filename
        _save_figure(fig, output_path)
        return _build_plot_metadata(filename, output_path, 0, "bar", "get_activity_summary")

    _apply_style()
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(
        df["activity"][::-1],
        df["event_count"][::-1],
        color=PALETTE[: len(df)][::-1],
        edgecolor="white",
        height=0.6,
    )
    ax.set_xlabel("Event Count")
    ax.set_title(f"Top {top_n} Activities by Event Count")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # Value labels
    max_val = max(df["event_count"])
    for bar in bars:
        width = bar.get_width()
        ax.text(width + max_val * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{int(width):,}", ha="left", va="center", fontsize=9)

    ax.set_xlim(0, max_val * 1.15)
    sns.despine(left=True)

    output_path = out_dir / filename
    _save_figure(fig, output_path)
    return _build_plot_metadata(filename, output_path, len(df), "bar", "get_activity_summary")


def plot_resource_workload(
    output_dir: Path | str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Horizontal bar chart of top resources by event count.

    Source: get_resource_workload(limit)

    Args:
        limit: Number of top resources to show (default 20).

    Returns:
        Metadata dict with filename, path, size_bytes, etc.
    """
    from src.analytics.queries import get_resource_workload

    data = get_resource_workload(limit=limit)
    if not data:
        return _empty_plot("Top Resources by Workload",
                           _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR),
                           "resource_workload.png")

    out_dir = _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR)
    filename = "resource_workload.png"
    df = pd.DataFrame(data)

    _apply_style()
    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(
        df["resource"][::-1],
        df["event_count"][::-1],
        color=PALETTE[: len(df)][::-1] if len(df) <= 8 else sns.color_palette("husl", len(df))[::-1],
        edgecolor="white",
        height=0.6,
    )
    ax.set_xlabel("Event Count")
    ax.set_title(f"Top {limit} Resources by Workload")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    max_val = max(df["event_count"])
    for bar in bars:
        width = bar.get_width()
        ax.text(width + max_val * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{int(width):,}", ha="left", va="center", fontsize=8)

    ax.set_xlim(0, max_val * 1.15)
    sns.despine(left=True)

    output_path = out_dir / filename
    _save_figure(fig, output_path)
    return _build_plot_metadata(filename, output_path, len(df), "bar", "get_resource_workload")


def plot_lifecycle_outcomes(
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Donut chart of lifecycle outcome distribution (complete / suspend / withdraw).

    Source: get_lifecycle_outcome_summary()

    Returns:
        Metadata dict with filename, path, size_bytes, etc.
    """
    from src.analytics.queries import get_lifecycle_outcome_summary

    data = get_lifecycle_outcome_summary()
    if not data:
        return _empty_plot("Lifecycle Outcome Distribution",
                           _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR),
                           "lifecycle_outcomes.png")

    out_dir = _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR)
    filename = "lifecycle_outcomes.png"
    df = pd.DataFrame(data)

    _apply_style()
    fig, ax = plt.subplots(figsize=(7, 7))

    labels = df["lifecycle_transition"]
    sizes = df["event_count"]
    colors = sns.color_palette("Set2", len(df))

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct=lambda pct: f"{pct:.1f}%\n({int(round(pct / 100.0 * sizes.sum())):,})",
        colors=colors,
        startangle=90,
        pctdistance=0.75,
        textprops={"fontsize": 10},
    )
    for t in autotexts:
        t.set_fontsize(9)

    # Draw centre circle for donut effect
    centre_circle = plt.Circle((0, 0), 0.50, fc="white")
    ax.add_artist(centre_circle)

    ax.set_title("Lifecycle Outcome Distribution")
    sns.despine(left=True, bottom=True)

    output_path = out_dir / filename
    _save_figure(fig, output_path)
    return _build_plot_metadata(filename, output_path, len(df), "donut", "get_lifecycle_outcome_summary")


def plot_loan_goal_summary(
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Grouped bar chart of application count and avg processing hours by loan goal.

    Source: get_loan_goal_summary()

    Returns:
        Metadata dict with filename, path, size_bytes, etc.
    """
    from src.analytics.queries import get_loan_goal_summary

    data = get_loan_goal_summary()
    if not data:
        return _empty_plot("Loan Goal Summary",
                           _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR),
                           "loan_goal_summary.png")

    out_dir = _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR)
    filename = "loan_goal_summary.png"
    df = pd.DataFrame(data)

    _apply_style()
    fig, ax1 = plt.subplots(figsize=(10, 5))
    x = range(len(df))
    width = 0.4

    bars1 = ax1.bar([i - width / 2 for i in x], df["application_count"],
                    width=width, label="Application Count", color=PALETTE[0], edgecolor="white")
    ax1.set_ylabel("Application Count")
    ax1.set_xlabel("Loan Goal")
    ax1.set_title("Loan Goal Summary — Applications vs Avg Processing Hours")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(df["loan_goal"], rotation=30, ha="right")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    ax2 = ax1.twinx()
    bars2 = ax2.bar([i + width / 2 for i in x], df["avg_processing_hours"],
                    width=width, label="Avg Processing Hours", color=PALETTE[3], edgecolor="white", alpha=0.85)
    ax2.set_ylabel("Avg Processing Hours")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

    sns.despine(left=False, right=False)
    output_path = out_dir / filename
    _save_figure(fig, output_path)
    return _build_plot_metadata(filename, output_path, len(df), "grouped_bar", "get_loan_goal_summary")


def plot_processing_time_distribution(
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Vertical bar chart of application count by processing time bucket.

    Source: get_processing_time_distribution()

    Returns:
        Metadata dict with filename, path, size_bytes, etc.
    """
    from src.analytics.queries import get_processing_time_distribution

    data = get_processing_time_distribution()
    if not data:
        return _empty_plot("Processing Time Distribution",
                           _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR),
                           "processing_time_distribution.png")

    out_dir = _ensure_output_dir(Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR)
    filename = "processing_time_distribution.png"
    df = pd.DataFrame(data)

    _apply_style()
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(
        df["bucket"],
        df["application_count"],
        color=[PALETTE[i] for i in range(len(df))],
        edgecolor="white",
        width=0.6,
    )
    ax.set_xlabel("Processing Time Bucket")
    ax.set_ylabel("Number of Applications")
    ax.set_title("Processing Time Distribution")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # Value labels on bars
    max_val = max(df["application_count"])
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + max_val * 0.01,
                f"{int(height):,}", ha="center", va="bottom", fontsize=10)

    ax.set_ylim(0, max_val * 1.12)
    plt.xticks(rotation=25, ha="right")
    sns.despine()

    output_path = out_dir / filename
    _save_figure(fig, output_path)
    return _build_plot_metadata(filename, output_path, len(df), "bar", "get_processing_time_distribution")


# ---------------------------------------------------------------------------
# Batch and manifest
# ---------------------------------------------------------------------------

def plot_all(
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Generate all analytics plots and return an aggregate manifest.

    Args:
        output_dir: Target directory. Defaults to reports/generated/plots/.

    Returns:
        Dict with keys:
        - generated_at: ISO timestamp
        - output_dir: Absolute path
        - figures: Dict mapping figure name to metadata dict
        - total_figures: Count of figures generated
        - total_size_bytes: Sum of all file sizes
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR
    figures = {}

    plot_funcs = [
        ("executive_summary", plot_executive_summary),
        ("application_volume_by_type", plot_application_volume_by_type),
        ("application_volume_monthly",
         lambda d: plot_application_volume_over_time(d, "monthly")),
        ("application_volume_daily",
         lambda d: plot_application_volume_over_time(d, "daily")),
        ("activity_summary", plot_activity_summary),
        ("resource_workload", plot_resource_workload),
        ("lifecycle_outcomes", plot_lifecycle_outcomes),
        ("loan_goal_summary", plot_loan_goal_summary),
        ("processing_time_distribution", plot_processing_time_distribution),
    ]

    for name, func in plot_funcs:
        try:
            meta = func(out_dir)
            figures[name] = meta
        except Exception as e:
            figures[name] = {"error": str(e)}

    total_size = sum(
        m.get("size_bytes", 0) for m in figures.values() if isinstance(m, dict) and "error" not in m
    )
    total_figs = sum(1 for m in figures.values() if isinstance(m, dict) and "error" not in m)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(_ensure_output_dir(out_dir)),
        "figures": figures,
        "total_figures": total_figs,
        "total_size_bytes": total_size,
    }


def get_plot_manifest(
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """List all plot files in the output directory.

    Args:
        output_dir: Directory to scan. Defaults to reports/generated/plots/.

    Returns:
        Dict with keys:
        - output_dir: Absolute path
        - files: List of dicts with filename, format, size_bytes, modified_at
        - total_files: Count of plot files
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_PLOTS_DIR
    out_dir = out_dir.resolve()

    files = []
    if out_dir.exists():
        for f in sorted(out_dir.iterdir()):
            if f.suffix == ".png":
                stat = f.stat()
                files.append({
                    "filename": f.name,
                    "format": "png",
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                })

    return {
        "output_dir": str(out_dir),
        "files": files,
        "total_files": len(files),
    }
