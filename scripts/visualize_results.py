#!/usr/bin/env python3
"""
visualize_results.py — turn a QM/MM ORCA output into a clean summary figure

Produces a single PNG with two panels:
  Left  : QM/MM energy, shown in all three common units
  Right : Mulliken atomic charges for every atom in the QM region, sorted,
          with the most negative (typically the strongest H-bond acceptor)
          and most positive atoms called out

Works on any ORCA QM/MM output — there is nothing protein- or
ligand-specific in this script. It only needs the .out file path.

Usage:
    python scripts/visualize_results.py --output-dir qmmm_output
    python scripts/visualize_results.py --orca-out path/to/qmmm_system.out
    python scripts/visualize_results.py --orca-out a.out --compare-to b.out \\
        --labels "In protein" "Gas phase"
"""

import argparse
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orca_parser import parse_orca_output  # noqa: E402

# -----------------------------------------------------------------------------
# Visual style — kept in one place so the look stays consistent everywhere
# -----------------------------------------------------------------------------
BG = "#0f1419"
PANEL_BG = "#161b22"
GRID = "#2a313c"
TEXT = "#e6edf3"
SUBTEXT = "#8b949e"
ACCENT_NEG = "#ef5350"   # negative charge / electronegative
ACCENT_POS = "#42a5f5"   # positive charge
ACCENT_NEUTRAL = "#8b949e"
ACCENT_HIGHLIGHT = "#ffca28"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": PANEL_BG,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT,
    "text.color": TEXT,
    "xtick.color": SUBTEXT,
    "ytick.color": SUBTEXT,
    "grid.color": GRID,
    "font.size": 10.5,
    "font.family": "DejaVu Sans",
})


def parse_args():
    p = argparse.ArgumentParser(description="Visualize a QM/MM ORCA result.")
    p.add_argument("--output-dir", default="qmmm_output",
                    help="Folder containing qmmm_system.out (default: qmmm_output)")
    p.add_argument("--orca-out", default=None,
                    help="Explicit path to an ORCA .out file (overrides --output-dir)")
    p.add_argument("--compare-to", default=None,
                    help="A second ORCA .out file to plot alongside the first "
                         "(e.g. gas-phase vs. in-protein)")
    p.add_argument("--labels", nargs=2, default=["System A", "System B"],
                    help="Labels for the two datasets when using --compare-to")
    p.add_argument("--title", default="QM/MM Results",
                    help="Title for the figure")
    p.add_argument("--out", default=None,
                    help="Where to save the figure (default: <output-dir>/qmmm_summary.png)")
    p.add_argument("--show", action="store_true", help="Also open an interactive window")
    return p.parse_args()


def resolve_orca_out_path(args) -> str:
    if args.orca_out:
        return args.orca_out
    candidate = os.path.join(args.output_dir, "qmmm_system.out")
    if os.path.isfile(candidate):
        return candidate
    print(f"Could not find an ORCA output file. Looked for: {candidate}")
    print("Pass --orca-out /path/to/your_file.out to point at it directly.")
    sys.exit(1)


def plot_single(result, title, out_path, show):
    fig = plt.figure(figsize=(12, 5.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.6], wspace=0.32,
                           left=0.06, right=0.97, top=0.84, bottom=0.13)

    fig.suptitle(title, fontsize=15, fontweight="bold", color=TEXT, x=0.06, ha="left")
    status = "ORCA terminated normally" if result.terminated_normally else "ORCA did not terminate normally"
    fig.text(0.06, 0.90, status,
              fontsize=9.5, color=("#66bb6a" if result.terminated_normally else ACCENT_NEG))

    _plot_energy_panel(fig.add_subplot(gs[0]), result)
    _plot_charge_panel(fig.add_subplot(gs[1]), result)

    fig.savefig(out_path, dpi=180, facecolor=BG)
    print(f"Saved figure -> {out_path}")
    if show:
        plt.show()


