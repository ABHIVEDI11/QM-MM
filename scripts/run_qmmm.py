#!/usr/bin/env python3
"""
run_qmmm.py — QM/MM single-point calculation for any protein-ligand system

What this script does, in order:
  1. Loads your CHARMM-GUI files (topology + equilibrated coordinates)
  2. Selects the QM region (your ligand, optionally plus nearby residues)
  3. Extracts every other atom's charge as a classical MM point charge
  4. Writes an ORCA input file with those point charges embedded
  5. Runs ORCA (solves the Schrodinger equation for the QM region, polarized
     by the surrounding protein/water)
  6. Parses and prints the energy and Mulliken atomic charges

Usage:
    python scripts/run_qmmm.py
    python scripts/run_qmmm.py --config path/to/your_config.yaml

All system-specific settings (paths, ligand name, charge, QM method) live
in config.yaml — this script itself never needs to be edited.
"""

import argparse
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qmmm_common import check_files_exist, find_orca, load_config, section_header  # noqa: E402

NM_TO_ANG = 10.0
HARTREE_TO_EV = 27.211396
HARTREE_TO_KCALMOL = 627.509


def parse_args():
    p = argparse.ArgumentParser(description="Run a QM/MM single-point calculation.")
    p.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    return p.parse_args()


def main():
    args = parse_args()
    cfg = load_config(args.config)

    try:
        import openmm as mm
        from openmm import app, unit
        from openmm.app import CharmmParameterSet, CharmmPsfFile, PDBFile
    except ImportError:
        print("OpenMM not found. Install it with: conda install -c conda-forge openmm")
        sys.exit(1)

    paths = cfg["paths"]
    ligand = cfg["ligand"]
    qm_region_cfg = cfg["qm_region"]
    qm_method_cfg = cfg["qm_method"]
    output_dir = cfg["output"]["dir"]

    resname = ligand["resname"]
    qm_charge = int(ligand["charge"])
    qm_multiplicity = int(ligand.get("multiplicity", 1))
    qm_method = qm_method_cfg["method"]
    n_cores = int(qm_method_cfg.get("cores", 4))
    ram_mb = int(qm_method_cfg.get("ram_mb_per_core", 4000))

    orca_exec = find_orca(cfg.get("orca", {}).get("path", "orca"))
    if not orca_exec:
        print("ORCA not found. Set orca.path in config.yaml, or add ORCA to your PATH.")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(section_header("QM/MM CALCULATION"))
    print(f"  PSF file    : {paths['psf_file']}")
    print(f"  PDB file    : {paths['pdb_file']}")
    print(f"  Ligand      : {resname}  (charge = {qm_charge:+d}, mult = {qm_multiplicity})")
    print(f"  QM method   : {qm_method}")
    print(f"  ORCA        : {orca_exec}")
    print(f"  Cores / RAM : {n_cores} cores x {ram_mb} MB = {n_cores * ram_mb} MB total")
    print(f"  Expand QM   : {qm_region_cfg.get('expand_to_nearby_residues', False)}")

    # -------------------------------------------------------------------
    # Check required input files
    # -------------------------------------------------------------------
    print("\nChecking input files...")
    missing = check_files_exist({
        "PSF (topology)": paths["psf_file"],
        "PDB (equilibrated)": paths["pdb_file"],
        "Ligand topology (.rtf)": paths["ligand_rtf"],
        "Ligand parameters (.prm)": paths["ligand_prm"],
    })
    if missing:
        print("\nMissing required files (see above). Check the [paths] section")
        print("of your config.yaml.")
        sys.exit(1)

    # -------------------------------------------------------------------
    # STEP 1 — Load CHARMM-GUI files into OpenMM
    # -------------------------------------------------------------------
    print("\nStep 1: Loading system...")

    psf = CharmmPsfFile(paths["psf_file"])
    pdb = PDBFile(paths["pdb_file"])
    positions = pdb.positions.value_in_unit(unit.nanometer)
    all_atoms = list(psf.topology.atoms())

    toppar_priority = [
        "top_all36_prot.rtf",
        "par_all36m_prot.prm",
        "top_all36_cgenff.rtf",
        "par_all36_cgenff.prm",
        "toppar_water_ions.str",
    ]

    param_files, added = [], set()

    # Ligand files first, so CHARMM36 doesn't redefine ligand atom types
    for f in (paths["ligand_rtf"], paths["ligand_prm"]):
        if os.path.isfile(f) and f not in added:
            param_files.append(f)
            added.add(f)

    toppar_dir = paths.get("toppar_dir", "")
    for fname in toppar_priority:
        full = os.path.join(toppar_dir, fname)
        if os.path.isfile(full) and full not in added:
            param_files.append(full)
            added.add(full)

    if os.path.isdir(toppar_dir):
        for fname in sorted(os.listdir(toppar_dir)):
            full = os.path.join(toppar_dir, fname)
            if fname.endswith((".rtf", ".prm", ".str")) and os.path.isfile(full) and full not in added:
                param_files.append(full)
                added.add(full)

    toppar_str = paths.get("toppar_str", "")
    if os.path.isfile(toppar_str) and toppar_str not in added:
        param_files.append(toppar_str)
        added.add(toppar_str)

    print(f"  Loading {len(param_files)} parameter files...")
    try:
        params = CharmmParameterSet(*param_files)
    except Exception as e:
        print(f"  ERROR loading parameters: {e}")
        print("  Check that your ligand .rtf / .prm files are valid CHARMM format.")
        sys.exit(1)

    try:
        system = psf.createSystem(
            params, nonbondedMethod=app.PME, nonbondedCutoff=1.0 * unit.nanometer,
            constraints=app.HBonds,
        )
        print("  System created with PME (periodic box)")
    except Exception as e1:
        if "periodic" in str(e1).lower():
            try:
                system = psf.createSystem(params, nonbondedMethod=app.NoCutoff, constraints=app.HBonds)
                print("  No periodic box found - using NoCutoff instead")
            except Exception as e2:
                print(f"  ERROR creating system: {e2}")
                sys.exit(1)
        else:
            print(f"  ERROR creating OpenMM system: {e1}")
            sys.exit(1)

    n_total = system.getNumParticles()
    print(f"  Total atoms : {n_total:,}")
    print(f"  Residues    : {psf.topology.getNumResidues():,}")

    drug_atoms_check = [a for a in all_atoms if a.residue.name == resname]
    if not drug_atoms_check:
        protein_res = {
            "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
            "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL",
            "HSD", "HSE", "HSP", "HID", "HIE", "HIP",
        }
        water_ions = {"HOH", "TIP3", "SOD", "CLA", "POT", "CAL", "MG", "ZN"}
        other = sorted({
            a.residue.name for a in all_atoms
            if a.residue.name not in protein_res and a.residue.name not in water_ions
        })
        print(f"\n  No atoms found with residue name '{resname}'.")
        if other:
            print(f"  Found these non-protein, non-water residue names instead: {other}")
            print("  -> update ligand.resname in config.yaml to one of these")
        else:
            print(f"  Check: grep HETATM {paths['pdb_file']} | head -3")
        sys.exit(1)

    print(f"  Ligand ({resname}) : {len(drug_atoms_check)} atoms found")

    # -------------------------------------------------------------------
    # STEP 2 — Select QM region
    # -------------------------------------------------------------------
    print(f"\nStep 2: Selecting QM region (ligand = {resname})...")

    qm_atoms = [a.index for a in all_atoms if a.residue.name == resname]
    qm_set = set(qm_atoms)

    if qm_region_cfg.get("expand_to_nearby_residues", False):
        cutoff = float(qm_region_cfg.get("expand_cutoff_angstrom", 5.0))
        print(f"  Expanding to residues within {cutoff} A of {resname}...")
        ligand_pos = np.array([
            [float(positions[a.index][k]) * NM_TO_ANG for k in range(3)]
            for a in all_atoms if a.residue.name == resname
        ])
        skip = {"HOH", "TIP3", "SOD", "CLA", "POT", "CAL", "MG", "ZN"}
        added_residues = set()
        for atom in all_atoms:
            if atom.residue.name in skip or atom.residue.name == resname:
                continue
            if atom.index in qm_set:
                continue
            pos = np.array([float(positions[atom.index][k]) * NM_TO_ANG for k in range(3)])
            if np.min(np.linalg.norm(ligand_pos - pos, axis=1)) < cutoff:
                qm_atoms.append(atom.index)
                qm_set.add(atom.index)
                added_residues.add(f"{atom.residue.name}{atom.residue.id}")
        print(f"  Added residues: {', '.join(sorted(added_residues)) if added_residues else 'none'}")

    print(f"  QM region: {len(qm_atoms)} atoms (charge {qm_charge:+d}, multiplicity {qm_multiplicity})")

    # -------------------------------------------------------------------
    # STEP 3 — Extract MM point charges
    # -------------------------------------------------------------------
    print("\nStep 3: Extracting MM point charges...")

    mm_charges = []
    for force in system.getForces():
        if isinstance(force, mm.NonbondedForce):
            for i in range(system.getNumParticles()):
                q, _, _ = force.getParticleParameters(i)
                mm_charges.append(q.value_in_unit(unit.elementary_charge))
            break

    pc_lines = []
    for i, q in enumerate(mm_charges):
        if i not in qm_set and abs(q) > 1e-6:
            pos = positions[i]
            x, y, z = (float(pos[k]) * NM_TO_ANG for k in range(3))
            pc_lines.append(f"{q:+.6f}  {x:.6f}  {y:.6f}  {z:.6f}")

    pc_path = os.path.abspath(os.path.join(output_dir, "mm_charges.pc"))
    with open(pc_path, "w") as f:
        f.write(str(len(pc_lines)) + "\n")
        f.write("\n".join(pc_lines))

    print(f"  MM point charges: {len(pc_lines):,}")
    print(f"  ({n_total:,} total - {len(qm_atoms)} QM = {len(pc_lines):,} MM)")
    print(f"  Written -> {pc_path}")

    # -------------------------------------------------------------------
    # STEP 4 — Write ORCA input
    # -------------------------------------------------------------------
    print("\nStep 4: Writing ORCA input file...")

    inp_path = os.path.abspath(os.path.join(output_dir, "qmmm_system.inp"))
    out_path = os.path.abspath(os.path.join(output_dir, "qmmm_system.out"))

    with open(inp_path, "w") as f:
        f.write(f"! {qm_method} TightSCF\n\n")
        f.write(f"%maxcore {ram_mb}\n")
        f.write(f"%pal nprocs {n_cores} end\n\n")
        f.write(f'%pointcharges "{pc_path}"\n\n')
        f.write("%output\n  Print[P_Mulliken] 1\nend\n\n")
        f.write(f"* xyz {qm_charge} {qm_multiplicity}\n")
        for idx in qm_atoms:
            atom = all_atoms[idx]
            elem = atom.element.symbol if atom.element else "X"
            pos = positions[idx]
            x, y, z = (float(pos[k]) * NM_TO_ANG for k in range(3))
            f.write(f"  {elem:3s}   {x:12.6f}   {y:12.6f}   {z:12.6f}\n")
        f.write("*\n")

    print(f"  ORCA input -> {inp_path}")
    print(f"  QM atoms   : {len(qm_atoms)}")
    print(f"  MM charges : {len(pc_lines):,}")
    print(f"  Method     : {qm_method}")

    # -------------------------------------------------------------------
    # STEP 5 — Run ORCA
    # -------------------------------------------------------------------
    n_qm = len(qm_atoms)
    print("\nStep 5: Running ORCA...")
    if n_qm <= 15:
        print("  Estimated time: 2-5 minutes (small QM region)")
    elif n_qm <= 60:
        print("  Estimated time: 5-20 minutes (medium QM region)")
    else:
        print("  Estimated time: 20-60 minutes (large QM region)")
    print("  (the terminal will be quiet while ORCA runs - this is normal)\n")

    try:
        with open(out_path, "w") as out_f:
            subprocess.run([orca_exec, inp_path], stdout=out_f, stderr=subprocess.STDOUT, timeout=7200)
    except FileNotFoundError:
        print(f"  Cannot execute ORCA at '{orca_exec}'. Check orca.path in config.yaml.")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("  ORCA timed out after 2 hours.")
        sys.exit(1)

    # -------------------------------------------------------------------
    # STEP 6 — Parse and print results
    # -------------------------------------------------------------------
    with open(out_path) as f:
        text = f.read()
    lines = text.split("\n")

    print(section_header("RESULTS"))

    if "ORCA TERMINATED NORMALLY" not in text:
        print("  ORCA did NOT terminate normally. Last 25 lines of output:")
        for line in lines[-25:]:
            if line.strip():
                print(f"    {line}")
        print(f"\n  Full output: {out_path}")
        print("\n  Common fixes:")
        print("    1. Wrong ligand charge -> check protonation state at your pH")
        print("    2. Try qm_method.method = 'HF STO-3G' as a quick test")
        print(f"    3. Verify ORCA path: {orca_exec}")
        sys.exit(1)

    print("  ORCA terminated normally\n")

    energy_ha = None
    for line in reversed(lines):
        if "FINAL SINGLE POINT ENERGY" in line:
            try:
                energy_ha = float(line.split()[-1])
            except (ValueError, IndexError):
                pass
            break

    if energy_ha is not None:
        print("  QM/MM Energy:")
        print(f"    {energy_ha:22.8f}  Hartree")
        print(f"    {energy_ha * HARTREE_TO_EV:22.4f}  eV")
        print(f"    {energy_ha * HARTREE_TO_KCALMOL:22.2f}  kcal/mol")
        print()
        print("  Note: the absolute value alone is not meaningful. To get the")
        print("  protein's binding/polarization contribution, run a second")
        print("  calculation with %pointcharges commented out (gas phase) and")
        print("  compute dE = E_protein - E_gas.")

    print(f"\n  Mulliken charges on QM atoms ({resname}):")
    print(f"  {'#':>4}  {'Elem':>5}  {'Charge (e)':>12}")
    print(f"  {'-' * 30}")

    mulliken, reading = {}, False
    for line in lines:
        if "MULLIKEN ATOMIC CHARGES" in line:
            reading = True
            continue
        if reading:
            if "Sum of atomic charges" in line:
                break
            parts = line.split()
            if len(parts) >= 4:
                try:
                    mulliken[int(parts[0])] = float(parts[-1])
                except (ValueError, IndexError):
                    pass

    if mulliken:
        for local_i, global_i in enumerate(qm_atoms):
            atom = all_atoms[global_i]
            elem = atom.element.symbol if atom.element else "?"
            charge = mulliken.get(local_i, 0.0)
            print(f"  {local_i:>4}  {elem:>5}  {charge:>+12.4f} e")

        most_neg_i = min(mulliken, key=mulliken.get)
        most_neg_q = mulliken[most_neg_i]
        most_neg_a = all_atoms[qm_atoms[most_neg_i]]
        most_neg_e = most_neg_a.element.symbol if most_neg_a.element else "?"
        print(f"\n  Most negative atom: {most_neg_e} (#{most_neg_i}) = {most_neg_q:+.4f} e")
        print("  This is usually the strongest H-bond acceptor / most polarized site.")

    print(section_header("CALCULATION COMPLETE"))
    print(f"  {os.path.join(output_dir, 'qmmm_system.out')}  <- ORCA output (full results)")
    print(f"  {os.path.join(output_dir, 'qmmm_system.inp')}  <- ORCA input")
    print(f"  {os.path.join(output_dir, 'mm_charges.pc')}    <- MM point charges")
    print(f"\n  Visualize these results with:")
    print(f"    python scripts/visualize_results.py --output-dir {output_dir}")


if __name__ == "__main__":
    main()
