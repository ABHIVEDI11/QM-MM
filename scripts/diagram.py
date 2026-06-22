#!/usr/bin/env python3
"""
diagram.py — professional QM/MM illustrative diagrams with rich dark backgrounds

Produces two PNGs:
  1. qmmm_concept.png    — QM region embedded in an MM point-charge field
  2. binding_pocket.png  — a cartoon ligand H-bonding inside a binding pocket

Usage:
    python scripts/diagram.py
    python scripts/diagram.py --out-dir docs/images
    python scripts/diagram.py --residue "Gln102" --ligand-label "JZ4" \
        --delta-q -0.028 --distance 2.8
"""

import argparse
import os

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyBboxPatch, FancyArrowPatch, Arc
from matplotlib.colors import LinearSegmentedColormap

# ── colour palette (white background, professional/print style) ───────────────
BG          = "#ffffff"
PANEL_BG    = "#f5f7fa"
CARD_BG     = "#ffffff"
GRID        = "#e7eaf0"
BORDER      = "#9aa7ba"
TEXT        = "#1f2937"
SUBTEXT     = "#5b6776"
MUTED       = "#8a96a8"
GREEN       = "#1f9d6b"
GREEN_DIM   = "#2fae7c"
BLUE        = "#2f6fed"
BLUE_DIM    = "#1d4fc0"
RED         = "#dc3a56"
YELLOW      = "#c9790f"
PURPLE      = "#7c4fd1"
CYAN        = "#0e8fa3"
WHITE       = "#ffffff"

GLOW_SHADOW = [pe.withStroke(linewidth=5, foreground="#1f9d6b20")]


def _fig(w, h):
    fig, ax = plt.subplots(figsize=(w, h), facecolor=BG)
    ax.set_facecolor(BG)
    ax.axis("off")
    return fig, ax


def _gradient_circle(ax, cx, cy, r, color_inner, color_outer, zorder=1, steps=40):
    """Draw a filled circle with a radial gradient using concentric rings."""
    for i in range(steps, 0, -1):
        frac = i / steps
        # blend inner -> outer
        ri = int(int(color_inner[1:3], 16) * frac + int(color_outer[1:3], 16) * (1 - frac))
        gi = int(int(color_inner[3:5], 16) * frac + int(color_outer[3:5], 16) * (1 - frac))
        bi = int(int(color_inner[5:7], 16) * frac + int(color_outer[5:7], 16) * (1 - frac))
        col = f"#{ri:02x}{gi:02x}{bi:02x}"
        c = Circle((cx, cy), r * frac, facecolor=col, edgecolor="none",
                   zorder=zorder, alpha=0.7)
        ax.add_patch(c)


def _glow_circle(ax, cx, cy, r, color, linewidth=2.0, zorder=5, alpha_halo=0.18, n_halo=4):
    """Draw a circle with a soft glowing halo."""
    for i in range(n_halo, 0, -1):
        c = Circle((cx, cy), r + i * 0.12, facecolor="none",
                   edgecolor=color, linewidth=linewidth * 0.5,
                   alpha=alpha_halo / i, zorder=zorder - 1)
        ax.add_patch(c)
    c = Circle((cx, cy), r, facecolor="none", edgecolor=color,
               linewidth=linewidth, zorder=zorder)
    ax.add_patch(c)


# =============================================================================
# Diagram 1 — QM/MM concept
# =============================================================================