def _plot_energy_panel(ax, result):
    ax.set_facecolor(PANEL_BG)
    ax.set_title("QM/MM Energy", fontsize=11.5, fontweight="bold", pad=12, loc="left")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    if result.energy_hartree is None:
        ax.text(0.5, 0.5, "No energy found", ha="center", va="center", color=SUBTEXT)
        return

    rows = [
        ("Hartree", result.energy_hartree),
        ("eV", result.energy_ev),
        ("kcal/mol", result.energy_kcalmol),
    ]

    y0 = 0.80
    dy = 0.20
    for i, (unit_name, value) in enumerate(rows):
        y = y0 - i * dy
        ax.text(0.0, y, unit_name, fontsize=10.5, color=SUBTEXT, transform=ax.transAxes)
        ax.text(1.0, y, f"{value:,.4f}", fontsize=14, color=TEXT, fontweight="bold",
                ha="right", transform=ax.transAxes, family="monospace")

    ax.text(0.0, 0.10,
            "Absolute energy is not meaningful alone.\n"
            "Compare two runs (e.g. in-protein vs. gas phase)\n"
            "to get a physically meaningful energy difference.",
            fontsize=8.3, color=SUBTEXT, transform=ax.transAxes, va="top")

    rect = plt.Rectangle((0.0, 0.0), 1.0, 1.0, transform=ax.transAxes,
                          fill=False, edgecolor=GRID, linewidth=1.2, clip_on=False)
    ax.add_patch(rect)


def _plot_charge_panel(ax, result):
    ax.set_title("Mulliken Atomic Charges (QM region)", fontsize=11.5,
                 fontweight="bold", pad=12, loc="left")

    if not result.mulliken_charges:
        ax.text(0.5, 0.5, "No Mulliken charges found", ha="center", va="center", color=SUBTEXT)
        ax.axis("off")
        return

    items = sorted(result.mulliken_charges.items(), key=lambda kv: kv[1])
    indices = [i for i, _ in items]
    charges = [q for _, q in items]
    labels = [f"{result.elements.get(i, '?')}{i}" for i in indices]

    colors = []
    most_neg_idx = min(result.mulliken_charges, key=result.mulliken_charges.get)
    most_pos_idx = max(result.mulliken_charges, key=result.mulliken_charges.get)
    for i, q in items:
        if i == most_neg_idx:
            colors.append(ACCENT_HIGHLIGHT)
        elif i == most_pos_idx:
            colors.append(ACCENT_POS)
        elif q < 0:
            colors.append(ACCENT_NEG)
        else:
            colors.append(ACCENT_NEUTRAL)

    y_pos = np.arange(len(labels))
    ax.barh(y_pos, charges, color=colors, height=0.62, edgecolor="none")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8.6, family="monospace")
    ax.axvline(0, color=GRID, linewidth=1)
    ax.set_xlabel("Charge (e)", fontsize=10)
    ax.grid(axis="x", alpha=0.35)
    ax.tick_params(axis="y", length=0)

    # annotate the extremes
    most_neg_q = result.mulliken_charges[most_neg_idx]
    neg_y = list(indices).index(most_neg_idx)
    ax.annotate(
        f"most negative: {most_neg_q:+.3f} e (likely H-bond acceptor)",
        xy=(most_neg_q, neg_y),
        xytext=(0, 16), textcoords="offset points",
        fontsize=8, color=ACCENT_HIGHLIGHT, ha="left",
        arrowprops=dict(arrowstyle="-", color=ACCENT_HIGHLIGHT, lw=0.7),
    )

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


