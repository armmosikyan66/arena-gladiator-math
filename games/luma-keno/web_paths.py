#!/usr/bin/env python3
"""Locate the web client's `src/data` directory.

Monorepo layout first, then the two-sibling-repos layout. Never mkdir the
target: writing into a directory that does not exist yet means we guessed
wrong about the checkout, and silently creating a phantom `web/` is how a
regenerated table ends up never reaching the client.
"""

from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))

_CANDIDATES = (
    ("..", "..", "..", "web", "src", "data"),
    ("..", "..", "..", "lumen-keno", "src", "data"),
)


def resolve_web_file(filename: str, env_var: str) -> str:
    """Absolute path to `filename` inside the client's data dir.

    `env_var` overrides with a full path to the file, not the directory.
    """
    override = os.environ.get(env_var)
    if override:
        return os.path.abspath(override)
    for candidate in _CANDIDATES:
        directory = os.path.abspath(os.path.join(HERE, *candidate))
        if os.path.isdir(directory):
            return os.path.join(directory, filename)
    searched = "\n  ".join(
        os.path.abspath(os.path.join(HERE, *c)) for c in _CANDIDATES
    )
    raise SystemExit(
        "cannot find the web app's src/data directory. Searched:\n  "
        f"{searched}\nSet {env_var} to the target {filename} path."
    )
