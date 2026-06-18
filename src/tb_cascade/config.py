"""Project-wide paths and constants.

Kept deliberately minimal for Phase 1 (ingestion). Thresholds and
suppression limits used by later phases (QC, derived variables, cascade
analytics) will be added here as those phases are implemented.
"""

from __future__ import annotations

from pathlib import Path

# src/tb_cascade/config.py -> parents[0]=tb_cascade, [1]=src, [2]=repo root
ROOT_DIR: Path = Path(__file__).resolve().parents[2]

RAW_DATA_DIR: Path = ROOT_DIR / "Data" / "raw"
RAW_DATA_PATH: Path = RAW_DATA_DIR / "VladKovMur_dataset.csv"

PROCESSED_DATA_DIR: Path = ROOT_DIR / "Data" / "processed"

# Phase 7 (cli.py): output root for `python -m tb_cascade.cli run`, one
# timestamped subfolder per run (`REPORTS_DIR / run_date`), per the
# Implementation Plan's §3 repo-structure layout. The ad hoc Phase 2/4
# runners (`scripts/run_qc.py`, `scripts/run_cascade.py`) predate this
# constant and still hardcode `ROOT_DIR / "reports"` directly for their
# own flat, non-timestamped output files -- left as-is since they are
# explicitly not the Phase 7 CLI and out of this change's scope.
REPORTS_DIR: Path = ROOT_DIR / "reports"
