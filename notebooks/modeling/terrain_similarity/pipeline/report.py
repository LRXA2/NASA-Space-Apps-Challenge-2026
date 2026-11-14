"""Static, headless terrain comparisons for a completed Moon/Earth site pair."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox

if TYPE_CHECKING:
    from notebooks.modeling.terrain_similarity.pipeline.main import SiteComparison


def _site_name(region: str) -> str:
    return re.sub(r"^A3CLR22_\d+_", "", region).replace("_", " ")


def _pair_figure(
    path: Path,
    query: pd.Series,
    candidate: pd.Series,
    values: list[np.ndarray],
    comparison: pd.DataFrame,
    score: float,
    rank: int,
    selection: str,
    height_limit: float,
    slope_limit: float,
) -> None:
    fig = Figure(figsize=(11, 13), constrained_layout=True)
    FigureCanvasAgg(fig)
    grid = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 0.65])
    axes = [[fig.add_subplot(grid[row, col]) for col in range(2)] for row in range(2)]
    measurements = fig.add_subplot(grid[2, :])
    measurements.axis("off")
    elevation_image = slope_image = None
    for column, (item, patch, body) in enumerate(
        zip([query, candidate], values, ["MOON", "EARTH"], strict=True)
    ):
        slope_image = axes[0][column].imshow(
            patch[1], cmap="viridis", vmin=0, vmax=slope_limit, extent=(0, 960, 0, 960)
        )
        elevation_image = axes[1][column].imshow(
            patch[0],
            cmap="RdBu_r",
            vmin=-height_limit,
            vmax=height_limit,
            extent=(0, 960, 0, 960),
        )
        axes[0][column].set_title(
            f"{body} — {_site_name(str(item['region']))}\nSlope · P90 {item['slope_p90_deg']:.1f}°",
            fontsize=11,
            pad=10,
        )
        axes[1][column].set_title(
            f"{body} — relative elevation\nHeight range {item['central_relief_m']:.1f} m",
            fontsize=11,
            pad=10,
        )
        for row in range(2):
            axes[row][column].set(
                xticks=[0, 480, 960],
                yticks=[0, 480, 960],
                xlabel="metres",
                ylabel="metres",
            )
    assert elevation_image is not None and slope_image is not None
    fig.colorbar(slope_image, ax=axes[0], label="Slope (degrees)", shrink=0.8)
    fig.colorbar(
        elevation_image, ax=axes[1], label="Relative elevation (m)", shrink=0.8
    )
    fig.suptitle(
        f"{selection} example · Earth candidate #{rank}\n"
        f"CNN cosine: {score:.3f} · rotations + reflections\n"
        "Same 960 m extent and shared physical colour scales",
        fontsize=13,
    )
    within = int(comparison.within_band.sum())
    measurements.text(
        0.0,
        0.99,
        "PHYSICAL MEASUREMENTS — lower differences are closer",
        transform=measurements.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
    )
    measurements.text(
        0.0,
        0.87,
        f"{within}/5 exploratory checks within the declared bands",
        transform=measurements.transAxes,
        fontsize=11,
        va="top",
    )
    table_values = []
    records = comparison.to_dict("records")
    for row in records:
        decimals = 3 if row["feature"] == "plane_residual_fraction" else 2
        table_values.append(
            [
                row["measurement"],
                f"{row['moon']:.{decimals}f}",
                f"{row['earth']:.{decimals}f}",
                f"{row['absolute_difference']:.{decimals}f}",
                f"{row['comparison_band']:.{decimals}f}",
                f"{row['difference_over_band']:.2f}×",
                "Within" if row["within_band"] else "Outside",
            ]
        )
    table = measurements.table(
        cellText=table_values,
        colLabels=[
            "Measurement / units",
            "Moon",
            "Earth",
            "Difference",
            "Band",
            "Diff./band",
            "Check",
        ],
        colWidths=[0.28, 0.105, 0.105, 0.145, 0.105, 0.13, 0.13],
        cellLoc="center",
        bbox=Bbox.from_bounds(0.0, 0.12, 1.0, 0.64),
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor("#d5dce3")
        if row == 0:
            cell.set_facecolor("#e9eef3")
            cell.set_text_props(weight="bold")
        elif column == 0:
            cell.set_text_props(ha="left")
        elif column in (5, 6):
            cell.set_facecolor(
                "#dcefe8" if records[row - 1]["within_band"] else "#ffe3c2"
            )
    measurements.text(
        0.0,
        0.04,
        "Exploratory bands, not mission limits or a similarity percentage.",
        transform=measurements.transAxes,
        fontsize=9,
        va="bottom",
    )
    fig.savefig(path, dpi=125)
    fig.clear()


def _distribution_figure(
    path: Path, arrays: list[np.ndarray], labels: list[str], selection: str
) -> None:
    fig = Figure(figsize=(11, 4.5), constrained_layout=True)
    FigureCanvasAgg(fig)
    axes = fig.subplots(1, 2)
    for position, (values, label) in enumerate(zip(arrays, labels, strict=True)):
        for ax, channel in zip(axes, [1, 0], strict=True):
            ordered = np.sort(values[channel].ravel())
            ax.step(
                ordered,
                np.arange(1, len(ordered) + 1) / len(ordered),
                where="post",
                label=label,
                linewidth=2.5 if position == 0 else 1.5,
                color="black" if position == 0 else None,
            )
    axes[0].set(
        xlabel="Slope (degrees)",
        ylabel="Fraction of patch cells",
        title="Steepness distribution",
    )
    axes[1].set(
        xlabel="Relative elevation (m)",
        ylabel="Fraction of patch cells",
        title="Height distribution",
    )
    for ax in axes:
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.2)
    axes[0].legend(fontsize=8, loc="lower right")
    fig.suptitle(f"{selection} example: lunar query and ranked Earth candidates")
    fig.savefig(path, dpi=125)
    fig.clear()


def write_report(
    output: Path,
    patches: pd.DataFrame,
    physical_patch: Callable[[str], np.ndarray],
    matches: pd.DataFrame,
    physical: pd.DataFrame,
    summary: SiteComparison,
    examples: pd.DataFrame,
) -> None:
    """Write selected comparisons; the summary covers every prepared lunar patch."""
    lines = [
        f"# Terrain similarity: {_site_name(summary['moon_site'])} → {_site_name(summary['earth_site'])}",
        "",
        f"Compared **{summary['moon_patch_count']} lunar patches** with **{summary['earth_patch_count']} Earth patches**, "
        f"returning the closest {summary['top_k']} Earth patches for each lunar patch.",
        "",
        "| Measurement | Result |",
        "| --- | --- |",
        f"| Median best-patch CNN cosine | {summary['median_best_patch_cosine']:.4f} |",
        f"| Median height-range difference for first matches | {summary['median_top1_relief_difference_m']:.2f} m |",
        f"| Median P90 slope difference for first matches | {summary['median_top1_slope_p90_difference_deg']:.2f}° |",
        f"| Lunar patches with a candidate passing all five exploratory checks in top {summary['top_k']} | "
        f"{summary['queries_with_all_five_checks_in_top_k']} / {summary['moon_patch_count']} |",
        f"| Distinct Earth patches used as first matches | {summary['distinct_top1_earth_patches']} |",
        "",
        "**Interpretation:** higher cosine means closer CNN representations. It is not a percentage of site similarity "
        "or validated accuracy. This asks whether the selected Earth site contains terrain resembling the lunar site; "
        "it does not establish that the entire Earth region is equivalent. Larger candidate pools can offer more chances "
        "for a close match, and the same Earth patch may serve multiple lunar patches.",
        "",
        "All eligible prepared patches are included, with development training/holdout folds pooled. "
        "The saved model, scaler and eight-orientation inference policy are reused. "
        "Physical measurements explain cosine rankings; they do not change the order.",
        "",
        "The bands are: median slope 1°, P90 slope 2°, height range max(5 m, 10% of the smaller value), "
        "plane residual fraction 0.1, and local height SD max(1 m, 10% of the smaller value). "
        "These are exploratory comparisons, not equipment limits. Independent relevance review is still needed.",
        "",
        "## Visual examples",
        "",
        "The examples are selected by highest, middle and lowest first-match cosine across lunar patches; "
        "they are not a random sample. Maps keep their original orientation, so mentally allow rotation/reflection. "
        "Height and slope retain physical units and shared scales within each query. "
        "Distribution curves do not show spatial arrangement.",
        "",
    ]
    for example in examples.to_dict("records"):
        query_id = example["query_id"]
        chosen = matches.loc[matches.query_id == query_id].sort_values("rank")
        ids = [query_id, *chosen.candidate_id.tolist()]
        arrays = [physical_patch(patch_id) for patch_id in ids]
        height_limit = max(float(np.abs(values[0]).max()) for values in arrays) or 1.0
        slope_limit = max(float(values[1].max()) for values in arrays) or 1.0
        lines.extend([f"### {example['selection']}", f"Lunar patch: `{query_id}`", ""])
        for row in chosen.to_dict("records"):
            rank = int(row["rank"])
            filename = f"example_{example['example']}_rank_{rank}.png"
            comparison = physical.loc[
                (physical.query_id == query_id) & (physical["rank"] == rank)
            ]
            _pair_figure(
                output / filename,
                patches.loc[query_id],
                patches.loc[row["candidate_id"]],
                [arrays[0], arrays[rank]],
                comparison,
                float(row["cosine_similarity"]),
                rank,
                example["selection"],
                height_limit,
                slope_limit,
            )
            lines.extend(
                [
                    f"Earth patch #{rank}: `{row['candidate_id']}`",
                    f"![Terrain comparison]({filename})",
                    "",
                ]
            )
        filename = f"example_{example['example']}_distributions.png"
        _distribution_figure(
            output / filename,
            arrays,
            ["Moon query", *[f"Earth #{rank}" for rank in range(1, len(ids))]],
            example["selection"],
        )
        lines.extend([f"![Slope and height distributions]({filename})", ""])
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
