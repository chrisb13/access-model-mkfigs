#!/usr/bin/env python

"""Tests for mkfigs.run._fix_kernel — notebook kernel normalisation.

Regression coverage for the shared-template race: mkfigs-run notebooks live
in a directory shared by every experiment (notebooks_dir), and multiple
mkfigs.sh PBS jobs can be running concurrently against the same clone. The
old _fix_kernel rewrote notebooks_dir/<name>.ipynb in place (open, write a
fixed shared '<name>.tmp.ipynb', then tmp.replace(nb_path)), so two
concurrent runs of the same notebook would race on that single shared file
and intermittently crash with FileNotFoundError. _fix_kernel now writes a
private, PID-suffixed copy and never touches nb_path.
"""

import json
import multiprocessing
import os
from pathlib import Path

import pytest

from mkfigs.run import _fix_kernel

NOTEBOOK = {
    "cells": [],
    "metadata": {
        "kernelspec": {
            "display_name": "conda-env-analysis3-25.07-py",
            "name": "conda-env-analysis3-25.07-py",
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


@pytest.fixture
def nb_path(tmp_path):
    p = tmp_path / "Example.ipynb"
    p.write_text(json.dumps(NOTEBOOK))
    return p


def test_fix_kernel_normalises_kernelspec_in_a_private_copy(nb_path):
    original_bytes = nb_path.read_bytes()

    fixed = _fix_kernel(nb_path)

    assert fixed != nb_path
    assert fixed.exists()
    assert str(os.getpid()) in fixed.name

    fixed_doc = json.loads(fixed.read_text())
    assert fixed_doc["metadata"]["kernelspec"]["name"] == "python3"
    assert fixed_doc["metadata"]["kernelspec"]["display_name"] == "Python 3 (ipykernel)"

    # the shared template must be untouched
    assert nb_path.read_bytes() == original_bytes

    fixed.unlink()


def _fix_kernel_worker(nb_path_str: str, results_dir: str, index: int) -> None:
    """Run in a subprocess: fix the shared notebook and record the outcome."""
    from mkfigs.run import _fix_kernel  # re-import: fresh process

    nb_path = Path(nb_path_str)
    try:
        fixed = _fix_kernel(nb_path)
        ok = fixed.exists()
        fixed.unlink(missing_ok=True)
    except Exception:
        ok = False
    (Path(results_dir) / f"{index}.result").write_text("ok" if ok else "fail")


def test_fix_kernel_survives_concurrent_processes_on_shared_notebook(nb_path, tmp_path):
    """Many concurrent processes hitting the same shared notebook must all
    succeed, and the shared template must never be modified or deleted.

    This reproduces the hazard that used to crash overlapping mkfigs.sh
    PBS jobs (see FileNotFoundError on notebooks/<name>.tmp.ipynb ->
    notebooks/<name>.ipynb in the old implementation).
    """
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    original_bytes = nb_path.read_bytes()

    n_workers = 16
    procs = [
        multiprocessing.Process(
            target=_fix_kernel_worker, args=(str(nb_path), str(results_dir), i)
        )
        for i in range(n_workers)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)

    results = [(results_dir / f"{i}.result").read_text() for i in range(n_workers)]
    assert results == ["ok"] * n_workers

    # shared template was never mutated or replaced
    assert nb_path.read_bytes() == original_bytes

    # no leftover private copies
    assert list(nb_path.parent.glob("*.kernel-fixed.*.ipynb")) == []
