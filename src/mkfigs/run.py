# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""
mkfigs-run – run evaluation notebooks via papermill.

Called by mkfigs.sh after modules are loaded.  Receives ENAME, ESMDIR, and
WFOLDER as command-line arguments.

Usage (via mkfigs.sh):
    qsub mkfigs.sh

After the job completes, run mkfigs-pushit on a login node to upload figures
to Figshare and prepare the git commit.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

from . import get_mkfigs_version


def _extract_notebook_error(rendered_path: Path) -> str | None:
    """Return the last error cell output from a rendered notebook, ANSI-stripped."""
    try:
        with open(rendered_path) as f:
            nb = json.load(f)
        for cell in reversed(nb.get("cells", [])):
            for output in cell.get("outputs", []):
                if output.get("output_type") == "error":
                    ename = output.get("ename", "")
                    evalue = output.get("evalue", "")
                    tb = "\n".join(output.get("traceback", []))
                    tb = re.sub(r'\x1b\[[0-9;]*m', '', tb)
                    return f"{ename}: {evalue}\n{tb}"
    except Exception:
        pass
    return None


def _fix_kernel(nb_path: Path) -> Path:
    """Normalise the notebook kernel to 'python3' so papermill can execute it.

    Notebooks opened interactively in ARE may have a kernel name like
    'conda-env-analysis3-25.07-py' that does not exist on the command line.
    This writes the kernel-fixed notebook to a private, PID-suffixed copy
    next to nb_path and returns that path — nb_path itself is never
    modified. Concurrent mkfigs-run jobs (e.g. multiple experiments queued
    at once, all reading the same shared notebooks/<name>.ipynb template)
    used to race on an in-place tmp.replace(nb_path) of that shared file;
    writing a private copy per run removes the shared mutable state.
    """
    with open(nb_path) as f:
        d = json.load(f)
    d["metadata"]["kernelspec"]["display_name"] = "Python 3 (ipykernel)"
    d["metadata"]["kernelspec"]["name"] = "python3"
    fixed = nb_path.with_name(f"{nb_path.stem}.kernel-fixed.{os.getpid()}.ipynb")
    with open(fixed, "w") as f:
        json.dump(d, f)
    return fixed


def _check_nci_environment() -> None:
    try:
        import nci_ipynb  # noqa: F401
    except ModuleNotFoundError:
        sys.exit(
            "ERROR: nci_ipynb not found.\n"
            "Please load the conda environment before running this script:\n\n"
            "  module purge\n"
            "  module use /g/data/xp65/public/modules\n"
            "  module load conda/analysis3\n"
        )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--ename",   required=True, help="Experiment name (ENAME)")
    p.add_argument("--esmdir",  required=True, help="Path to ESM datastore JSON")
    p.add_argument("--wfolder", required=True, help="Repo root folder")
    return p.parse_args()


def setup_logging(log_file: Path) -> logging.Logger:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s %(levelname)-8s %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(log_file)),
        ],
    )
    return logging.getLogger(__name__)


def run_notebook(nb: str, esmdir: str, ofol: Path, notebooks_dir: Path) -> bool:
    """Strip outputs, run via papermill, convert to markdown. Returns True on success."""
    nb_path = notebooks_dir / f"{nb}.ipynb"
    fixed_path = _fix_kernel(nb_path)

    try:
        rendered = str(ofol / f"{nb}_rendered.ipynb")
        result = subprocess.run(
            [
                "papermill", str(fixed_path), rendered,
                "-p", "esm_file", esmdir,
                "-p", "papermill", "True",
                "-p", "cwd", str(ofol) + "/",
                "-p", "nbname", f"{nb}.ipynb",
            ],
            cwd=str(notebooks_dir),
        )
    finally:
        fixed_path.unlink(missing_ok=True)

    subprocess.run(
        ["jupyter", "nbconvert", "--to", "markdown", rendered],
        check=False,
    )
    return result.returncode == 0


def main() -> None:
    _check_nci_environment()
    args = parse_args()

    ename  = args.ename
    esmdir = args.esmdir
    notebooks_dir = Path(args.wfolder) / "notebooks"

    ofol  = notebooks_dir / f"mkfigs_output_{ename}"
    mdfol = ofol / "mkmd"
    mdfol.mkdir(parents=True, exist_ok=True)

    log = setup_logging(mdfol / "mkfigs_run.log")

    mkfigs_ver = get_mkfigs_version()

    log.info("Experiment            : %s", ename)
    log.info("ESMDIR                : %s", esmdir)
    log.info("Output dir            : %s", ofol)
    log.info("Log file              : %s", mdfol / "mkfigs_run.log")
    log.info("access-model-mkfigs   : %s", mkfigs_ver)

    notebooks_env = os.environ.get("MKFIGS_NOTEBOOKS", "")
    if not notebooks_env:
        log.error("MKFIGS_NOTEBOOKS env var not set — run via mkfigs.sh")
        sys.exit(1)
    notebooks = [n for n in notebooks_env.split(":") if n]

    succeeded: list[str] = []
    failed:    list[str] = []

    log.info("")
    log.info("Running %d notebooks ...", len(notebooks))
    log.info("")
    for nb in notebooks:
        log.info("START  %s", nb)
        ok = run_notebook(nb, esmdir, ofol, notebooks_dir)
        if ok:
            succeeded.append(nb)
            log.info("OK     %s", nb)
        else:
            failed.append(nb)
            log.error("FAILED %s", nb)

    log.info("")
    log.info("=" * 56)
    log.info("Run complete")
    log.info("=" * 56)
    log.info("Output folder : %s", ofol)
    log.info("Markdown dir  : %s", mdfol)
    log.info("Log file      : %s", mdfol / "mkfigs_run.log")

    if succeeded:
        log.info("Succeeded (%d): %s", len(succeeded), ", ".join(succeeded))
    if failed:
        log.error("FAILED    (%d): %s", len(failed), ", ".join(failed))
        errors_log = mdfol / "mkfigs_errors.log"
        with open(errors_log, "w") as ef:
            for nb in failed:
                rendered = ofol / f"{nb}_rendered.ipynb"
                ef.write(f"{'=' * 56}\n")
                ef.write(f"FAILED: {nb}\n")
                ef.write(f"{'=' * 56}\n")
                error = _extract_notebook_error(rendered)
                ef.write(error + "\n" if error else "(no error output found in rendered notebook)\n")
                ef.write("\n")
        log.error("Error details: %s", errors_log)

    venv = notebooks_dir / f"mkfigs_output_{ename}" / "venv"
    sep = "=" * 56
    print()
    print(sep)
    print("Run complete — next steps on a login node:")
    print(sep)
    print()
    print("  # 1. Load the environment and activate the venv")
    print("  module purge")
    print("  module use /g/data/xp65/public/modules")
    print("  module load conda/analysis3")
    print(f"  source {venv}/bin/activate")
    print()
    print("  # 2. Dry-run first to review what will be committed")
    print(f"  mkfigs-pushit --ename {ename} --dry-run")
    print()
    print("  # 3. Push figures to Figshare and prepare the git commit")
    print(f"  mkfigs-pushit --ename {ename}")
    print()
    print("  # 4. Log in to Figshare and publish the article, then verify")
    print(f"  mkfigs-pushit --ename {ename} --check-figshare-upload")
    print(sep)
    print()


if __name__ == "__main__":
    main()
