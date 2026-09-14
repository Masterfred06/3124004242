"""Command-line entry point for the plagiarism checker."""

from __future__ import annotations

import sys

from plagiarism_checker import run_cli


if __name__ == "__main__":
    raise SystemExit(run_cli(sys.argv[1:]))
