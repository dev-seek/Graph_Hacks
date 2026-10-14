MATCH p = (f:Term {id: $finding})-[:IS_A*0..6]->(a:Term)<-[r:HAS_PHENOTYPE]-(d:Disease {id: $disease})
WHERE ID(r) >= 0
RETURN [n IN nodes(p) | n.id] AS path, length(p) AS len ORDER BY len ASC LIMIT 1
