// Run:
// mongosh "$MONGO_URI" --file scripts/02_transform.js

const databaseName = "spotify";
const dbSpotify = db.getSiblingDB(databaseName);

print(`Using database: ${databaseName}`);
print("Dropping old tracks collection...");
dbSpotify.tracks.drop();

print("Transforming tracks_raw -> tracks...");

dbSpotify.tracks_raw.aggregate(
  [
    {
      $match: {
        track_name: { $exists: true, $ne: null },
        artists: { $exists: true, $ne: null }
      }
    },
    {
      $project: {
        _id: 0,
        track_id: 1,
        track_name: 1,
        album_name: 1,
        explicit: 1,
        popularity: 1,
        duration_ms: 1,
        track_genre: 1,
        artists_raw: "$artists",
        audio_features: {
          danceability: "$danceability",
          energy: "$energy",
          loudness: "$loudness",
          speechiness: "$speechiness",
          acousticness: "$acousticness",
          instrumentalness: "$instrumentalness",
          liveness: "$liveness",
          valence: "$valence",
          tempo: "$tempo",
          key: "$key",
          mode: "$mode",
          time_signature: "$time_signature"
        },
        duration_sec: {
          $round: [{ $divide: ["$duration_ms", 1000] }, 1]
        },
        popularity_tier: {
          $switch: {
            branches: [
              { case: { $gte: ["$popularity", 70] }, then: "high" },
              { case: { $gte: ["$popularity", 40] }, then: "medium" }
            ],
            default: "low"
          }
        }
      }
    },
    {
      $addFields: {
        artists: {
          $filter: {
            input: {
              $map: {
                input: { $split: ["$artists_raw", ";"] },
                as: "artist",
                in: { $trim: { input: "$$artist" } }
              }
            },
            as: "artist",
            cond: { $ne: ["$$artist", ""] }
          }
        }
      }
    },
    {
      $project: {
        artists_raw: 0
      }
    },
    {
      $out: "tracks"
    }
  ],
  { allowDiskUse: true }
);

print(`tracks count: ${dbSpotify.tracks.countDocuments({})}`);
print("Sample transformed document:");
printjson(dbSpotify.tracks.findOne());
