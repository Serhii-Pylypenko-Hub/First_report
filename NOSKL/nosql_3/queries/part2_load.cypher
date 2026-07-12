// Constraints are indexes too and make repeated imports safe and fast.
CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.userId IS UNIQUE;

CREATE CONSTRAINT movie_id_unique IF NOT EXISTS
FOR (m:Movie) REQUIRE m.movieId IS UNIQUE;

CREATE CONSTRAINT genre_name_unique IF NOT EXISTS
FOR (g:Genre) REQUIRE g.name IS UNIQUE;

// Users
LOAD CSV WITH HEADERS FROM 'file:///users.csv' AS row
CALL {
  WITH row
  MERGE (u:User {userId: toInteger(row.userId)})
  SET u.gender = row.gender,
      u.age = toInteger(row.age),
      u.occupation = toInteger(row.occupation),
      u.zip = row.zip
} IN TRANSACTIONS OF 1000 ROWS;

// Movies and normalized Genre nodes. The final parenthesized four digits are year.
LOAD CSV WITH HEADERS FROM 'file:///movies.csv' AS row
CALL {
  WITH row
  MERGE (m:Movie {movieId: toInteger(row.movieId)})
  SET m.title = row.title,
      m.year = CASE
        WHEN row.title =~ '.*\\([0-9]{4}\\)$'
        THEN toInteger(substring(row.title, size(row.title) - 5, 4))
        ELSE null
      END
  WITH m, split(row.genres, '|') AS genres
  UNWIND genres AS genreName
  MERGE (g:Genre {name: genreName})
  MERGE (m)-[:HAS_GENRE]->(g)
} IN TRANSACTIONS OF 1000 ROWS;

// 1,000,209 relationships are imported in bounded transactions.
// MERGE includes endpoints and identifies one rating per user/movie pair.
CALL apoc.periodic.iterate(
  "LOAD CSV WITH HEADERS FROM 'file:///ratings.csv' AS row RETURN row",
  "MATCH (u:User {userId: toInteger(row.userId)})
   MATCH (m:Movie {movieId: toInteger(row.movieId)})
   MERGE (u)-[r:RATED]->(m)
   SET r.rating = toInteger(row.rating),
       r.timestamp = toInteger(row.timestamp)",
  {batchSize: 10000, parallel: false, retries: 3}
) YIELD batches, total, failedOperations, errorMessages
RETURN batches, total, failedOperations, errorMessages;

MATCH (u:User) RETURN count(u) AS users;
MATCH (m:Movie) RETURN count(m) AS movies;
MATCH (g:Genre) RETURN count(g) AS genres;
MATCH ()-[r:RATED]->() RETURN count(r) AS ratings;
