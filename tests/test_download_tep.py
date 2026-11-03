import hashlib
import socket
import sys
import urllib.error

import pytest

from data import download_tep

PAYLOAD = b"not really an RData file"
PAYLOAD_MD5 = hashlib.md5(PAYLOAD).hexdigest()


def _fake_fetch(calls):
    def fetch(url, dest):
        calls.append(url)
        dest.write_bytes(PAYLOAD)

    return fetch


def test_network_is_blocked():
    with pytest.raises(RuntimeError, match="Network access is blocked"):
        socket.create_connection(("example.com", 80))


def test_download_requests_only_the_two_training_files(tmp_path, monkeypatch):
    assert set(download_tep.FILES) == {
        "TEP_FaultFree_Training.RData",
        "TEP_Faulty_Training.RData",
    }
    calls = []
    monkeypatch.setattr(download_tep, "_fetch", _fake_fetch(calls))
    monkeypatch.setattr(
        download_tep,
        "FILES",
        {name: {**spec, "md5": PAYLOAD_MD5} for name, spec in download_tep.FILES.items()},
    )

    download_tep.download_all(tmp_path)

    assert sorted(calls) == [
        "https://dataverse.harvard.edu/api/access/datafile/3031241",
        "https://dataverse.harvard.edu/api/access/datafile/3031242",
    ]
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(download_tep.FILES)


def test_download_rejects_wrong_md5(tmp_path, monkeypatch):
    monkeypatch.setattr(download_tep, "_fetch", _fake_fetch([]))

    with pytest.raises(ValueError, match="MD5 mismatch"):
        download_tep.download_all(tmp_path)

    assert list(tmp_path.iterdir()) == []


def _refuse_with(code):
    def fetch(url, dest):
        raise urllib.error.HTTPError(url, code, "Refused", None, None)

    return fetch


def test_download_explains_a_403_instead_of_a_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(download_tep, "_fetch", _refuse_with(403))
    monkeypatch.setattr(sys, "argv", ["download_tep.py", "--raw-dir", str(tmp_path)])

    with pytest.raises(SystemExit) as exit_info:
        download_tep.main()

    assert exit_info.value.code == 1
    message = capsys.readouterr().err
    assert download_tep.DATASET_URL in message
    assert str(tmp_path) in message
    assert all(name in message for name in download_tep.FILES)
    assert list(tmp_path.iterdir()) == []


def test_download_does_not_hide_other_http_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(download_tep, "_fetch", _refuse_with(500))
    monkeypatch.setattr(sys, "argv", ["download_tep.py", "--raw-dir", str(tmp_path)])

    with pytest.raises(urllib.error.HTTPError):
        download_tep.main()


def test_download_skips_file_already_verified(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(download_tep, "_fetch", _fake_fetch(calls))
    monkeypatch.setattr(
        download_tep,
        "FILES",
        {name: {**spec, "md5": PAYLOAD_MD5} for name, spec in download_tep.FILES.items()},
    )
    for name in download_tep.FILES:
        (tmp_path / name).write_bytes(PAYLOAD)

    download_tep.download_all(tmp_path)

    assert calls == []
