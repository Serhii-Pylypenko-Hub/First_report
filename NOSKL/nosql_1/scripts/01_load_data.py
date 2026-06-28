import os

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from tqdm import tqdm


load_dotenv()

MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.getenv("MONGO_DB", "spotify")
CSV_PATH = os.getenv("CSV_PATH", "dataset.csv")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))

INT_COLS = ["popularity", "duration_ms", "key", "mode", "time_signature"]
FLOAT_COLS = [
    "danceability",
    "energy",
    "loudness",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
]


def main() -> None:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"CSV file not found: {CSV_PATH}. Put the Kaggle dataset here or set CSV_PATH in .env."
        )

    print(f"Reading CSV: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)

    required = {"artists", "track_name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

    print("Normalizing types...")
    if "explicit" in df.columns:
        df["explicit"] = df["explicit"].astype(bool)

    for col in INT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    for col in FLOAT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)

    before = len(df)
    df = df[~(df["artists"].isna() | df["track_name"].isna())]
    print(f"Rows kept after basic cleanup: {len(df)} of {before}")

    records = df.to_dict("records")

    print("Dropping old tracks_raw collection...")
    db["tracks_raw"].drop()

    print(f"Loading {len(records)} tracks into {DB_NAME}.tracks_raw...")
    for i in tqdm(range(0, len(records), BATCH_SIZE)):
        batch = records[i : i + BATCH_SIZE]
        if batch:
            db["tracks_raw"].insert_many(batch, ordered=False)

    print(f"Loaded documents: {db['tracks_raw'].count_documents({})}")
    print("Sample raw document:")
    print(db["tracks_raw"].find_one())


if __name__ == "__main__":
    main()
