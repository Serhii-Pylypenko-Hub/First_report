// Clean up stale in-memory projections before rerunning individual sections:
CALL gds.graph.drop('movieRatings', false);
CALL gds.graph.drop('userSimilarity', false);

// 5.1 PageRank: directed RATED edges point from users to movies.
CALL gds.graph.project(
  'movieRatings',
  ['User', 'Movie'],
  {RATED: {orientation: 'NATURAL'}}
) YIELD graphName, nodeCount, relationshipCount;

CALL gds.pageRank.stream('movieRatings', {maxIterations: 20, dampingFactor: 0.85})
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS node, score
WHERE node:Movie
RETURN node.movieId, node.title, score
ORDER BY score DESC
LIMIT 20;

CALL gds.graph.drop('movieRatings');

// 5.2 Materialize bounded user similarity edges from commonly liked movies.
MATCH (u1:User)-[r1:RATED]->(m:Movie)<-[r2:RATED]-(u2:User)
WHERE r1.rating >= 4 AND r2.rating >= 4 AND u1.userId < u2.userId
WITH u1, u2, count(m) AS weight
WHERE weight >= 3
WITH u1, u2, weight
ORDER BY weight DESC
LIMIT 50000
MERGE (u1)-[sim:SIMILAR]->(u2)
SET sim.weight = weight, sim.cost = 1.0 / weight;

CALL gds.graph.project(
  'userSimilarity',
  'User',
  {SIMILAR: {orientation: 'UNDIRECTED', properties: ['weight', 'cost']}}
) YIELD graphName, nodeCount, relationshipCount;

CALL gds.louvain.write(
  'userSimilarity',
  {relationshipWeightProperty: 'weight', writeProperty: 'communityId'}
) YIELD communityCount, modularity, modularities
RETURN communityCount, modularity, modularities;

MATCH (u:User)
RETURN u.communityId AS community, count(*) AS users
ORDER BY users DESC
LIMIT 10;

// Top three genres among highly rated films for each of the ten largest communities.
MATCH (u:User)
WITH u.communityId AS community, count(*) AS users
ORDER BY users DESC LIMIT 10
MATCH (u:User {communityId: community})-[r:RATED]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
WHERE r.rating >= 4
WITH community, users, g.name AS genre, count(*) AS likes
ORDER BY community, likes DESC
WITH community, users, collect({genre: genre, likes: likes})[0..3] AS topGenres
RETURN community, users, topGenres
ORDER BY users DESC;

// 5.3 Dijkstra. Replace IDs with a pair present in the projected component.
MATCH (source:User {userId: 17}), (target:User {userId: 18})
CALL gds.shortestPath.dijkstra.stream('userSimilarity', {
  sourceNode: source,
  targetNode: target,
  relationshipWeightProperty: 'cost'
})
YIELD totalCost, nodeIds, costs
RETURN totalCost,
       [nodeId IN nodeIds | gds.util.asNode(nodeId).userId] AS userPath,
       size(nodeIds) - 1 AS hops,
       costs;

CALL gds.graph.drop('userSimilarity');
MATCH ()-[sim:SIMILAR]->() DELETE sim;

