import os
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import DATA_PATH, ensure_dataset


def main() -> None:
    df = ensure_dataset(DATA_PATH)
    print(f"Loaded {len(df)} records")
    print(df[["title", "year", "category"]].head(5).to_string(index=False))
    print(f"Saved dataset to {DATA_PATH}")


if __name__ == "__main__":
    main()
