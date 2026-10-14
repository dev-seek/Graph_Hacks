MATCH (t:Term)-[:IS_A*0..]->(a:Term)
WHERE t.depth >= $min_depth AND t.depth < $max_depth
RETURN t.id AS id, collect(DISTINCT a.id) AS ancestors