def plot_comparison(result_a, result_b, labels, title, out_path, show):
    fig = plt.figure(figsize=(13, 6.4))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 2.4], hspace=0.45,
                           left=0.08, right=0.96, top=0.86, bottom=0.10)

    fig.suptitle(title, fontsize=15, fontweight="bold", color=TEXT, x=0.08, ha="left")

    # --- energy comparison bar ---
    ax_e = fig.add_subplot(gs[0])
    ax_e.set_facecolor(PANEL_BG)
    ax_e.set_title("Energy comparison (kcal/mol)", fontsize=11, loc="left", fontweight="bold")
    energies = [result_a.energy_kcalmol, result_b.energy_kcalmol]
    bars = ax_e.bar(labels, energies, color=[ACCENT_NEUTRAL, ACCENT_HIGHLIGHT], width=0.45)
    for bar, val in zip(bars, energies):
        if val is not None:
            ax_e.text(bar.get_x() + bar.get_width() / 2, val, f"{val:,.1f}",
                       ha="center", va="bottom" if val >= 0 else "top", fontsize=9.5, color=TEXT)
    ax_e.grid(axis="y", alpha=0.3)
    for spine in ("top", "right"):
        ax_e.spines[spine].set_visible(False)
    if all(e is not None for e in energies):
        delta = energies[0] - energies[1]
        ax_e.text(0.985, 0.92, f"\u0394 = {delta:+.2f} kcal/mol  ({labels[0]} \u2212 {labels[1]})",
                   transform=ax_e.transAxes, fontsize=9, color=SUBTEXT, va="top", ha="right")

    # --- charge comparison (grouped bars) ---
    ax_c = fig.add_subplot(gs[1])
    ax_c.set_facecolor(PANEL_BG)
    ax_c.set_title("Mulliken charge comparison, per atom", fontsize=11, loc="left", fontweight="bold")

    shared_indices = sorted(set(result_a.mulliken_charges) & set(result_b.mulliken_charges))
    if not shared_indices:
        ax_c.text(0.5, 0.5, "No overlapping atom indices to compare", ha="center", va="center", color=SUBTEXT)
        ax_c.axis("off")
    else:
        a_vals = [result_a.mulliken_charges[i] for i in shared_indices]
        b_vals = [result_b.mulliken_charges[i] for i in shared_indices]
        elem_labels = [f"{result_a.elements.get(i, '?')}{i}" for i in shared_indices]

        x = np.arange(len(shared_indices))
        width = 0.36
        ax_c.bar(x - width / 2, a_vals, width, label=labels[0], color=ACCENT_NEUTRAL)
        ax_c.bar(x + width / 2, b_vals, width, label=labels[1], color=ACCENT_HIGHLIGHT)
        ax_c.set_xticks(x)
        ax_c.set_xticklabels(elem_labels, fontsize=8.5, family="monospace", rotation=0)
        ax_c.axhline(0, color=GRID, linewidth=1)
        ax_c.set_ylabel("Charge (e)")
        ax_c.legend(frameon=False, fontsize=9, loc="upper right")
        ax_c.grid(axis="y", alpha=0.3)
        ymin, ymax = ax_c.get_ylim()
        ax_c.set_ylim(ymin, ymax + 0.15 * (ymax - ymin))
        for spine in ("top", "right"):
            ax_c.spines[spine].set_visible(False)

        # highlight the biggest charge shift
        deltas = [b - a for a, b in zip(a_vals, b_vals)]
        max_i = int(np.argmax(np.abs(deltas)))
        peak_y = max(a_vals[max_i], b_vals[max_i])
        ax_c.annotate(
            f"largest shift: {elem_labels[max_i]}  \u0394q = {deltas[max_i]:+.3f} e",
            xy=(max_i + width / 2, peak_y),
            xytext=(15, 10), textcoords="offset points",
            ha="left", fontsize=8.5, color=ACCENT_HIGHLIGHT,
            arrowprops=dict(arrowstyle="-", color=ACCENT_HIGHLIGHT, lw=0.8),
        )

    fig.savefig(out_path, dpi=180, facecolor=BG)
    print(f"Saved figure -> {out_path}")
    if show:
        plt.show()


def main():
    args = parse_args()
    orca_out = resolve_orca_out_path(args)
    result_a = parse_orca_output(orca_out)

    default_out_dir = os.path.dirname(orca_out) or "."
    out_path = args.out or os.path.join(default_out_dir, "qmmm_summary.png")

    if args.compare_to:
        result_b = parse_orca_output(args.compare_to)
        plot_comparison(result_a, result_b, args.labels, args.title, out_path, args.show)
    else:
        plot_single(result_a, args.title, out_path, args.show)

    # Console summary, useful even without opening the image
    print("\nSummary:")
    print(f"  Energy: {result_a.energy_hartree:.6f} Hartree "
          f"({result_a.energy_kcalmol:,.2f} kcal/mol)" if result_a.energy_hartree else "  No energy parsed.")
    extreme = result_a.most_negative_atom()
    if extreme:
        idx, q = extreme
        print(f"  Most negative atom: {result_a.elements.get(idx, '?')}{idx} = {q:+.4f} e")


if __name__ == "__main__":
    main()
