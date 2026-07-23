# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""
mkfigs — evaluation figure workflow tools for ACCESS model paper repositories.

Public API for use in analysis notebooks:

    from mkfigs import MkmdWriter
    mkmd = MkmdWriter(esm_file, nbname, str(cwd), pm=papermill)
"""

__author__ = "ACCESS-NRI and contributors"
__email__ = "chris.bull@anu.edu.au"
__version__ = "0.1.0"

from .configdoc import (  # noqa: F401
    MkmdWriter,
    FigshareUploader,
    figshare_upload_and_rewrite,
    get_notebook_authors,
)


def get_mkfigs_version() -> str:
    """Best-effort version string for the run-history table and logs.

    mkfigs.sh deliberately runs this package straight off PYTHONPATH from the
    external/access-model-mkfigs git submodule -- "no venv, no pip install"
    (see the comment block at the top of mkfigs.sh) -- so
    importlib.metadata.version() always raises PackageNotFoundError in the
    normal NCI workflow, and every run showed "unknown" in the version
    column. Fall back to this package's own git commit hash in that case.
    """
    import json
    from importlib.metadata import PackageNotFoundError, distribution, version
    from pathlib import Path

    try:
        ver = version("access-model-mkfigs")
        commit = ""
        try:
            direct = json.loads(distribution("access-model-mkfigs").read_text("direct_url.json"))
            commit = direct.get("vcs_info", {}).get("commit_id", "")[:7]
        except Exception:
            pass
        return f"{ver}+{commit}" if commit else ver
    except PackageNotFoundError:
        pass
    except Exception:
        pass

    try:
        import subprocess
        pkg_dir = Path(__file__).resolve().parent
        result = subprocess.run(
            ["git", "-C", str(pkg_dir), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        commit = result.stdout.strip()
        if result.returncode == 0 and commit:
            return f"git+{commit}"
    except Exception:
        pass

    return "unknown"
