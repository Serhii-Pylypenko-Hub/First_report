"""Convert MovieLens 1M *.dat files (Latin-1, :: delimiter) to UTF-8 CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


SPECS = {
    "movies.dat": (["movieId", "title", "genres"], 3),
    "ratings.dat": (["userId", "movieId", "rating", "timestamp"], 4),
    "users.dat": (["userId", "gender", "age", "occupation", "zip"], 5),
}


def convert(source_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, (header, width) in SPECS.items():
        source = source_dir / filename
        destination = output_dir / filename.replace(".dat", ".csv")
        if not source.is_file():
            raise FileNotFoundError(f"Missing input file: {source}")

        count = 0
        with source.open("r", encoding="latin-1", newline="") as src, destination.open(
            "w", encoding="utf-8", newline=""
        ) as dst:
            writer = csv.writer(dst)
            writer.writerow(header)
            for line_number, raw_line in enumerate(src, start=1):
                row = raw_line.rstrip("\r\n").split("::")
                if len(row) != width:
                    raise ValueError(
                        f"{source}:{line_number}: expected {width} fields, got {len(row)}"
                    )
                writer.writerow(row)
                count += 1
        print(f"{filename}: {count:,} rows -> {destination}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("ml-1m"))
    parser.add_argument("--output", type=Path, default=Path("import"))
    args = parser.parse_args()
    convert(args.source, args.output)


if __name__ == "__main__":
    main()
