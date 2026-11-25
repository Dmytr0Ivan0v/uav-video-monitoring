"""Provenance of site files: output + cv_course sources -> manifest entries with sha256."""

import subprocess
from pathlib import Path

from portfolio_export.outputs import sha256


def course_git(course: Path) -> dict:
    def git(*args: str) -> str:
        # --no-optional-locks: status must not refresh the index of the read-only checkout
        return subprocess.run(['git', '--no-optional-locks', '-C', str(course), *args],
                              check=True, capture_output=True, text=True).stdout.strip()
    return {'commit': git('rev-parse', 'HEAD'), 'dirty': bool(git('status', '--porcelain'))}


def entry(output: Path, sources: list[Path], course: Path) -> dict:
    return {
        'sha256': sha256(output),
        'sources': {p.relative_to(course).as_posix(): sha256(p) for p in sorted(set(sources))},
    }
