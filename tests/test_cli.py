"""Phase 7 tests: `cli.py`'s `run` command, exercised against the same
synthetic fixture used by every other phase's tests
(`tests/fixtures/synthetic_rows.csv`). Quarto itself is never invoked --
`subprocess.run` is monkeypatched to a stand-in that mimics Quarto's
real on-disk side effect (writing `<template>.html`/`.md` next to the
template) rather than requiring Quarto to be installed in the test
environment, consistent with `cli.py`'s own module docstring.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from tb_cascade import cli as cli_module
from tb_cascade import derive as derive_module
from tb_cascade.io import DATE_COLUMNS, DTYPE_MAP

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "synthetic_rows.csv"


def _load_fixture() -> pd.DataFrame:
    """Same load logic `test_qc.py`/`test_derive.py` use for the fixture."""
    frame = pd.read_csv(FIXTURE_PATH, dtype=DTYPE_MAP, parse_dates=DATE_COLUMNS)
    for col in DATE_COLUMNS:
        if not pd.api.types.is_datetime64_any_dtype(frame[col]):
            frame[col] = pd.to_datetime(frame[col], errors="coerce")
    return frame


@pytest.fixture
def isolated_cli(tmp_path, monkeypatch):
    """Redirect every path `cli.run` writes to (`REPORTS_DIR`, and
    `derive.py`'s `PROCESSED_DATA_DIR` for the persisted Parquet) under
    `tmp_path`, and swap in the synthetic fixture for `load_raw()` --
    mirrors `test_io.py`'s `monkeypatch.setattr(io_module,
    "PROCESSED_DATA_DIR", tmp_path)` pattern.
    """
    reports_dir = tmp_path / "reports"
    processed_dir = tmp_path / "processed"
    monkeypatch.setattr(cli_module, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(derive_module, "PROCESSED_DATA_DIR", processed_dir)
    monkeypatch.setattr(cli_module, "load_raw", _load_fixture)
    return {"reports_dir": reports_dir, "processed_dir": processed_dir}


def test_run_skip_report_writes_qc_and_parquet(isolated_cli):
    """`--skip-report` should still run ingestion/QC/derive and write the
    QC report, the flagged-records local-review CSV (the fixture has
    several deliberate violations -- see `test_qc.py`'s docstring), and
    the persisted analysis-ready Parquet -- just no Quarto render."""
    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        ["run", "--as-of", "2026-06-16", "--skip-report"],
    )
    assert result.exit_code == 0, result.output

    out_dir = isolated_cli["reports_dir"] / "2026-06-16"
    assert (out_dir / "qc_report.md").exists()
    assert (out_dir / "flagged_records.csv").exists()

    parquet_path = isolated_cli["processed_dir"] / "analysis_ready_2026-06-16.parquet"
    assert parquet_path.exists()

    persisted = pd.read_parquet(parquet_path)
    raw = _load_fixture()
    assert len(persisted) == len(raw)
    assert len(persisted.columns) > len(raw.columns)  # derived columns appended


def test_run_default_run_date_falls_back_to_as_of(isolated_cli):
    """No `--run-date` given -> the output folder and Parquet are both
    tagged with `--as-of`, mirroring `scripts/run_derive.py`'s
    `run_date = args.run_date or args.as_of`."""
    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        ["run", "--as-of", "2026-01-01", "--skip-report"],
    )
    assert result.exit_code == 0, result.output
    assert (isolated_cli["reports_dir"] / "2026-01-01" / "qc_report.md").exists()
    assert (isolated_cli["processed_dir"] / "analysis_ready_2026-01-01.parquet").exists()


def test_run_explicit_run_date_overrides_as_of(isolated_cli):
    """`--run-date` tags the output folder/Parquet independently of
    `--as-of` (e.g. re-tagging a re-run against the same analysis date)."""
    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        ["run", "--as-of", "2026-01-01", "--run-date", "2026-01-02", "--skip-report"],
    )
    assert result.exit_code == 0, result.output
    assert (isolated_cli["reports_dir"] / "2026-01-02" / "qc_report.md").exists()
    assert (isolated_cli["processed_dir"] / "analysis_ready_2026-01-02.parquet").exists()
    assert not (isolated_cli["reports_dir"] / "2026-01-01").exists()


def test_run_skips_missing_template_without_calling_quarto(isolated_cli, monkeypatch, tmp_path):
    """An explicitly requested `--lang` whose `.qmd` template is missing on
    disk should be skipped with a message, never reaching `subprocess.run`
    -- exercises the `template.exists()` guard inside the render loop
    itself (as opposed to the default-language filter, which would just
    silently omit it from `selected_langs`)."""
    monkeypatch.setattr(
        cli_module, "REPORT_TEMPLATES", {"en": tmp_path / "does_not_exist.qmd"}
    )
    calls = []
    monkeypatch.setattr(cli_module.subprocess, "run", lambda *a, **k: calls.append((a, k)))

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli, ["run", "--as-of", "2026-06-16", "--lang", "en"]
    )
    assert result.exit_code == 0, result.output
    assert calls == []
    assert "Skipping 'en': template not found" in result.output


def test_render_report_invokes_quarto_and_moves_output(tmp_path, monkeypatch):
    """`_render_report` should call `quarto render` with the documented
    `-P key:value` parameters and `--execute-daemon-restart`, then move the
    resulting `.html`/`.md` files (Quarto's real on-disk side effect, here
    faked by the monkeypatched `subprocess.run`) into the run's output dir
    -- not just copy them, since the source-adjacent copy must not linger
    in `report/` after a run."""
    template = tmp_path / "descriptive_report.qmd"
    template.write_text("# placeholder\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    captured = {}

    def fake_run(cmd, cwd=None, check=None):
        captured["cmd"] = cmd
        template.with_suffix(".html").write_text("<html></html>", encoding="utf-8")
        template.with_suffix(".md").write_text("# rendered\n", encoding="utf-8")

    monkeypatch.setattr(cli_module.subprocess, "run", fake_run)

    cli_module._render_report(template, "2026-06-16", "Data/processed/x.parquet", 12, out_dir)

    cmd = captured["cmd"]
    assert cmd[:3] == ["quarto", "render", str(template)]
    assert "-P" in cmd
    assert "as_of:2026-06-16" in cmd
    assert "analysis_ready_path:Data/processed/x.parquet" in cmd
    assert "window_months:12" in cmd
    assert "--execute-daemon-restart" in cmd

    assert (out_dir / "descriptive_report.html").exists()
    assert (out_dir / "descriptive_report.md").exists()
    assert not template.with_suffix(".html").exists()  # moved, not copied
    assert not template.with_suffix(".md").exists()


def test_render_report_missing_quarto_exits_nonzero(tmp_path, monkeypatch):
    """If `quarto` isn't on PATH, `_render_report` should exit(1) with a
    clear message rather than letting a bare `FileNotFoundError` propagate
    out of the CLI."""
    template = tmp_path / "descriptive_report.qmd"
    template.write_text("# placeholder\n", encoding="utf-8")

    def fake_run(cmd, cwd=None, check=None):
        raise FileNotFoundError("quarto not found")

    monkeypatch.setattr(cli_module.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc_info:
        cli_module._render_report(template, "2026-06-16", "", 12, tmp_path)
    assert exc_info.value.code == 1
