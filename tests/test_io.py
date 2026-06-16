"""Phase 1 tests: ingestion regression guard + snapshot round-trip."""

from __future__ import annotations

import pandas as pd
import pytest

from tb_cascade.config import RAW_DATA_PATH
from tb_cascade.io import DATE_COLUMNS, EXPECTED_COLUMN_COUNT, load_raw, snapshot

EXPECTED_ROW_COUNT = 7732


def test_load_raw_row_and_column_counts():
    """Regression guard: alerts if the upstream export format changes."""
    df = load_raw(RAW_DATA_PATH)
    assert len(df) == EXPECTED_ROW_COUNT
    assert len(df.columns) == EXPECTED_COLUMN_COUNT


def test_load_raw_dtypes():
    df = load_raw(RAW_DATA_PATH)
    assert str(df["Source"].dtype) == "category"
    assert str(df["IndexCase"].dtype) == "string"
    assert str(df["Source_id"].dtype) == "Int64"
    assert str(df["Contact"].dtype) == "boolean"
    for col in DATE_COLUMNS:
        assert pd.api.types.is_datetime64_any_dtype(df[col]), col


def test_index_case_preserves_leading_zeros():
    df = load_raw(RAW_DATA_PATH)
    non_null = df["IndexCase"].dropna()
    assert non_null.str.len().gt(0).all()
    # At least one value with a leading zero should survive untouched.
    assert non_null.str.startswith("0").any()


def test_snapshot_round_trip(tmp_path, monkeypatch):
    pytest.importorskip("pyarrow")
    import tb_cascade.io as io_module

    monkeypatch.setattr(io_module, "PROCESSED_DATA_DIR", tmp_path)

    df = load_raw(RAW_DATA_PATH)
    out_path = snapshot(df, run_date="2026-06-16")

    assert out_path == tmp_path / "raw_snapshot_2026-06-16.parquet"
    assert out_path.exists()

    round_tripped = pd.read_parquet(out_path)
    assert len(round_tripped) == len(df)
    assert len(round_tripped.columns) == len(df.columns)
