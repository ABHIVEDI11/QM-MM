#!/usr/bin/env python3
"""
diagram.py — illustrative QM/MM diagrams (concept + binding pocket cartoon)

These are schematic, not data plots: they explain *what a QM/MM calculation
is* and *what it looks like inside a binding pocket*, independent of any
particular protein or ligand. Useful as figures in a README, report, or
presentation.

Produces two PNGs:
  1. qmmm_concept.png    — QM region embedded in an MM point-charge field
  2. binding_pocket.png  — a generic ligand H-bonding to a residue inside
                            a hydrophobic pocket, with a charge-shift callout

Usage:
    python scripts/diagram.py
    python scripts/diagram.py --out-dir docs/images
    python scripts/diagram.py --residue "Gln102" --ligand-label "Ligand" \\
        --delta-q -0.028 --distance 2.8
"""

import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyBboxPatch

# -----------------------------------------------------------------------------
# Shared visual style (matches visualize_results.py)
# -----------------------------------------------------------------------------
BG = "#0f1419"
PANEL_BG = "#161b22"
GRID = "#2a313c"
TEXT = "#e6edf3"
SUBTEXT = "#8b949e"
ACCENT_NEG = "#ef5350"
ACCENT_POS = "#42a5f5"
ACCENT_HIGHLIGHT = "#ffca28"
ACCENT_GREEN = "#66bb6a"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "text.color": TEXT,
    "font.size": 10.5,
    "font.family": "DejaVu Sans",
})


def parse_args():
    p = argparse.ArgumentParser(description="Generate illustrative QM/MM diagrams.")
    p.add_argument("--out-dir", default="docs/images", help="Where to save the PNGs")
    p.add_argument("--residue", default="Residue X",
                   help="Label for the H-bonding residue in the pocket cartoon")
    p.add_argument("--ligand-label", default="Ligand",
                   help="Label for the ligand in the pocket cartoon")
    p.add_argument("--distance", type=float, default=2.8,
                   help="H-bond distance in Angstrom, shown on the cartoon")
    p.add_argument("--delta-q", type=float, default=-0.028,
                   help="Example charge shift (e) to annotate, gas -> environment")
    p.add_argument("--show", action="store_true")
    return p.parse_args()


# =============================================================================
# Diagram 1 — QM/MM concept
# =============================================================================

