"""
qmmm_common.py — shared helpers used by every script in this toolkit.

Keeping this logic in one place means the rest of the scripts stay short
and focused on the actual science, and you only need to fix a path-finding
bug in one spot if your setup is unusual.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Missing dependency: pyyaml")
    print("Install it with:  pip install pyyaml")
    sys.exit(1)


# -----------------------------------------------------------------------------
# Config loading
# -----------------------------------------------------------------------------

def load_config(config_path: str = "config.yaml") -> dict:
    """
    Load config.yaml and resolve ${variable} references within the
    'paths' section, so you only need to define each path component once.
    """
    if not os.path.isfile(config_path):
        print(f"Config file not found: {config_path}")
        print("Copy config.yaml.example to config.yaml and edit it, or pass")
        print("--config /path/to/your_config.yaml")
        sys.exit(1)

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    cfg["paths"] = _resolve_path_vars(cfg.get("paths", {}))
    return cfg


def _resolve_path_vars(paths: dict) -> dict:
    """Resolve ${key} placeholders against other entries in the same dict."""
    resolved = dict(paths)
    pattern = re.compile(r"\$\{([a-zA-Z0-9_]+)\}")

    # Iterate a few times in case of nested references
    for _ in range(5):
        changed = False
        for key, value in resolved.items():
            if not isinstance(value, str):
                continue
            match = pattern.search(value)
            if not match:
                continue
            ref_key = match.group(1)
            if ref_key in resolved:
                resolved[key] = value.replace(
                    f"${{{ref_key}}}", str(resolved[ref_key])
                )
                changed = True
        if not changed:
            break
    return resolved


# -----------------------------------------------------------------------------
# ORCA discovery
# -----------------------------------------------------------------------------

_COMMON_ORCA_LOCATIONS = [
    "~/orca/orca",
    "~/orca_6.1.0_linux_x86-64_shared_openmpi418_avx2/orca",
    "~/orca_6.0.0_linux_x86-64_shared_openmpi516/orca",
    "~/orca_5.0.4_linux_x86-64_shared_openmpi411/orca",
    "/opt/orca/orca",
    "/usr/local/orca/orca",
]


def find_orca(configured_path: str = "orca") -> str | None:
    """
    Locate the ORCA executable. Tries, in order:
      1. the exact path given in config.yaml (if it's a real, executable file)
      2. the system PATH
      3. a handful of common install locations
    Returns the resolved path, or None if ORCA could not be found.
    """
    expanded = os.path.expanduser(configured_path)
    if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
        return expanded

    found = shutil.which(configured_path)
    if found:
        return found

    for candidate in _COMMON_ORCA_LOCATIONS:
        expanded = os.path.expanduser(candidate)
        if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
            return expanded

    return None


# -----------------------------------------------------------------------------
# Small formatting helpers used across scripts
# -----------------------------------------------------------------------------

def section_header(text: str, width: int = 70, char: str = "=") -> str:
    return f"\n{char * width}\n  {text}\n{char * width}"


def check_files_exist(file_map: dict[str, str]) -> list[str]:
    """
    Given {label: path}, print a ✓/✗ status line for each, and return the
    list of labels for files that are missing.
    """
    missing = []
    for label, path in file_map.items():
        exists = os.path.isfile(path)
        mark = "✓" if exists else "✗"
        size = f"{os.path.getsize(path) / 1024:.0f} KB" if exists else "MISSING"
        print(f"  {mark}  {label:<28} {size}")
        if not exists:
            missing.append(label)
    return missing
