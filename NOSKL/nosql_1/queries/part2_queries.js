// Run:
// mongosh "$MONGO_URI" --file queries/part2_queries.js

const dbSpotify = db.getSiblingDB("spotify");

print("\nTask 1. Party tracks");
printjson(
  dbSpotify.tracks
    .find(
      {
        "audio_features.danceability": { $gt: 0.7 },
        "audio_features.energy": { $gt: 0.7 },
        duration_ms: { $gte: 180000, $lte: 300000 }
      },
      {
        _id: 0,
        track_name: 1,
        artists: 1,
        track_genre: 1,
        popularity: 1,
        duration_sec: 1,
        "audio_features.danceability": 1,
        "audio_features.energy": 1
      }
    )
    .sort({ popularity: -1 })
    .limit(20)
    .toArray()
);

print("\nTask 2. Artists whose tracks are all popular");
printjson(
  dbSpotify.tracks
    .aggregate([
      { $unwind: "$artists" },
      {
        $group: {
          _id: "$artists",
          track_count: { $sum: 1 },
          min_popularity: { $min: "$popularity" },
          avg_popularity: { $avg: "$popularity" }
        }
      },
      {
        $match: {
          track_count: { $gte: 3 },
          min_popularity: { $gte: 60 }
        }
      },
      {
        $project: {
          _id: 0,
          artist: "$_id",
          track_count: 1,
          min_popularity: 1,
          avg_popularity: { $round: ["$avg_popularity", 1] }
        }
      },
      { $sort: { avg_popularity: -1, track_count: -1, artist: 1 } },
      { $limit: 20 }
    ])
    .toArray()
);

print("\nTask 3. Tempo outliers by genre");
printjson(
  dbSpotify.tracks
    .aggregate(
      [
        {
          $setWindowFields: {
            partitionBy: "$track_genre",
            output: {
              avg_tempo_raw: { $avg: "$audio_features.tempo" },
              std_tempo: { $stdDevPop: "$audio_features.tempo" }
            }
          }
        },
        {
          $addFields: {
            outlier_threshold: {
              $add: ["$avg_tempo_raw", { $multiply: [2, "$std_tempo"] }]
            }
          }
        },
        {
          $match: {
            $expr: {
              $gt: ["$audio_features.tempo", "$outlier_threshold"]
            }
          }
        },
        {
          $group: {
            _id: "$track_genre",
            avg_tempo: { $first: "$avg_tempo_raw" },
            outlier_threshold: { $first: "$outlier_threshold" },
            outlier_tracks: {
              $push: {
                _id: "$_id",
                track_name: "$track_name",
                popularity: "$popularity",
                artists: "$artists",
                audio_features: { tempo: "$audio_features.tempo" }
              }
            }
          }
        },
        {
          $project: {
            _id: 0,
            genre: "$_id",
            avg_tempo: { $round: ["$avg_tempo", 1] },
            outlier_threshold: { $round: ["$outlier_threshold", 1] },
            outlier_tracks: { $slice: ["$outlier_tracks", 5] }
          }
        },
        { $sort: { genre: 1 } },
        { $limit: 5 }
      ],
      { allowDiskUse: true }
    )
    .toArray()
);

print("\nTask 4. Background work tracks");
printjson(
  dbSpotify.tracks
    .find(
      {
        explicit: false,
        "audio_features.loudness": { $lt: -10 },
        "audio_features.speechiness": { $lt: 0.1 },
        "audio_features.instrumentalness": { $gt: 0.5 }
      },
      {
        _id: 0,
        track_name: 1,
        artists: 1,
        track_genre: 1,
        popularity: 1,
        "audio_features.loudness": 1,
        "audio_features.speechiness": 1,
        "audio_features.instrumentalness": 1
      }
    )
    .sort({ popularity: -1 })
    .limit(20)
    .toArray()
);