def draw_qmmm_concept(out_path, show=False):
    fig, ax = plt.subplots(figsize=(9.0, 9.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9.2)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(0.3, 8.7, "QM/MM: Two Levels of Theory, One System",
            fontsize=15, fontweight="bold", color=TEXT)
    ax.text(0.3, 8.25, "The part you care about is solved exactly; everything else is a fixed electric field",
            fontsize=9.5, color=SUBTEXT)

    cx, cy = 5.0, 4.5

    # Outer MM region (periodic box)
    box = FancyBboxPatch((0.6, 0.6), 8.8, 6.6, boxstyle="round,pad=0,rounding_size=0.15",
                          linewidth=1.4, edgecolor=GRID, facecolor=PANEL_BG, zorder=0)
    ax.add_patch(box)
    ax.text(0.9, 6.95, "MM region — classical force field", fontsize=10, color=SUBTEXT,
            style="italic")

    # scattered MM point charges (water / protein atoms)
    rng = np.random.default_rng(7)
    n_pts = 70
    pts = []
    while len(pts) < n_pts:
        x = rng.uniform(1.1, 8.9)
        y = rng.uniform(1.1, 6.8)
        if np.hypot(x - cx, y - cy) > 2.15:
            pts.append((x, y))
    pts = np.array(pts)
    signs = rng.choice([-1, 1], size=len(pts), p=[0.5, 0.5])
    colors = np.where(signs < 0, ACCENT_NEG, ACCENT_POS)
    ax.scatter(pts[:, 0], pts[:, 1], s=26, c=colors, alpha=0.55, linewidths=0, zorder=1)

    # faint field lines radiating from a few MM charges toward the QM region
    field_sources = pts[rng.choice(len(pts), size=10, replace=False)]
    for fx, fy in field_sources:
        ax.annotate(
            "", xy=(cx, cy), xytext=(fx, fy),
            arrowprops=dict(arrowstyle="-", color=GRID, lw=0.7, alpha=0.6,
                             connectionstyle="arc3,rad=0.05"),
            zorder=1,
        )

    # QM region circle
    qm_circle = Circle((cx, cy), 1.95, facecolor="#0d2b1a", edgecolor=ACCENT_GREEN,
                        linewidth=2.2, zorder=2)
    ax.add_patch(qm_circle)
    ax.text(cx, cy + 1.55, "QM region", fontsize=11, fontweight="bold",
            color=ACCENT_GREEN, ha="center", zorder=3)
    ax.text(cx, cy + 1.22, "(your ligand)", fontsize=8.5, color=SUBTEXT, ha="center", zorder=3)

    # small molecule sketch inside QM circle: a simple ring + substituent
    mol_pts = {
        "C1": (cx - 0.55, cy + 0.35), "C2": (cx + 0.05, cy + 0.55),
        "C3": (cx + 0.55, cy + 0.15), "C4": (cx + 0.4, cy - 0.45),
        "C5": (cx - 0.2, cy - 0.6), "C6": (cx - 0.65, cy - 0.2),
    }
    ring_order = ["C1", "C2", "C3", "C4", "C5", "C6", "C1"]
    ring_xy = [mol_pts[k] for k in ring_order]
    ax.plot([p[0] for p in ring_xy], [p[1] for p in ring_xy],
            color=TEXT, lw=1.6, zorder=4)
    for k, (x, y) in mol_pts.items():
        ax.scatter(x, y, s=46, color="#3d3d3d", edgecolor=TEXT, linewidth=0.8, zorder=5)
    ox, oy = cx - 1.05, cy + 0.55
    ax.plot([mol_pts["C1"][0], ox], [mol_pts["C1"][1], oy], color=TEXT, lw=1.6, zorder=4)
    ax.scatter(ox, oy, s=80, color=ACCENT_NEG, edgecolor=TEXT, linewidth=0.8, zorder=5)
    ax.text(ox - 0.05, oy + 0.28, "O", fontsize=9, color=ACCENT_NEG, ha="center", fontweight="bold")

    # Schrodinger callout
    ax.text(cx, cy - 1.55, r"$\hat{H}\Psi = E\Psi$  solved here", fontsize=9.5,
            color=ACCENT_GREEN, ha="center", style="italic", zorder=3)

    # Clean legend using proxy handles
    legend_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=ACCENT_GREEN,
               markeredgecolor=ACCENT_GREEN, markersize=10,
               label="QM region — wavefunction solved by ab initio / DFT"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=ACCENT_NEG,
               markeredgecolor="none", markersize=9, label="MM point charge (negative)"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=ACCENT_POS,
               markeredgecolor="none", markersize=9, label="MM point charge (positive)"),
    ]
    ax.legend(handles=legend_handles, loc="lower center", bbox_to_anchor=(0.5, -0.13),
              ncol=1, frameon=False, fontsize=9.2, labelcolor=SUBTEXT,
              handletextpad=0.6, borderaxespad=0)

    fig.savefig(out_path, dpi=180, facecolor=BG, bbox_inches="tight")
    print(f"Saved -> {out_path}")
    if show:
        plt.show()
    plt.close(fig)


# =============================================================================
# Diagram 2 — generic binding-pocket cartoon
# =============================================================================

