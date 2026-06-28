// Run:
// mongosh "$MONGO_URI" --file queries/part4_indexes.js

const dbSpotify = db.getSiblingDB("spotify");

function showExecutionStats(label, cursor) {
  const stats = cursor.explain("executionStats").executionStats;
  print(`\n${label}`);
  printjson({
    executionTimeMillis: stats.executionTimeMillis,
    totalKeysExamined: stats.totalKeysExamined,
    totalDocsExamined: stats.totalDocsExamined,
    nReturned: stats.nReturned,
    winningPlan: stats.executionStages
  });
}

print("\nTask 1. Explain before/after index for pop danceability query");

const query1 = {
  track_genre: "pop",
  "audio_features.danceability": { $gte: 0.7 }
};
const sort1 = { popularity: -1 };

try {
  dbSpotify.tracks.dropIndex("idx_genre_popularity_danceability");
} catch (error) {
  print("Index idx_genre_popularity_danceability did not exist yet.");
}

showExecutionStats(
  "Before index",
  dbSpotify.tracks.find(query1).sort(sort1)
);

dbSpotify.tracks.createIndex(
  {
    track_genre: 1,
    popularity: -1,
    "audio_features.danceability": 1
  },
  { name: "idx_genre_popularity_danceability" }
);

showExecutionStats(
  "After index",
  dbSpotify.tracks.find(query1).sort(sort1)
);

print("\nTask 2. Work music compound index");

const query2 = {
  explicit: false,
  "audio_features.instrumentalness": { $gt: 0.5 },
  "audio_features.speechiness": { $lt: 0.1 }
};

dbSpotify.tracks.createIndex(
  {
    explicit: 1,
    "audio_features.instrumentalness": 1,
    "audio_features.speechiness": 1
  },
  { name: "idx_work_music" }
);

showExecutionStats(
  "Work music query with index",
  dbSpotify.tracks.find(query2)
);

print("\nTask 3. Covered query check");
print("Original query is NOT covered because it has no projection and MongoDB must fetch full documents.");
print("A covered variant must project only indexed fields and exclude _id:");

showExecutionStats(
  "Covered variant",
  dbSpotify.tracks.find(
    {
      track_genre: "pop",
      popularity: { $gte: 70 }
    },
    {
      _id: 0,
      track_genre: 1,
      popularity: 1
    }
  )
);

print("\nCurrent indexes:");
printjson(dbSpotify.tracks.getIndexes());
