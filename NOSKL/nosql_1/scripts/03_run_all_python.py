import json
import os
from pathlib import Path

import pandas as pd
from bson import json_util
from dotenv import load_dotenv
from pymongo import MongoClient
from tqdm import tqdm


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.getenv("MONGO_DB", "spotify")
CSV_PATH = ROOT / os.getenv("CSV_PATH", "dataset.csv")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))
OUTPUTS_DIR = ROOT / "outputs"

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


def to_jsonable(value):
    return json.loads(json_util.dumps(value))


def save_report(report):
    OUTPUTS_DIR.mkdir(exist_ok=True)
    path = OUTPUTS_DIR / "results.json"
    path.write_text(
        json.dumps(to_jsonable(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nReport saved to: {path}")


def load_data(db, report):
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    print(f"\n[1/5] Loading CSV into {DB_NAME}.tracks_raw")
    df = pd.read_csv(CSV_PATH)

    required = {"track_id", "artists", "track_name", "popularity", "track_genre"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")

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

    db.tracks_raw.drop()
    records = df.to_dict("records")
    for i in tqdm(range(0, len(records), BATCH_SIZE), desc="insert batches"):
        batch = records[i : i + BATCH_SIZE]
        if batch:
            db.tracks_raw.insert_many(batch, ordered=False)

    report["load"] = {
        "csv_path": str(CSV_PATH),
        "rows_in_csv": before,
        "loaded_to_tracks_raw": db.tracks_raw.count_documents({}),
        "sample": db.tracks_raw.find_one({}, {"_id": 0}),
    }


def transform_data(db, report):
    print(f"\n[2/5] Transforming tracks_raw -> tracks")
    db.tracks.drop()

    pipeline = [
        {
            "$match": {
                "track_name": {"$exists": True, "$ne": None},
                "artists": {"$exists": True, "$ne": None},
            }
        },
        {
            "$project": {
                "_id": 0,
                "track_id": 1,
                "track_name": 1,
                "album_name": 1,
                "explicit": 1,
                "popularity": 1,
                "duration_ms": 1,
                "track_genre": 1,
                "artists_raw": "$artists",
                "audio_features": {
                    "danceability": "$danceability",
                    "energy": "$energy",
                    "loudness": "$loudness",
                    "speechiness": "$speechiness",
                    "acousticness": "$acousticness",
                    "instrumentalness": "$instrumentalness",
                    "liveness": "$liveness",
                    "valence": "$valence",
                    "tempo": "$tempo",
                    "key": "$key",
                    "mode": "$mode",
                    "time_signature": "$time_signature",
                },
                "duration_sec": {"$round": [{"$divide": ["$duration_ms", 1000]}, 1]},
                "popularity_tier": {
                    "$switch": {
                        "branches": [
                            {"case": {"$gte": ["$popularity", 70]}, "then": "high"},
                            {"case": {"$gte": ["$popularity", 40]}, "then": "medium"},
                        ],
                        "default": "low",
                    }
                },
            }
        },
        {
            "$addFields": {
                "artists": {
                    "$filter": {
                        "input": {
                            "$map": {
                                "input": {"$split": ["$artists_raw", ";"]},
                                "as": "artist",
                                "in": {"$trim": {"input": "$$artist"}},
                            }
                        },
                        "as": "artist",
                        "cond": {"$ne": ["$$artist", ""]},
                    }
                }
            }
        },
        {"$project": {"artists_raw": 0}},
        {"$out": "tracks"},
    ]
    list(db.tracks_raw.aggregate(pipeline, allowDiskUse=True))

    report["transform"] = {
        "tracks_count": db.tracks.count_documents({}),
        "sample": db.tracks.find_one({}, {"_id": 0}),
    }


def run_part2_queries(db, report):
    print("\n[3/5] Running Part 2 queries")
    report["part2_queries"] = {}

    report["part2_queries"]["party_tracks"] = list(
        db.tracks.find(
            {
                "audio_features.danceability": {"$gt": 0.7},
                "audio_features.energy": {"$gt": 0.7},
                "duration_ms": {"$gte": 180000, "$lte": 300000},
            },
            {
                "_id": 0,
                "track_name": 1,
                "artists": 1,
                "popularity": 1,
                "audio_features.danceability": 1,
                "audio_features.energy": 1,
            },
        )
        .sort("popularity", -1)
        .limit(10)
    )

    report["part2_queries"]["popular_artists"] = list(
        db.tracks.aggregate(
            [
                {"$unwind": "$artists"},
                {
                    "$group": {
                        "_id": "$artists",
                        "track_count": {"$sum": 1},
                        "min_popularity": {"$min": "$popularity"},
                        "avg_popularity": {"$avg": "$popularity"},
                    }
                },
                {"$match": {"track_count": {"$gte": 3}, "min_popularity": {"$gte": 60}}},
                {
                    "$project": {
                        "_id": 0,
                        "artist": "$_id",
                        "track_count": 1,
                        "min_popularity": 1,
                        "avg_popularity": {"$round": ["$avg_popularity", 1]},
                    }
                },
                {"$sort": {"avg_popularity": -1, "track_count": -1, "artist": 1}},
                {"$limit": 20},
            ]
        )
    )

    report["part2_queries"]["tempo_outliers_by_genre"] = list(
        db.tracks.aggregate(
            [
                {
                    "$setWindowFields": {
                        "partitionBy": "$track_genre",
                        "output": {
                            "avg_tempo_raw": {"$avg": "$audio_features.tempo"},
                            "std_tempo": {"$stdDevPop": "$audio_features.tempo"},
                        },
                    }
                },
                {
                    "$addFields": {
                        "outlier_threshold": {
                            "$add": ["$avg_tempo_raw", {"$multiply": [2, "$std_tempo"]}]
                        }
                    }
                },
                {"$match": {"$expr": {"$gt": ["$audio_features.tempo", "$outlier_threshold"]}}},
                {
                    "$group": {
                        "_id": "$track_genre",
                        "avg_tempo": {"$first": "$avg_tempo_raw"},
                        "outlier_threshold": {"$first": "$outlier_threshold"},
                        "outlier_tracks": {
                            "$push": {
                                "_id": "$_id",
                                "track_name": "$track_name",
                                "popularity": "$popularity",
                                "artists": "$artists",
                                "audio_features": {"tempo": "$audio_features.tempo"},
                            }
                        },
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "genre": "$_id",
                        "avg_tempo": {"$round": ["$avg_tempo", 1]},
                        "outlier_threshold": {"$round": ["$outlier_threshold", 1]},
                        "outlier_tracks": {"$slice": ["$outlier_tracks", 10]},
                    }
                },
                {"$sort": {"genre": 1}},
                {"$limit": 20},
            ],
            allowDiskUse=True,
        )
    )

    report["part2_queries"]["background_work_tracks"] = list(
        db.tracks.find(
            {
                "explicit": False,
                "audio_features.loudness": {"$lt": -10},
                "audio_features.speechiness": {"$lt": 0.1},
                "audio_features.instrumentalness": {"$gt": 0.5},
            },
            {"_id": 0, "track_name": 1, "artists": 1, "track_genre": 1, "audio_features": 1},
        ).limit(10)
    )


def run_part3_aggregations(db, report):
    print("\n[4/5] Running Part 3 aggregation pipelines")
    report["part3_aggregations"] = {}

    report["part3_aggregations"]["top_artists"] = list(
        db.tracks.aggregate(
            [
                {"$unwind": "$artists"},
                {"$group": {"_id": "$artists", "tracks": {"$sum": 1}, "avg_popularity": {"$avg": "$popularity"}}},
                {"$match": {"tracks": {"$gte": 5}}},
                {"$sort": {"avg_popularity": -1}},
                {"$limit": 10},
            ]
        )
    )

    report["part3_aggregations"]["mood_distribution"] = list(
        db.tracks.aggregate(
            [
                {
                    "$addFields": {
                        "mood": {
                            "$switch": {
                                "branches": [
                                    {
                                        "case": {
                                            "$and": [
                                                {"$gte": ["$audio_features.valence", 0.5]},
                                                {"$gte": ["$audio_features.energy", 0.5]},
                                            ]
                                        },
                                        "then": "happy",
                                    },
                                    {
                                        "case": {
                                            "$and": [
                                                {"$lt": ["$audio_features.valence", 0.5]},
                                                {"$gte": ["$audio_features.energy", 0.5]},
                                            ]
                                        },
                                        "then": "angry",
                                    },
                                    {
                                        "case": {
                                            "$and": [
                                                {"$gte": ["$audio_features.valence", 0.5]},
                                                {"$lt": ["$audio_features.energy", 0.5]},
                                            ]
                                        },
                                        "then": "calm",
                                    },
                                ],
                                "default": "sad",
                            }
                        }
                    }
                },
                {"$group": {"_id": "$mood", "tracks": {"$sum": 1}, "avg_popularity": {"$avg": "$popularity"}}},
                {"$sort": {"tracks": -1}},
            ]
        )
    )

    report["part3_aggregations"]["danceable_genres"] = list(
        db.tracks.aggregate(
            [
                {
                    "$group": {
                        "_id": "$track_genre",
                        "tracks": {"$sum": 1},
                        "avg_danceability": {"$avg": "$audio_features.danceability"},
                        "avg_energy": {"$avg": "$audio_features.energy"},
                        "avg_valence": {"$avg": "$audio_features.valence"},
                    }
                },
                {"$match": {"tracks": {"$gte": 100}}},
                {
                    "$addFields": {
                        "dance_score": {
                            "$round": [
                                {
                                    "$avg": [
                                        "$avg_danceability",
                                        "$avg_energy",
                                        "$avg_valence",
                                    ]
                                },
                                3,
                            ]
                        }
                    }
                },
                {"$sort": {"dance_score": -1}},
                {"$limit": 10},
            ]
        )
    )

    db.artist_stats.drop()
    list(
        db.tracks.aggregate(
            [
                {"$unwind": "$artists"},
                {"$group": {"_id": "$artists", "artist_track_count": {"$sum": 1}, "artist_avg_popularity": {"$avg": "$popularity"}}},
                {"$out": "artist_stats"},
            ]
        )
    )

    report["part3_aggregations"]["lookup_demo"] = list(
        db.tracks.aggregate(
            [
                {"$match": {"popularity": {"$gte": 85}}},
                {"$unwind": "$artists"},
                {"$lookup": {"from": "artist_stats", "localField": "artists", "foreignField": "_id", "as": "artist_info"}},
                {"$unwind": "$artist_info"},
                {"$project": {"_id": 0, "track_name": 1, "artists": 1, "popularity": 1, "artist_info": 1}},
                {"$sort": {"popularity": -1}},
                {"$limit": 10},
            ]
        )
    )


def explain_find(db, filter_doc, sort_doc=None, projection_doc=None):
    command = {"find": "tracks", "filter": filter_doc}
    if sort_doc:
        command["sort"] = sort_doc
    if projection_doc:
        command["projection"] = projection_doc
    return db.command("explain", command, verbosity="executionStats")["executionStats"]


def compact_stats(stats):
    return {
        "executionTimeMillis": stats.get("executionTimeMillis"),
        "totalKeysExamined": stats.get("totalKeysExamined"),
        "totalDocsExamined": stats.get("totalDocsExamined"),
        "nReturned": stats.get("nReturned"),
    }


def run_part4_indexes(db, report):
    print("\n[5/5] Running Part 4 indexes and explain")
    report["part4_indexes"] = {}

    query1 = {"track_genre": "pop", "audio_features.danceability": {"$gte": 0.7}}
    sort1 = {"popularity": -1}

    try:
        db.tracks.drop_index("idx_genre_popularity_danceability")
    except Exception:
        pass

    before = explain_find(db, query1, sort1)
    db.tracks.create_index(
        [("track_genre", 1), ("popularity", -1), ("audio_features.danceability", 1)],
        name="idx_genre_popularity_danceability",
    )
    after = explain_find(db, query1, sort1)

    query2 = {
        "explicit": False,
        "audio_features.instrumentalness": {"$gt": 0.5},
        "audio_features.speechiness": {"$lt": 0.1},
    }
    db.tracks.create_index(
        [("explicit", 1), ("audio_features.instrumentalness", 1), ("audio_features.speechiness", 1)],
        name="idx_work_music",
    )
    work_music = explain_find(db, query2)

    covered = explain_find(
        db,
        {"track_genre": "pop", "popularity": {"$gte": 70}},
        projection_doc={"_id": 0, "track_genre": 1, "popularity": 1},
    )

    report["part4_indexes"] = {
        "pop_danceability_before_index": compact_stats(before),
        "pop_danceability_after_index": compact_stats(after),
        "work_music_with_index": compact_stats(work_music),
        "covered_query_variant": compact_stats(covered),
        "indexes": list(db.tracks.list_indexes()),
    }


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    client.admin.command("ping")
    db = client[DB_NAME]

    report = {"database": DB_NAME}
    load_data(db, report)
    transform_data(db, report)
    run_part2_queries(db, report)
    run_part3_aggregations(db, report)
    run_part4_indexes(db, report)
    save_report(report)

    print("\nDone. Open outputs/results.json to copy results into README.md.")


if __name__ == "__main__":
    main()