def draw_qmmm_concept(out_path, show=False):
    fig, ax = _fig(11, 10)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 10)
    ax.set_aspect("equal")

    # ── background grid (subtle) ───────────────────────────────────────────
    for x in np.arange(0, 11, 0.8):
        ax.axvline(x, color=GRID, lw=0.3, alpha=0.4)
    for y in np.arange(0, 10, 0.8):
        ax.axhline(y, color=GRID, lw=0.3, alpha=0.4)

    # ── title block ───────────────────────────────────────────────────────
    ax.text(0.5, 9.6, "QM/MM: Two Levels of Theory, One System",
            fontsize=17, fontweight="bold", color=TEXT,
            path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
    ax.text(0.5, 9.18,
            "The QM region's wavefunction is solved inside the electric field of every MM atom.",
            fontsize=10, color=SUBTEXT)

    cx, cy = 5.5, 4.7

    # ── outer MM box ──────────────────────────────────────────────────────
    box = FancyBboxPatch((0.35, 0.55), 10.3, 8.0,
                          boxstyle="round,pad=0,rounding_size=0.25",
                          linewidth=1.6, edgecolor=BORDER,
                          facecolor=PANEL_BG, zorder=0)
    ax.add_patch(box)
    # corner label
    ax.text(0.6, 8.3, "MM  region", fontsize=9.5, color=SUBTEXT,
            style="italic", alpha=0.8)
    ax.text(0.6, 7.98, "Classical force field  ·  fixed point charges",
            fontsize=8.2, color=MUTED, style="italic")

    # ── scattered MM point charges ────────────────────────────────────────
    rng = np.random.default_rng(42)
    n_pts = 90
    pts = []
    while len(pts) < n_pts:
        x = rng.uniform(0.7, 10.3)
        y = rng.uniform(0.8, 8.3)
        if np.hypot(x - cx, y - cy) > 2.5:
            pts.append((x, y))
    pts = np.array(pts[:n_pts])
    signs = rng.choice([-1, 1], size=n_pts, p=[0.48, 0.52])
    for (x, y), s in zip(pts, signs):
        col = RED if s < 0 else BLUE
        ax.scatter(x, y, s=35, c=col, alpha=0.55, linewidths=0, zorder=2)
        symbol = "−" if s < 0 else "+"
        ax.text(x, y, symbol, fontsize=6, color=col, ha="center", va="center",
                fontweight="bold", alpha=0.9, zorder=3)

    # ── electric field lines from MM charges toward QM centre ─────────────
    field_sources = pts[rng.choice(len(pts), size=14, replace=False)]
    for fx, fy in field_sources:
        dx, dy = cx - fx, cy - fy
        dist = np.hypot(dx, dy)
        # stop arrow just outside the QM halo
        ex = fx + dx * (dist - 2.55) / dist
        ey = fy + dy * (dist - 2.55) / dist
        ax.annotate("", xy=(ex, ey), xytext=(fx, fy),
                    arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=0.8,
                                   mutation_scale=6, alpha=0.5),
                    zorder=2)

    # ── QM region — glowing green circle ──────────────────────────────────
    # soft glow halos
    for i in range(6, 0, -1):
        c = Circle((cx, cy), 2.0 + i * 0.18, facecolor="none",
                   edgecolor=GREEN, linewidth=1.0,
                   alpha=0.06, zorder=3)
        ax.add_patch(c)
    # filled interior
    qm_fill = Circle((cx, cy), 2.0, facecolor="#eafbf3", edgecolor=GREEN,
                     linewidth=2.5, zorder=4)
    ax.add_patch(qm_fill)

    # ── small molecule inside QM (benzene-like ring + oxygen) ─────────────
    def ring_vertex(k, cx=cx, cy=cy, r=0.75, offset_y=0.05):
        angle = np.pi / 2 + k * (2 * np.pi / 6)
        return cx + r * np.cos(angle), cy + r * np.sin(angle) + offset_y

    ring = [ring_vertex(k) for k in range(6)]
    # bonds
    for i in range(6):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % 6]
        ax.plot([x0, x1], [y0, y1], color=TEXT, lw=2.0, zorder=6)
    # alternate double bonds (inner offset)
    for i in [0, 2, 4]:
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % 6]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = -(my - cy) * 0.12, (mx - cx) * 0.12
        ax.plot([x0 + dx * 0.5, x1 + dx * 0.5],
                [y0 + dy * 0.5, y1 + dy * 0.5], color=TEXT, lw=1.0, alpha=0.6, zorder=6)
    # atoms
    for x, y in ring:
        ax.scatter(x, y, s=55, color=CARD_BG, edgecolor=TEXT, linewidth=1.2, zorder=7)
    # oxygen substituent
    ox, oy = cx - 1.45, cy + 0.62
    ax.plot([ring[0][0], ox], [ring[0][1], oy], color=TEXT, lw=2.0, zorder=6)
    _glow_circle(ax, ox, oy, 0.27, RED, linewidth=1.5, zorder=8, alpha_halo=0.25)
    ax.add_patch(Circle((ox, oy), 0.27, facecolor=RED, edgecolor="none", zorder=8, alpha=0.9))
    ax.text(ox, oy, "O", fontsize=9, color=WHITE, ha="center", va="center",
            fontweight="bold", zorder=9)

    # ── Hamiltonian equation ───────────────────────────────────────────────
    ax.text(cx, cy - 1.52, r"$\hat{H}_{\mathrm{eff}}\,\Psi = E\,\Psi$",
            fontsize=13, color=GREEN, ha="center", style="italic", zorder=6,
            path_effects=[pe.withStroke(linewidth=4, foreground="#eafbf3")])

    # ── QM label ──────────────────────────────────────────────────────────
    ax.text(cx, cy + 1.62, "QM  region", fontsize=12, fontweight="bold",
            color=GREEN, ha="center", zorder=6)
    ax.text(cx, cy + 1.18, "wavefunction solved by DFT / ab initio",
            fontsize=8.0, color=GREEN_DIM, ha="center", zorder=6)

    # ── legend ────────────────────────────────────────────────────────────
    legend_handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=GREEN, markeredgecolor=GREEN, markersize=11,
               label="QM region — electron density solved quantum-mechanically"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=RED, markeredgecolor="none", markersize=9,
               label="MM point charge (negative)"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=BLUE, markeredgecolor="none", markersize=9,
               label="MM point charge (positive)"),
        Line2D([0], [0], color=MUTED, lw=1.2,
               marker=">", markersize=5,
               label="Electric field contribution to Hamiltonian"),
    ]
    ax.legend(handles=legend_handles, loc="lower center",
              bbox_to_anchor=(0.5, -0.02), ncol=2, frameon=False,
              fontsize=9, labelcolor=SUBTEXT,
              handletextpad=0.7, columnspacing=1.4)

    fig.savefig(out_path, dpi=200, facecolor=BG, bbox_inches="tight")
    print(f"Saved -> {out_path}")
    if show:
        plt.show()
    plt.close(fig)


