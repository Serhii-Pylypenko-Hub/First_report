// Highest-degree nodes, with degree split by relationship type.
MATCH (n)
WITH n, count { (n)--() } AS degree
ORDER BY degree DESC
LIMIT 20
RETURN labels(n) AS labels,
       coalesce(n.title, n.name, 'User ' + toString(n.userId)) AS node,
       degree,
       count { (n)-[:RATED]-() } AS ratedDegree,
       count { (n)-[:HAS_GENRE]-() } AS genreDegree
ORDER BY degree DESC;

// Distribution gives a defensible threshold instead of an arbitrary one.
MATCH (n)
WITH labels(n) AS labels, count { (n)--() } AS degree
RETURN labels, count(*) AS nodes,
       round(avg(degree), 2) AS meanDegree,
       percentileCont(degree, 0.95) AS p95,
       percentileCont(degree, 0.99) AS p99,
       max(degree) AS maximum;

// Profile expansion from a known high-degree movie after inspecting query 1.
PROFILE
MATCH (m:Movie)
WITH m, count { (m)<-[:RATED]-() } AS degree
ORDER BY degree DESC LIMIT 1
MATCH (m)<-[r:RATED]-(u:User)
RETURN m.title, count(u) AS raters, avg(r.rating) AS avgRating;
