# Workflow: From a PDB File to a QM/MM Result

This is the full pipeline, in order. It works for **any** protein-ligand
system — only the protein/ligand names change between projects, not the
steps themselves.

```
1. Download structure  ──▶  2. Prepare ligand  ──▶  3. Build solvated system
        (RCSB PDB)              (OpenBabel + CGenFF)      (CHARMM-GUI)
                                                                  │
                                                                  ▼
6. Visualize results  ◀──  5. Run QM/MM  ◀──────────  4. Equilibrate
   (visualize_results.py)    (run_qmmm.py)              (openmm_run.py)
```

## Step 1 — Get a structure

Go to [rcsb.org](https://www.rcsb.org), search for your protein, and download
the PDB file. Most structures of pharmacological interest already have a
bound ligand — note its three-letter residue code (e.g. `JZ4`, `ATP`, `HEM`);
you'll need it later.

## Step 2 — Prepare the ligand for the force field

Extract just the ligand's atoms from the PDB file and convert it to MOL2
format with [OpenBabel](https://openbabel.org/):

```bash
grep "HETATM.*YOUR_LIGAND_CODE" structure.pdb > ligand.pdb
obabel ligand.pdb -O ligand.mol2 --gen3d
```

Then get CHARMM-compatible parameters for the ligand from
[CGenFF](https://cgenff.silcsbio.com/) (or SwissParam): upload the MOL2 file,
set the correct net charge, and download the resulting `.str` file. This
encodes the ligand's bond, angle, and partial-charge parameters so the force
field knows how to treat it.

## Step 3 — Build the solvated system in CHARMM-GUI

Go to [charmm-gui.org](https://charmm-gui.org) → **Input Generator** → **PDB
Reader**, and work through five pages:

| Page | What to set | Why |
|---|---|---|
| 1 — Upload | Your PDB file | Starting structure |
| 2 — Select components | Keep protein chain(s) + ligand; remove crystal water | Crystal water reflects the crystal, not solution; CHARMM-GUI builds a proper water box instead |
| 3 — Manipulate PDB | Add hydrogens, add missing residues, set pH, **upload your ligand's `.str` file** | X-ray structures lack H atoms; pH sets correct protonation states |
| 4 — Solvator | Water model = TIP3P, box padding ≥ 10 Å, ions as needed, force field = CHARMM36m, **output format = OpenMM** | TIP3P matches CHARMM36's parameterization; OpenMM output is what `run_qmmm.py` expects |
| 5 — Download | Download the `.tgz` and extract it | Gives you the `openmm/` folder this toolkit reads from |

## Step 4 — Equilibrate

Crystal water sits on an artificial, grid-like lattice. Before any QM/MM
calculation is meaningful, water needs to relax into a realistic hydrogen-bond
network around the protein:

```bash
cd charmm-gui-output/openmm
conda activate openmm_env
python openmm_run.py \
  -i step4_equilibration.inp -p step3_input.psf -c step3_input.crd \
  -t toppar.str -b sysinfo.dat --platform OpenCL \
  -opdb step4_equilibration.pdb -orst step4_equilibration.rst -odcd step4_equilibration.dcd
```

(If `OpenCL` isn't available on your machine, use `--platform CPU` instead —
slower, but always works.)

This produces `step4_equilibration.pdb` — the file you actually want to run
QM/MM on. Never run QM/MM directly on `step3_input.pdb`; that one still has
water in unequilibrated, unphysical positions.

## Step 5 — Run the QM/MM calculation

Edit `config.yaml` (copy `config.yaml.example` first) to point at your files
and ligand:

```yaml
paths:
  charmm_gui_dir: "./charmm-gui-output"
ligand:
  resname: "YOUR_LIGAND_CODE"
  charge: 0
```

Then run:

```bash
python scripts/check_setup.py     # confirm OpenMM + ORCA are working
python scripts/run_qmmm.py        # run the QM/MM single point
```

This automatically:
1. loads the topology and equilibrated coordinates,
2. selects your ligand as the quantum region,
3. extracts every other atom as a classical point charge,
4. writes and runs an ORCA input with those charges embedded in the
   Hamiltonian,
5. parses and prints the energy and Mulliken atomic charges.

## Step 6 — Visualize

```bash
python scripts/visualize_results.py --output-dir qmmm_output
```

This produces a single summary figure: the QM/MM energy in three common
units, and a sorted bar chart of Mulliken charges across the quantum region,
with the most negative/positive atoms called out.

To see how the *environment* changed your ligand's electronic structure
(the actual point of doing QM/MM instead of a faster classical calculation),
run a second calculation with the `%pointcharges` line in `qmmm_system.inp`
commented out (gas phase), then compare:

```bash
python scripts/visualize_results.py \
  --orca-out qmmm_output/qmmm_system.out \
  --compare-to qmmm_output_gas_phase/qmmm_system.out \
  --labels "In protein" "Gas phase"
```

## What never changes between systems

| Always the same | Changes per system |
|---|---|
| CHARMM-GUI's 5 pages and settings | PDB code |
| The equilibration command | `ligand.resname` |
| `run_qmmm.py` itself | `ligand.charge` |
| `visualize_results.py` itself | QM method (optional, for accuracy/speed trade-off) |

Once you've done this once, doing it again for a different protein-ligand
pair is mostly just re-running the same six steps with a different PDB code.
