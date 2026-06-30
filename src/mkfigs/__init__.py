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
