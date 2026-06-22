# QM/MM Toolkit

A small, config-driven toolkit for running QM/MM (Quantum Mechanics /
Molecular Mechanics) calculations on protein-ligand systems, and turning the
results into clear, professional figures.

QM/MM combines a fast classical force field for most of a system (a solvated
protein) with an accurate quantum mechanical treatment of the one part you
actually care about (a small molecule bound in the protein's active site). A
field of classical point charges — every protein and water atom outside the
quantum region — sits directly inside the quantum Hamiltonian, so the
molecule's electron density physically responds to its surroundings. That
responsiveness is something a purely classical force field, with its fixed
atomic charges, cannot capture at all.

<p align="center">
  <img src="docs/images/qmmm_concept.png" width="600">
</p>

This repository wraps that workflow — [OpenMM](https://openmm.org/) for the
molecular mechanics side and [ORCA](https://www.faccts.de/orca/) for the
quantum side — into a small set of scripts driven by one config file, so the
same code runs on any protein and any ligand.

## What it looks like inside the pocket

<p align="center">
  <img src="docs/images/binding_pocket.png" width="640">
</p>

This is the physical picture behind every number the toolkit produces: a
ligand's most electronegative atom forming a hydrogen bond with a pocket
residue, with its electron density measurably shifted by that environment —
something only the quantum side of the calculation can show you.

## Case study: the project behind this toolkit

I didn't build this toolkit in the abstract. It's the general, reusable
version of one real calculation I ran, cleaned up so the same code works on
any protein and ligand, not just mine.

**System:** T4 Lysozyme L99A/M102Q (PDB
[3HTB](https://www.rcsb.org/structure/3HTB)), bound to **JZ4**
(2-propylphenol). T4 lysozyme L99A has an engineered hydrophobic pocket and
is a standard model system for studying ligand binding. The M102Q mutation
adds one glutamine, Gln102, giving that pocket a single polar spot where a
ligand can form a hydrogen bond.

**Pipeline:** I prepared the system in [CHARMM-GUI](https://charmm-gui.org/),
equilibrated it in [OpenMM](https://openmm.org/), then ran a QM/MM single
point calculation in [ORCA](https://www.faccts.de/orca/) using
B3LYP/def2-SVP with D3BJ dispersion correction. The QM region was the full
JZ4 ligand, 22 atoms. Everything else, about 46,400 atoms of solvated
protein, became 46,365 fixed point charges embedded directly in the QM
Hamiltonian.

**Result:** the final QM/MM energy was **−424.8538 Hartree** (about
−11,560.8 eV). The interesting number is the charge on the ligand's
hydroxyl oxygen, the atom that hydrogen bonds to Gln102. In the protein
environment, ORCA gives it a Mulliken charge of **−0.20 e**. The classical
force field (CGenFF/SwissParam) assumes a fixed charge of about **−0.54 e**
for that same atom, a difference of roughly **0.34 e**. This is the whole
reason to run QM/MM instead of a classical calculation: a force field locks
that charge in place forever, but the real electron density shifts by over
a third of an electron once the molecule sits inside the protein, and only
the quantum side of the calculation can see that. It's the same effect
shown in the diagram above, and it's literally what `sample_summary.png` is
plotting below. That figure is the real output of this calculation, not a
made up example.

**What I learned:**
*(draft, reword this in your own voice before publishing)*
- Getting one molecule through three different tools, CHARMM-GUI's topology
  format, OpenMM's equilibration, and ORCA's input format, was harder than
  the actual QM/MM physics. Most of my debugging time went into file format
  and atom indexing problems, not chemistry.
- A QM/MM energy on its own doesn't mean much. It only becomes useful once
  you compare it to something else, like a gas phase or unembedded run.
  That's why `visualize_results.py` is built around comparisons instead of
  single numbers.
- Mulliken charges depend on the basis set you use and aren't a perfect
  measurement, but they're still the cheapest way to see polarization
  happening directly. The 0.34 e shift I found was a clear sign the point
  charge embedding was doing something physically real, not just running
  without errors.
- In plain terms, this is what a fixed charge force field can never
  capture. Having Gln102 sitting right next to JZ4's hydroxyl group changes
  that atom's electron density in a way no MM charge set is allowed to
  respond to, no matter how well it's parameterized.

## Real output, visualized

Both figures below are generated directly by `visualize_results.py` from
real ORCA output included in `examples/sample_output/` — nothing here is
mocked up. The summary figure is the actual JZ4/3HTB run described above;
the comparison figure is a second, separate real calculation used to
demonstrate the environment-vs-gas-phase comparison feature.

**Energy + Mulliken charge summary** for a single QM/MM run — energy in all
three units quantum chemists use, plus a sorted bar chart of every atom's
charge, with the strongest H-bond acceptor called out automatically:

<p align="center">
  <img src="examples/sample_output/sample_summary.png" width="720">
</p>

**Environment vs. gas phase** — the actual point of running QM/MM instead of
a faster classical or gas-phase calculation. The same molecule, once
polarized by its surroundings and once in vacuum, shows a measurable shift in
both energy and per-atom charge:

<p align="center">
  <img src="examples/sample_output/sample_comparison.png" width="720">
</p>

## What's in here

```
qmmm-toolkit/
├── config.yaml.example       # copy to config.yaml and edit for your system
├── scripts/
│   ├── check_setup.py        # verifies OpenMM + ORCA are installed correctly
│   ├── run_qmmm.py            # runs the QM/MM single-point calculation
│   ├── visualize_results.py  # turns ORCA output into the charts above
│   ├── diagram.py             # generates the schematic illustrations above
│   ├── orca_parser.py        # standalone ORCA-output parser (energy + charges)
│   └── qmmm_common.py        # shared config-loading / ORCA-discovery helpers
├── examples/
│   └── sample_output/        # real ORCA output + figures, so you can try
│                              # the visualizer immediately without running ORCA
└── docs/
    ├── images/                # the two illustrations shown above
    ├── workflow.md            # full pipeline: PDB file -> QM/MM result
    └── file_reference.md      # what every generated file is and means
```

## Quick start

Try the visualizer right away on the included sample data — no setup
required:

```bash
pip install -r requirements.txt

python scripts/visualize_results.py \
  --orca-out examples/sample_output/qmmm_system.out \
  --title "Sample QM/MM Result"

python scripts/visualize_results.py \
  --orca-out examples/sample_output/environment_example.out \
  --compare-to examples/sample_output/gas_phase_example.out \
  --labels "In environment" "Gas phase"
```

You can also regenerate the two schematic illustrations, optionally with
your own residue/ligand labels and numbers:

```bash
python scripts/diagram.py --out-dir docs/images \
  --residue "Gln102" --ligand-label "Ligand" --distance 2.8 --delta-q -0.028
```

## Running it on your own system

This requires [OpenMM](https://openmm.org/) and
[ORCA](https://www.faccts.de/orca/) (free for academic use) installed
locally, plus a system prepared in [CHARMM-GUI](https://charmm-gui.org/).
The full pipeline — from downloading a PDB file to a finished QM/MM
result — is in **[docs/workflow.md](docs/workflow.md)**.

Once you have a CHARMM-GUI-prepared, equilibrated system:

```bash
# 1. Copy and edit the config for your protein/ligand
cp config.yaml.example config.yaml
# edit config.yaml: set paths.charmm_gui_dir and ligand.resname / ligand.charge

# 2. Confirm your environment is set up correctly
python scripts/check_setup.py

# 3. Run the QM/MM calculation
python scripts/run_qmmm.py

# 4. Visualize the result
python scripts/visualize_results.py --output-dir qmmm_output
```

Nothing in `scripts/` needs to change between projects — every
system-specific detail (file paths, ligand name, net charge, QM method,
core count) lives in `config.yaml`.

## How it works

1. **Load the system.** `run_qmmm.py` reads the CHARMM-GUI topology (`.psf`)
   and equilibrated coordinates (`.pdb`) into OpenMM.
2. **Select the QM region.** By default, every atom belonging to your
   ligand's residue name. Optionally, nearby protein residues too (see
   `qm_region.expand_to_nearby_residues` in the config), if you want a key
   H-bonding side chain treated quantum-mechanically instead of classically.
3. **Extract MM point charges.** Every other atom in the system — the rest of
   the protein, all the water, any ions — becomes a fixed classical point
   charge.
4. **Write and run an ORCA input.** The point charges are embedded directly in
   ORCA's Hamiltonian via `%pointcharges`. This is the actual QM/MM coupling:
   the quantum region's wavefunction is solved *in the presence of* the
   surrounding electric field, so it can polarize in response to it.
5. **Parse and visualize.** The script extracts the total energy (Hartree,
   eV, kcal/mol) and the Mulliken atomic charges, and `visualize_results.py`
   turns those into the figures shown above.

## Requirements

- Python 3.10+
- [OpenMM](https://openmm.org/) (best installed via conda:
  `conda install -c conda-forge openmm`)
- [ORCA](https://www.faccts.de/orca/) 5 or 6, with the `orca` binary on
  your `PATH`
- Everything else: `pip install -r requirements.txt`

## License

MIT — see [LICENSE](LICENSE).
