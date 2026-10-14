MATCH (t:Term)-[:IS_A*0..]->(a:Term)
WHERE t.id IN $ids
RETURN t.id AS id, collect(DISTINCT a.id) AS ancestors
