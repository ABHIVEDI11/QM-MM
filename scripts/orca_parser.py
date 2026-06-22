"""
orca_parser.py — parse energy and Mulliken charges out of an ORCA output file.

This is intentionally standalone (no OpenMM/ORCA dependency) so it can be
reused by visualize_results.py, or imported into a notebook, without needing
the full simulation environment installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

HARTREE_TO_EV = 27.211396
HARTREE_TO_KCALMOL = 627.509


@dataclass
class QMMMResult:
    terminated_normally: bool
    energy_hartree: float | None
    mulliken_charges: dict[int, float] = field(default_factory=dict)  # local index -> charge
    elements: dict[int, str] = field(default_factory=dict)            # local index -> element symbol

    @property
    def energy_ev(self) -> float | None:
        return self.energy_hartree * HARTREE_TO_EV if self.energy_hartree is not None else None

    @property
    def energy_kcalmol(self) -> float | None:
        return self.energy_hartree * HARTREE_TO_KCALMOL if self.energy_hartree is not None else None

    def most_negative_atom(self) -> tuple[int, float] | None:
        if not self.mulliken_charges:
            return None
        idx = min(self.mulliken_charges, key=self.mulliken_charges.get)
        return idx, self.mulliken_charges[idx]

    def most_positive_atom(self) -> tuple[int, float] | None:
        if not self.mulliken_charges:
            return None
        idx = max(self.mulliken_charges, key=self.mulliken_charges.get)
        return idx, self.mulliken_charges[idx]


def parse_orca_output(path: str) -> QMMMResult:
    """Parse an ORCA .out file into a QMMMResult."""
    with open(path) as f:
        text = f.read()
    lines = text.split("\n")

    terminated_normally = "ORCA TERMINATED NORMALLY" in text

    energy_hartree = None
    for line in reversed(lines):
        if "FINAL SINGLE POINT ENERGY" in line:
            try:
                energy_hartree = float(line.split()[-1])
            except (ValueError, IndexError):
                pass
            break

    mulliken, elements, reading = {}, {}, False
    for line in lines:
        if "MULLIKEN ATOMIC CHARGES" in line:
            reading = True
            continue
        if reading:
            if "Sum of atomic charges" in line:
                break
            parts = line.split()
            # Expected format: "  0   O :   -0.200265"
            if len(parts) >= 4 and parts[2] == ":":
                try:
                    idx = int(parts[0])
                    mulliken[idx] = float(parts[-1])
                    elements[idx] = parts[1]
                except (ValueError, IndexError):
                    pass

    return QMMMResult(
        terminated_normally=terminated_normally,
        energy_hartree=energy_hartree,
        mulliken_charges=mulliken,
        elements=elements,
    )
