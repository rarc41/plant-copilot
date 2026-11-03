"""Raw TEP data and the built database must never reach git."""

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)


@pytest.mark.parametrize(
    "path",
    [
        "data/raw/TEP_FaultFree_Training.RData",
        "data/raw/TEP_Faulty_Training.RData",
        "data/raw/TEP_Faulty_Training.RData.part",
        "somewhere/else/copy.RData",
        "data/tep.duckdb",
        "data/tep.duckdb.wal",
        "data/tep.duckdb.tmp",
        "data/tep.duckdb.tmp.wal",
        "somewhere/else/copy.duckdb",
    ],
)
def test_raw_and_db_files_are_ignored(path):
    assert _git("check-ignore", "-q", path).returncode == 0


def test_no_raw_or_db_files_are_tracked():
    result = _git("ls-files")
    assert result.returncode == 0
    tracked = [
        name
        for name in result.stdout.splitlines()
        if name.startswith("data/raw/") or name.endswith((".RData", ".rda", ".duckdb"))
    ]
    assert tracked == []