# =============================================================================
# Diagram 2 — binding-pocket cartoon
# =============================================================================

def draw_binding_pocket(out_path, residue_label, ligand_label, distance, delta_q, show=False):
    fig, ax = _fig(13, 10.5)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 10.5)
    ax.set_aspect("equal")

    # background grid
    for x in np.arange(0, 13, 0.8):
        ax.axvline(x, color=GRID, lw=0.3, alpha=0.35)
    for y in np.arange(0, 10.5, 0.8):
        ax.axhline(y, color=GRID, lw=0.3, alpha=0.35)

    # ── title ─────────────────────────────────────────────────────────────
    ax.text(0.5, 10.1, "Inside the Binding Pocket",
            fontsize=17, fontweight="bold", color=TEXT,
            path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
    ax.text(0.5, 9.62,
            "QM/MM captures how the ligand's electron density responds to its protein environment — "
            "atom by atom.",
            fontsize=9.5, color=SUBTEXT)

    # ── pocket boundary ────────────────────────────────────────────────────
    pcx, pcy, pr = 5.5, 4.5, 4.0
    # soft glow for pocket
    for i in range(5, 0, -1):
        c = Circle((pcx, pcy), pr + i * 0.15, facecolor="none",
                   edgecolor=BORDER, linewidth=1.0, alpha=0.07 * i, zorder=0)
        ax.add_patch(c)
    pocket = Circle((pcx, pcy), pr, facecolor=PANEL_BG,
                    edgecolor=BORDER, linewidth=1.8,
                    linestyle=(0, (7, 4)), zorder=1)
    ax.add_patch(pocket)
    ax.text(pcx, pcy + pr + 0.42, "hydrophobic pocket",
            fontsize=9, color=SUBTEXT, ha="center", style="italic")

    # ── hydrophobic residues lining the pocket ─────────────────────────────
    hpos = [
        (pcx - 3.0, pcy - 0.9,  "Val"),
        (pcx - 1.6, pcy - 3.2,  "Leu"),
        (pcx + 0.1, pcy - 3.7,  "Ile"),
        (pcx + 1.8, pcy - 3.1,  "Phe"),
        (pcx + 3.0, pcy - 0.8,  "Trp"),
        (pcx + 2.5, pcy + 2.2,  "Met"),
        (pcx - 2.4, pcy + 2.3,  "Ala"),
    ]
    for hx, hy, hlabel in hpos:
        # glow
        for i in range(4, 0, -1):
            c = Circle((hx, hy), 0.52 + i * 0.08, facecolor="none",
                       edgecolor=GREEN_DIM, linewidth=0.8, alpha=0.05 * i, zorder=2)
            ax.add_patch(c)
        c = Circle((hx, hy), 0.52, facecolor="#eafbf3",
                   edgecolor=GREEN_DIM, linewidth=1.5, zorder=3)
        ax.add_patch(c)
        ax.text(hx, hy, hlabel[:1], fontsize=8.5, color=GREEN,
                ha="center", va="center", fontweight="bold", zorder=4)
        ax.text(hx, hy - 0.78, hlabel, fontsize=7.5, color=SUBTEXT,
                ha="center", va="top", zorder=4)

    # ── ligand ─────────────────────────────────────────────────────────────
    lig_cx, lig_cy = pcx + 0.1, pcy - 0.7
    def lring(k, r=0.72):
        a = np.pi / 2 + k * (2 * np.pi / 6)
        return lig_cx + r * np.cos(a), lig_cy + r * np.sin(a)

    lrpts = [lring(k) for k in range(6)]
    for i in range(6):
        x0, y0 = lrpts[i]; x1, y1 = lrpts[(i + 1) % 6]
        ax.plot([x0, x1], [y0, y1], color=TEXT, lw=2.2, zorder=6)
    for i in [0, 2, 4]:
        x0, y0 = lrpts[i]; x1, y1 = lrpts[(i + 1) % 6]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dx2 = -(my - lig_cy) * 0.11; dy2 = (mx - lig_cx) * 0.11
        ax.plot([x0 + dx2 * 0.5, x1 + dx2 * 0.5],
                [y0 + dy2 * 0.5, y1 + dy2 * 0.5],
                color=TEXT, lw=1.0, alpha=0.5, zorder=6)
    for x, y in lrpts:
        ax.scatter(x, y, s=50, color=CARD_BG, edgecolor=TEXT, linewidth=1.1, zorder=7)

    # hydrophobic tail
    tail = [lrpts[3],
            (lrpts[3][0] + 0.35, lrpts[3][1] - 0.65),
            (lrpts[3][0] + 0.08, lrpts[3][1] - 1.35)]
    ax.plot([p[0] for p in tail], [p[1] for p in tail],
            color=TEXT, lw=2.2, zorder=6)
    for x, y in tail[1:]:
        ax.scatter(x, y, s=50, color=CARD_BG, edgecolor=TEXT, linewidth=1.1, zorder=7)

    # hydroxyl oxygen
    ox, oy = lrpts[0][0] - 0.04, lrpts[0][1] + 0.98
    ax.plot([lrpts[0][0], ox], [lrpts[0][1], oy], color=TEXT, lw=2.2, zorder=6)
    for i in range(5, 0, -1):
        c = Circle((ox, oy), 0.24 + i * 0.07, facecolor="none",
                   edgecolor=RED, linewidth=0.8, alpha=0.07 * i, zorder=7)
        ax.add_patch(c)
    ax.add_patch(Circle((ox, oy), 0.24, facecolor=RED, edgecolor=TEXT,
                        linewidth=1.2, zorder=8))
    ax.text(ox, oy, "O", fontsize=9, color=WHITE, ha="center", va="center",
            fontweight="bold", zorder=9)

    # ligand label
    ax.text(lig_cx, lig_cy - 1.95, ligand_label, fontsize=11, fontweight="bold",
            color=YELLOW, ha="center", zorder=6)
    ax.text(lig_cx, lig_cy - 2.30, "QM region", fontsize=8.5, color=SUBTEXT,
            ha="center", zorder=6)

    # ── H-bonding residue ──────────────────────────────────────────────────
    res_x, res_y = ox, oy + 2.25
    for i in range(5, 0, -1):
        c = Circle((res_x, res_y), 0.55 + i * 0.08, facecolor="none",
                   edgecolor=BLUE, linewidth=0.8, alpha=0.06 * i, zorder=6)
        ax.add_patch(c)
    ax.add_patch(Circle((res_x, res_y), 0.55, facecolor=BLUE_DIM,
                        edgecolor=BLUE, linewidth=2.0, zorder=7))
    ax.text(res_x, res_y + 0.10, "N", fontsize=11, color=WHITE, ha="center",
            fontweight="bold", zorder=8)
    ax.text(res_x, res_y - 0.22, residue_label, fontsize=6.5, color=CYAN,
            ha="center", zorder=8)

    # H atom
    h_x, h_y = res_x, res_y - 1.0
    ax.plot([res_x, h_x], [res_y - 0.55, h_y], color=TEXT, lw=1.6, zorder=7)
    ax.add_patch(Circle((h_x, h_y), 0.16, facecolor="#cccccc",
                        edgecolor=TEXT, linewidth=1.0, zorder=8))
    ax.text(h_x + 0.32, h_y, "H", fontsize=8.5, color=TEXT, ha="left", va="center")

    # H-bond dashed line
    ax.plot([h_x, ox], [h_y, oy + 0.24], color=YELLOW, lw=2.0,
            linestyle=(0, (5, 3.5)), zorder=6)
    mid_x, mid_y = (h_x + ox) / 2 + 0.55, (h_y + oy) / 2
    hbbox = dict(boxstyle="round,pad=0.35", facecolor=CARD_BG,
                 edgecolor=YELLOW, linewidth=1.2)
    ax.text(mid_x, mid_y, f"H-bond\n{distance:.1f} Å",
            fontsize=9, color=YELLOW, ha="left", va="center",
            fontweight="bold", bbox=hbbox, zorder=9)

    # ── charge-shift info panel (right side) ───────────────────────────────
    px0, py0, pw, ph = 9.55, 5.35, 3.05, 4.0
    panel = FancyBboxPatch((px0, py0), pw, ph,
                            boxstyle="round,pad=0.12,rounding_size=0.18",
                            facecolor=CARD_BG, edgecolor=BORDER,
                            linewidth=1.6, zorder=9)
    ax.add_patch(panel)

    # panel title
    ax.text(px0 + 0.18, py0 + ph - 0.22, "What QM/MM Captures",
            fontsize=10.5, fontweight="bold", color=TEXT, va="top", zorder=10)
    ax.axhline(py0 + ph - 0.60, xmin=(px0) / 13, xmax=(px0 + pw) / 13,
               color=BORDER, lw=1.0, zorder=10)

    sign_str = "more negative" if delta_q < 0 else "more positive"
    lines = [
        (0.45, GREEN,  "✓  Polarization effects"),
        (0.22, SUBTEXT, "Classical MM cannot capture\ncharge redistribution"),
    ]
    y_cursor = py0 + ph - 0.82
    for txt, col, content in lines:
        ax.text(px0 + 0.18, y_cursor, content, fontsize=8.5, color=col,
                va="top", zorder=10)
        y_cursor -= 0.55

    # big delta-q display
    ax.text(px0 + 0.18, y_cursor - 0.1, "O atom charge shift:", fontsize=8.5,
            color=SUBTEXT, va="top", zorder=10)
    ax.text(px0 + pw / 2, y_cursor - 0.72, f"Δq = {delta_q:+.3f} e",
            fontsize=16, color=YELLOW, ha="center", fontweight="bold",
            family="monospace", zorder=10,
            path_effects=[pe.withStroke(linewidth=4, foreground=CARD_BG)])
    ax.text(px0 + pw / 2, y_cursor - 1.25, f"({sign_str}\nvs. gas phase)",
            fontsize=8, color=SUBTEXT, ha="center", va="top", zorder=10)

    # mini bar chart inside panel
    bar_y = py0 + 0.45
    bar_h = 0.36
    bar_vals = [0.0, delta_q]
    bar_cols = [MUTED, YELLOW]
    bar_labels = ["gas phase", "in pocket"]
    bw = 0.6
    xs = [px0 + 0.55, px0 + 1.65]
    for bx, bv, bc, bl in zip(xs, bar_vals, bar_cols, bar_labels):
        height = abs(bv) * 4.5 + 0.05
        by = bar_y
        ax.bar(bx, height if bv >= 0 else -height, width=bw,
               bottom=bar_y, color=bc, alpha=0.85, zorder=10)
        ax.text(bx, by - 0.25, bl, fontsize=7, color=SUBTEXT,
                ha="center", va="top", zorder=10)
    ax.axhline(bar_y, xmin=px0 / 13, xmax=(px0 + pw) / 13,
               color=MUTED, lw=0.8, zorder=10)

    # ── legend bottom ──────────────────────────────────────────────────────
    legend_handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=GREEN_DIM, markeredgecolor=GREEN_DIM, markersize=10,
               label="Hydrophobic pocket residues (MM region)"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=BLUE, markeredgecolor=BLUE, markersize=10,
               label="H-bond donor residue (MM)"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=RED, markeredgecolor="none", markersize=10,
               label="Electronegative atom (QM region)"),
        Line2D([0], [0], color=YELLOW, lw=2, linestyle="--",
               label="Hydrogen bond"),
    ]
    ax.legend(handles=legend_handles, loc="lower left",
              bbox_to_anchor=(0.0, -0.16), ncol=2, frameon=False,
              fontsize=8.5, labelcolor=SUBTEXT, handletextpad=0.6)

    fig.savefig(out_path, dpi=200, facecolor=BG, bbox_inches="tight")
    print(f"Saved -> {out_path}")
    if show:
        plt.show()
    plt.close(fig)


# =============================================================================
# main
# =============================================================================

def parse_args():
    p = argparse.ArgumentParser(description="Generate professional QM/MM diagrams.")
    p.add_argument("--out-dir", default="docs/images")
    p.add_argument("--residue", default="Gln102")
    p.add_argument("--ligand-label", default="Ligand")
    p.add_argument("--distance", type=float, default=2.8)
    p.add_argument("--delta-q", type=float, default=-0.028)
    p.add_argument("--show", action="store_true")
    return p.parse_args()


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
