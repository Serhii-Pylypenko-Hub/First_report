// Q1: Thriller films with average rating above 4.0 (and a support count).
MATCH (m:Movie)-[:HAS_GENRE]->(:Genre {name: 'Thriller'})
MATCH (m)<-[r:RATED]-(:User)
WITH m, avg(r.rating) AS avgRating, count(r) AS ratingCount
WHERE avgRating > 4.0
RETURN m.movieId, m.title, round(avgRating, 3) AS avgRating, ratingCount
ORDER BY avgRating DESC, ratingCount DESC;

// Q2: users who gave more than 50 five-star ratings.
MATCH (u:User)-[r:RATED]->(:Movie)
WHERE r.rating = 5
WITH u, count(r) AS fiveStarCount
WHERE fiveStarCount > 50
RETURN u.userId, fiveStarCount
ORDER BY fiveStarCount DESC;

// Q3: movies highly rated by both users 1 and 2.
MATCH (u1:User {userId: 1})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(u2:User {userId: 2})
WHERE r1.rating >= 4 AND r2.rating >= 4
RETURN m.movieId, m.title, r1.rating AS user1Rating, r2.rating AS user2Rating
ORDER BY m.title;

// Q4: genres with consistently high ratings. Count prevents tiny samples dominating.
MATCH (:User)-[r:RATED]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
WITH g, avg(r.rating) AS avgRating, count(r) AS ratingCount
WHERE ratingCount >= 1000
RETURN g.name AS genre, round(avgRating, 3) AS avgRating, ratingCount
ORDER BY avgRating DESC;

// Q5: collaborative filtering for user 1.
// Similarity is the number of commonly liked films; candidates are unseen films liked by peers.
MATCH (target:User {userId: 1})-[tr:RATED]->(common:Movie)<-[pr:RATED]-(peer:User)
WHERE tr.rating >= 4 AND pr.rating >= 4 AND peer <> target
WITH target, peer, count(common) AS similarity
WHERE similarity >= 3
WITH target, peer, similarity
ORDER BY similarity DESC
LIMIT 100
MATCH (peer)-[candidateRating:RATED]->(candidate:Movie)
WHERE candidateRating.rating >= 4
  AND NOT EXISTS { MATCH (target)-[:RATED]->(candidate) }
WITH candidate,
     sum(similarity * candidateRating.rating) AS weightedScore,
     sum(similarity) AS totalSimilarity,
     count(DISTINCT peer) AS peerCount
WHERE peerCount >= 2
RETURN candidate.movieId, candidate.title,
       round(weightedScore / totalSimilarity, 3) AS predictedRating,
       peerCount
ORDER BY predictedRating DESC, peerCount DESC
LIMIT 20;

// Q6: shortest alternating User-Movie chain between users 1 and 2.
// Upper bound avoids accidental unbounded expansion on the dense graph.
MATCH (u1:User {userId: 1}), (u2:User {userId: 2})
MATCH p = shortestPath((u1)-[:RATED*..6]-(u2))
RETURN length(p) AS hops,
       [n IN nodes(p) | CASE WHEN n:User THEN 'User:' + toString(n.userId)
                             ELSE 'Movie:' + n.title END] AS chain;

