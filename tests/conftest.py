import socket
from pathlib import Path

import pandas as pd
import pyreadr
import pytest

TAG_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "tag_map.csv"
FIXTURE_RUNS = 7
FIXTURE_SAMPLES = 6
CONTINUOUS_TAGS = [f"xmeas_{i}" for i in range(1, 23)]

# The synthetic run that trips: continuous signals freeze from this sample on.
SHUTDOWN_FAULT = 6
SHUTDOWN_RUN = 2
SHUTDOWN_SAMPLE = 4


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Any test that reaches the network fails, so the suite never downloads the dataset."""

    def refuse(*args, **kwargs):
        raise RuntimeError("Network access is blocked during tests")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def signal_value(tag_index, fault, run, sample):
    """A value unique to each tag and row, so a scrambled rename cannot go unnoticed."""
    return tag_index * 1000 + fault * 10 + run + sample / 100


def _build_frame(faults, tags):
    rows = [
        (fault, run, sample)
        for fault in faults
        for run in range(1, FIXTURE_RUNS + 1)
        for sample in range(1, FIXTURE_SAMPLES + 1)
    ]
    frame = pd.DataFrame(rows, columns=["faultNumber", "simulationRun", "sample"])
    signals = {
        tag: signal_value(index, frame["faultNumber"], frame["simulationRun"], frame["sample"])
        for index, tag in enumerate(tags, start=1)
    }
    return pd.concat([frame, pd.DataFrame(signals)], axis=1)


def _freeze_after_shutdown(frame):
    tripped = (frame["faultNumber"] == SHUTDOWN_FAULT) & (frame["simulationRun"] == SHUTDOWN_RUN)
    frozen = frame.loc[tripped & (frame["sample"] == SHUTDOWN_SAMPLE), CONTINUOUS_TAGS]
    after = tripped & (frame["sample"] > SHUTDOWN_SAMPLE)
    frame.loc[after, CONTINUOUS_TAGS] = frozen.to_numpy().repeat(after.sum(), axis=0)
    return frame


@pytest.fixture
def make_raw_dir(tmp_path_factory):
    """Write tiny synthetic .RData files shaped like the real ones; never committed.

    Key column types differ between the two files, as they do in the real data.
    """

    def make(change_normal=None, change_faulty=None):
        tags = pd.read_csv(TAG_MAP_PATH)["original_tag"].tolist()
        normal = _build_frame([0], tags).astype(
            {"faultNumber": "float64", "simulationRun": "float64", "sample": "int32"}
        )
        faulty = _freeze_after_shutdown(_build_frame(range(1, 21), tags)).astype(
            {"faultNumber": "int32", "simulationRun": "float64", "sample": "int32"}
        )
        if change_normal:
            normal = change_normal(normal)
        if change_faulty:
            faulty = change_faulty(faulty)

        raw_dir = tmp_path_factory.mktemp("raw")
        pyreadr.write_rdata(
            str(raw_dir / "TEP_FaultFree_Training.RData"), normal, df_name="fault_free_training"
        )
        pyreadr.write_rdata(
            str(raw_dir / "TEP_Faulty_Training.RData"), faulty, df_name="faulty_training"
        )
        return raw_dir

    return make
