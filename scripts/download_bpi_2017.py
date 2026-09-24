"""BPI Challenge 2017 Dataset Downloader.

Downloads the raw gzip-compressed XES event log from Figshare / 4TU.ResearchData,
validates MD5 checksum, and saves to data/raw/BPI_Challenge_2017.xes.gz safely.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "data" / "source_manifest.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "raw" / "BPI_Challenge_2017.xes.gz"
DEFAULT_URL = "https://ndownloader.figshare.com/files/24044117"
DEFAULT_MD5 = "10b37a2f78e870d78406198403ff13d2"


def load_manifest() -> dict[str, str | int]:
    """Load dataset configuration from data/source_manifest.json if present."""
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "download_url": data.get("download_url", DEFAULT_URL),
                    "expected_md5": data.get("expected_md5", DEFAULT_MD5),
                }
        except Exception:
            pass
    return {"download_url": DEFAULT_URL, "expected_md5": DEFAULT_MD5}


def download_dataset(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    force: bool = False,
    url: str | None = None,
    expected_md5: str | None = None,
) -> Path:
    """Download BPI 2017 dataset with checksum verification and atomic placement."""
    manifest_info = load_manifest()
    download_url = url or str(manifest_info["download_url"])
    target_md5 = (expected_md5 or str(manifest_info["expected_md5"])).lower()

    output_path = Path(output_path).resolve()

    if output_path.exists() and not force:
        print(f"Dataset already exists at: {output_path} (use --force to overwrite)")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    print(f"Downloading BPI Challenge 2017 dataset from {download_url}...")
    md5_hash = hashlib.md5()

    try:
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(req) as resp, open(temp_path, "wb") as f_out:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                f_out.write(chunk)
                md5_hash.update(chunk)

        actual_md5 = md5_hash.hexdigest().lower()
        if actual_md5 != target_md5:
            if temp_path.exists():
                temp_path.unlink()
            raise ValueError(
                f"Checksum verification failed! Expected MD5: {target_md5}, received: {actual_md5}"
            )

        temp_path.replace(output_path)
        print(f"Successfully downloaded and verified dataset: {output_path}")
        return output_path

    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Download and verify the BPI Challenge 2017 dataset."
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Target output path for BPI_Challenge_2017.xes.gz",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing dataset if present",
    )
    args = parser.parse_args()

    try:
        download_dataset(output_path=args.output_path, force=args.force)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
