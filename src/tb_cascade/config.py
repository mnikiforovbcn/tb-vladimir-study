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
