"""Run the non-destructive BPI Challenge 2017 data-quality pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.cleaning.quality_pipeline import run_quality_checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/raw/BPI_Challenge_2017.xes.gz"),
        help="Path to the BPI Challenge 2017 gzip-compressed XES source.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/generated/data_quality"),
        help="Directory for quality reports and quarantine manifest.",
    )
    args = parser.parse_args()
    report = run_quality_checks(args.source, args.output_dir)
    print(f"Checked {report['records']['traces']} traces and {report['records']['events']} events.")


if __name__ == "__main__":
    main()