def draw_binding_pocket(out_path, residue_label, ligand_label, distance, delta_q, show=False):
    fig, ax = plt.subplots(figsize=(9.8, 9.0))
    ax.set_xlim(0, 11.6)
    ax.set_ylim(0, 10.7)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(0.3, 10.25, "Inside the Binding Pocket",
            fontsize=15, fontweight="bold", color=TEXT)
    ax.text(0.3, 9.72,
            "A generic H-bond between a ligand and a pocket residue — the kind of\n"
            "interaction QM/MM lets you quantify, atom by atom",
            fontsize=9.3, color=SUBTEXT, va="top")

    pocket_cx, pocket_cy, pocket_r = 5.3, 4.3, 3.55
    pocket = Circle((pocket_cx, pocket_cy), pocket_r, facecolor=PANEL_BG,
                     edgecolor=GRID, linewidth=1.5, linestyle=(0, (6, 4)), zorder=0)
    ax.add_patch(pocket)
    ax.text(pocket_cx, pocket_cy + pocket_r + 0.35, "hydrophobic pocket wall",
            fontsize=8.5, color=SUBTEXT, ha="center", style="italic")

    # hydrophobic residues lining the lower half of the pocket (decorative, generic labels)
    hydrophobic_positions = [
        (pocket_cx - 2.5, pocket_cy - 1.15, "Hydrophobic\nresidue"),
        (pocket_cx - 1.3, pocket_cy - 2.65, "Hydrophobic\nresidue"),
        (pocket_cx + 1.35, pocket_cy - 2.65, "Hydrophobic\nresidue"),
        (pocket_cx + 2.5, pocket_cy - 1.15, "Hydrophobic\nresidue"),
    ]
    for x, y, label in hydrophobic_positions:
        circ = Circle((x, y), 0.48, facecolor="#163a24", edgecolor=ACCENT_GREEN,
                       linewidth=1.4, zorder=2)
        ax.add_patch(circ)
        ax.text(x, y - 0.78, label, fontsize=7.2, color=SUBTEXT, ha="center", va="top")

    # ligand (simple ring + hydrophobic tail), lower-center of the pocket,
    # tail pointing down into the hydrophobic residues, head pointing up
    lig_cx, lig_cy = pocket_cx + 0.1, pocket_cy - 0.95
    mol_pts = {
        "C1": (lig_cx - 0.5, lig_cy + 0.32), "C2": (lig_cx + 0.05, lig_cy + 0.5),
        "C3": (lig_cx + 0.5, lig_cy + 0.13), "C4": (lig_cx + 0.36, lig_cy - 0.4),
        "C5": (lig_cx - 0.18, lig_cy - 0.55), "C6": (lig_cx - 0.58, lig_cy - 0.18),
    }
    ring_order = ["C1", "C2", "C3", "C4", "C5", "C6", "C1"]
    ring_xy = [mol_pts[k] for k in ring_order]
    ax.plot([p[0] for p in ring_xy], [p[1] for p in ring_xy], color=TEXT, lw=1.8, zorder=5)
    for k, (x, y) in mol_pts.items():
        ax.scatter(x, y, s=42, color="#3d3d3d", edgecolor=TEXT, linewidth=0.8, zorder=6)

    chain_pts = [mol_pts["C4"], (mol_pts["C4"][0] + 0.3, mol_pts["C4"][1] - 0.7),
                 (mol_pts["C4"][0] + 0.05, mol_pts["C4"][1] - 1.4)]
    ax.plot([p[0] for p in chain_pts], [p[1] for p in chain_pts], color=TEXT, lw=1.8, zorder=5)
    for x, y in chain_pts[1:]:
        ax.scatter(x, y, s=42, color="#3d3d3d", edgecolor=TEXT, linewidth=0.8, zorder=6)

    # hydroxyl oxygen pointing straight up toward the H-bonding residue
    ox, oy = mol_pts["C1"][0] - 0.05, mol_pts["C1"][1] + 0.85
    ax.plot([mol_pts["C1"][0], ox], [mol_pts["C1"][1], oy], color=TEXT, lw=1.8, zorder=5)
    o_circle = Circle((ox, oy), 0.21, facecolor=ACCENT_NEG, edgecolor=TEXT,
                       linewidth=1.0, zorder=7)
    ax.add_patch(o_circle)
    ax.text(ox, oy, "O", fontsize=9, color="white", ha="center", va="center",
            fontweight="bold", zorder=8)

    ax.text(lig_cx, lig_cy - 1.95, ligand_label, fontsize=10.5, fontweight="bold",
            color=ACCENT_HIGHLIGHT, ha="center")
    ax.text(lig_cx, lig_cy - 2.28, "(QM region)", fontsize=8, color=SUBTEXT, ha="center")

    # H-bonding residue, directly above the oxygen with clear vertical separation
    res_x, res_y = ox, oy + 2.0
    res_circle = Circle((res_x, res_y), 0.5, facecolor="#0d2440", edgecolor=ACCENT_POS,
                         linewidth=1.6, zorder=7)
    ax.add_patch(res_circle)
    ax.text(res_x, res_y + 0.12, "N", fontsize=10, color="white", ha="center",
            fontweight="bold", zorder=8)
    ax.text(res_x, res_y - 0.18, residue_label, fontsize=7.0, color="white", ha="center", zorder=8)

    # H attached to the residue, hanging down toward the oxygen
    h_x, h_y = res_x, res_y - 0.85
    ax.plot([res_x, h_x], [res_y - 0.5, h_y], color="white", lw=1.4, zorder=6)
    ax.scatter(h_x, h_y, s=55, color="#cccccc", edgecolor=TEXT, linewidth=0.8, zorder=7)
    ax.text(h_x + 0.28, h_y, "H", fontsize=8, color=TEXT, ha="left", va="center")

    # H-bond dashed line from H down to O; label offset to the right, clear of both atoms
    ax.plot([h_x, ox], [h_y, oy + 0.21], color=ACCENT_HIGHLIGHT, lw=1.6,
            linestyle=(0, (5, 4)), zorder=6)
    mid_x, mid_y = (h_x + ox) / 2, (h_y + oy) / 2
    ax.text(mid_x + 0.45, mid_y, f"H-bond\n{distance:.1f} \u00c5", fontsize=8.6,
            color=ACCENT_HIGHLIGHT, ha="left", va="center", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=BG, edgecolor=ACCENT_HIGHLIGHT,
                      linewidth=0.8))

    # charge-shift callout panel, top-right corner, clear of the pocket circle
    panel = FancyBboxPatch((8.85, 6.55), 2.55, 2.85, boxstyle="round,pad=0.08,rounding_size=0.12",
                            facecolor=PANEL_BG, edgecolor=GRID, linewidth=1.2, zorder=9)
    ax.add_patch(panel)
    px = 9.08
    ax.text(px, 9.0, "What QM/MM\ncaptures", fontsize=9.5, fontweight="bold",
            color=TEXT, zorder=10, va="top")
    ax.text(px, 8.25, "O charge shifts by", fontsize=8.3, color=SUBTEXT, zorder=10)
    sign = "more negative" if delta_q < 0 else "more positive"
    ax.text(px, 7.78, f"\u0394q = {delta_q:+.3f} e", fontsize=12.5, color=ACCENT_HIGHLIGHT,
            fontweight="bold", family="monospace", zorder=10)
    ax.text(px, 7.38, f"({sign} vs.\ngas phase)", fontsize=7.8, color=SUBTEXT, zorder=10, va="top")
    ax.text(px, 6.78, "A fixed-charge force\nfield cannot reproduce\nthis.",
            fontsize=7.4, color=SUBTEXT, va="top", zorder=10)

    fig.savefig(out_path, dpi=180, facecolor=BG, bbox_inches="tight")
    print(f"Saved -> {out_path}")
    if show:
        plt.show()
    plt.close(fig)


def main():
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    draw_qmmm_concept(os.path.join(args.out_dir, "qmmm_concept.png"), show=args.show)
    draw_binding_pocket(
        os.path.join(args.out_dir, "binding_pocket.png"),
        residue_label=args.residue,
        ligand_label=args.ligand_label,
        distance=args.distance,
        delta_q=args.delta_q,
        show=args.show,
    )


if __name__ == "__main__":
    main()
