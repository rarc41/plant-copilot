"""Download the two TEP training files from the Harvard Dataverse (doi:10.7910/DVN/6C3JR1).

Usage: python data/download_tep.py [--raw-dir data/raw]
"""

import argparse
import hashlib
import shutil
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://dataverse.harvard.edu/api/access/datafile"
DATASET_URL = "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/6C3JR1"
DEFAULT_RAW_DIR = Path(__file__).resolve().parent / "raw"
CHUNK_SIZE = 1024 * 1024

FILES = {
    "TEP_FaultFree_Training.RData": {
        "id": 3031241,
        "md5": "ec126484534331f85001d8c4ebce6d17",
    },
    "TEP_Faulty_Training.RData": {
        "id": 3031242,
        "md5": "c5f594d54c47e620ff877feb58407fda",
    },
}


def _fetch(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response, dest.open("wb") as out:
        shutil.copyfileobj(response, out, CHUNK_SIZE)


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def download_all(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, spec in FILES.items():
        dest = raw_dir / name
        if dest.exists() and _md5(dest) == spec["md5"]:
            print(f"{name}: already downloaded")
            continue

        part = raw_dir / f"{name}.part"
        print(f"{name}: downloading")
        _fetch(f"{BASE_URL}/{spec['id']}", part)
        actual = _md5(part)
        if actual != spec["md5"]:
            part.unlink()
            raise ValueError(f"{name}: MD5 mismatch, expected {spec['md5']}, got {actual}")
        part.replace(dest)
        print(f"{name}: verified {spec['md5']}, {dest.stat().st_size} bytes")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    args = parser.parse_args()
    try:
        download_all(args.raw_dir)
    except urllib.error.HTTPError as error:
        if error.code != 403:
            raise
        parser.exit(
            1,
            f"Dataverse refused the download (HTTP 403).\n"
            f"Download {' and '.join(FILES)} in a browser from\n"
            f"{DATASET_URL}\n"
            f"move them into {args.raw_dir} and run this script again to verify their MD5s.\n",
        )


if __name__ == "__main__":
    main()
