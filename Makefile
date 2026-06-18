# Phase 7 (Implementation Plan Sec 7) -- thin wrappers around the `uv`-managed
# environment and the `tb_cascade.cli` entry point (src/tb_cascade/cli.py).
# Nothing here duplicates pipeline logic; every target just shells out to
# `uv run ...` so this Makefile and a developer typing the same commands by
# hand always do exactly the same thing.
#
# Targets:
#   make setup   - resolve/lock deps, create .venv, install dev tools + pre-commit hook
#   make test    - run the test suite (tests/)
#   make report  - run the full pipeline (Phases 1-6) via the CLI, writing
#                  reports/<run_date>/; pass CLI flags via ARGS, e.g.
#                  `make report ARGS="--as-of 2026-06-16 --skip-report"`
#   make clean   - remove generated reports/ output and processed Parquet
#                  (anything the pipeline regenerates -- never source data)

.PHONY: setup test report clean

setup:
	uv lock
	uv sync --extra dev
	uv run pre-commit install

test:
	uv run pytest

report:
	uv run python -m tb_cascade.cli run $(ARGS)

clean:
	rm -rf reports/*
	touch reports/.gitkeep
	rm -rf Data/processed/*
