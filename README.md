# access-model-mkfigs

[![CI](https://github.com/ACCESS-NRI/access-model-mkfigs/actions/workflows/ci.yml/badge.svg)](https://github.com/ACCESS-NRI/access-model-mkfigs/actions/workflows/ci.yml)

Evaluation figure workflow tools for ACCESS model paper repositories.

* License: Apache-2.0

## Overview

`access-model-mkfigs` provides the `mkfigs` Python package and three command-line tools
used by ACCESS model paper repositories (e.g. `access-om3-paper-1`, `access-cm3-paper-1`)
to run analysis notebooks via papermill, upload figures and rendered notebooks to Figshare,
and build a MkDocs documentation site.

## Installation

```bash
pip install git+https://github.com/ACCESS-NRI/access-model-mkfigs.git
```

## Usage

In paper repo notebooks:

```python
from mkfigs import MkmdWriter
mkmd = MkmdWriter(esm_file, nbname, str(cwd), pm=papermill)
```

CLI entry points (called from `mkfigs.sh` or interactively on a login node):

```bash
mkfigs-run     --ename ENAME --esmdir ESMDIR --wfolder WFOLDER
mkfigs-pushit  [--dry-run] [--skip-figshare] [--check-figshare-upload]
mkfigs-restore [--ename ENAME] [--force]
```

## Credits

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the
[`ACCESS-NRI/cookiecutter-pypackage-access`](https://github.com/ACCESS-NRI/cookiecutter-pypackage-access)
project template.
