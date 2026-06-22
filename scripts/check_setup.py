#!/usr/bin/env python3
"""
check_setup.py — QM/MM environment checker

Run this first, before anything else in this toolkit, to confirm that
OpenMM and ORCA are correctly installed and reachable.

Usage:
    python scripts/check_setup.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qmmm_common import find_orca  # noqa: E402

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    GREEN, RED, YELLOW, CYAN = (
        Fore.GREEN + Style.BRIGHT,
        Fore.RED + Style.BRIGHT,
        Fore.YELLOW + Style.BRIGHT,
        Fore.CYAN + Style.BRIGHT,
    )
    RESET = Style.RESET_ALL
except ImportError:
    GREEN = RED = YELLOW = CYAN = RESET = ""

results = []  # (label, ok, detail)


def record(label, ok, detail=""):
    results.append((label, ok, detail))
    tag = f"{GREEN}OK{RESET}" if ok else f"{RED}FAIL{RESET}"
    print(f"  [{tag}]  {label:<32} {detail}")


# -----------------------------------------------------------------------------
def check_python_packages():
    print(f"\n{CYAN}[1/3] Python packages{RESET}")
    print("  " + "-" * 56)
    for mod in ("numpy", "matplotlib", "openmm", "yaml"):
        try:
            imported = __import__(mod)
            ver = getattr(imported, "__version__", "installed")
            record(mod, True, f"version {ver}")
        except ImportError:
            record(mod, False, f"not found — pip install {mod}")


# -----------------------------------------------------------------------------
def check_orca_binary():
    print(f"\n{CYAN}[2/3] ORCA installation{RESET}")
    print("  " + "-" * 56)

    orca_path = find_orca("orca")
    if orca_path is None:
        record("ORCA binary", False, "not found — add ORCA to PATH or set orca.path in config.yaml")
        return None

    try:
        result = subprocess.run(
            [orca_path, "--version"], capture_output=True, text=True, timeout=15
        )
        ver_line = (result.stdout + result.stderr).strip().splitlines()
        ver_str = ver_line[0] if ver_line else "unknown version"
        record("ORCA binary", True, f"found at {orca_path}")
        record("ORCA version", True, ver_str)
    except subprocess.TimeoutExpired:
        record("ORCA version", False, "timed out checking version")
    except Exception as e:
        record("ORCA binary (run)", False, str(e))

    return orca_path


# -----------------------------------------------------------------------------
def test_openmm_tip3p():
    print(f"\n{CYAN}[3/3] Functional tests{RESET}")
    print("  " + "-" * 56)
    try:
        import openmm as mm
        import openmm.app as app
        import openmm.unit as unit

        pdb_text = """\
ATOM      1  O   WAT A   1       0.000   0.000   0.000  1.00  0.00           O
ATOM      2  H1  WAT A   1       0.957   0.000   0.000  1.00  0.00           H
ATOM      3  H2  WAT A   1      -0.240   0.927   0.000  1.00  0.00           H
END
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pdb", delete=False) as f:
            f.write(pdb_text)
            tmp_pdb = f.name

        pdb = app.PDBFile(tmp_pdb)
        forcefield = app.ForceField("tip3p.xml")
        system = forcefield.createSystem(pdb.topology, nonbondedMethod=app.NoCutoff)
        integrator = mm.LangevinIntegrator(
            300 * unit.kelvin, 1.0 / unit.picosecond, 0.002 * unit.picoseconds
        )
        simulation = app.Simulation(pdb.topology, system, integrator)
        simulation.context.setPositions(pdb.positions)
        state = simulation.context.getState(getEnergy=True)
        pe = state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole)

        os.unlink(tmp_pdb)
        record("OpenMM TIP3P water test", True, f"PE = {pe:.4f} kJ/mol")
    except Exception as e:
        record("OpenMM TIP3P water test", False, str(e))


ORCA_TEST_INPUT = """\
! HF STO-3G EnGrad
%pal nprocs 1 end
* xyz 0 1
  H   0.000   0.000   0.000
  H   0.000   0.000   0.741
*
"""


def test_orca_calculation(orca_path):
    if orca_path is None:
        record("ORCA test calculation (H2)", False, "skipped — ORCA not found")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        inp_file = os.path.join(tmpdir, "h2_test.inp")
        with open(inp_file, "w") as f:
            f.write(ORCA_TEST_INPUT)

        try:
            t0 = time.time()
            proc = subprocess.run(
                [orca_path, inp_file], capture_output=True, text=True,
                timeout=120, cwd=tmpdir,
            )
            elapsed = time.time() - t0
            output = proc.stdout + proc.stderr

            energy = None
            for line in output.splitlines():
                if "FINAL SINGLE POINT ENERGY" in line:
                    try:
                        energy = float(line.split()[-1]) * 27.2114  # -> eV
                    except ValueError:
                        pass
                    break

            if energy is not None:
                record("ORCA test calculation (H2)", True, f"E = {energy:.4f} eV ({elapsed:.1f}s)")
            elif "ORCA TERMINATED NORMALLY" in output:
                record("ORCA test calculation (H2)", True, f"terminated normally ({elapsed:.1f}s)")
            else:
                record("ORCA test calculation (H2)", False, "did not terminate normally")
        except subprocess.TimeoutExpired:
            record("ORCA test calculation (H2)", False, "timed out after 120s")
        except Exception as e:
            record("ORCA test calculation (H2)", False, str(e))


# -----------------------------------------------------------------------------
def print_summary():
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'-' * 60}")
    if passed == total:
        print(f"{GREEN}All {total} checks passed — environment is ready.{RESET}")
    else:
        print(f"{RED}{total - passed} of {total} checks failed.{RESET} See details above.")
        print(f"{YELLOW}Common fixes:{RESET}")
        print("  - Activate your conda/venv environment first")
        print("  - pip install numpy matplotlib pyyaml")
        print("  - conda install -c conda-forge openmm")
        print("  - Make sure 'orca' is in your PATH, or set orca.path in config.yaml")
        sys.exit(1)
    print(f"{'-' * 60}\n")


if __name__ == "__main__":
    print(f"\n{CYAN}{'=' * 60}")
    print("  QM/MM Toolkit — Environment Check")
    print(f"  Python {sys.version.split()[0]}")
    print(f"{'=' * 60}{RESET}")

    check_python_packages()
    orca_path = check_orca_binary()
    test_openmm_tip3p()
    test_orca_calculation(orca_path)
    print_summary()
