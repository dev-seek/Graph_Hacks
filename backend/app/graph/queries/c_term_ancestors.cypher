MATCH (t:Term) WHERE t.id IN $ids
MATCH (t)-[:IS_A*0..25]->(a:Term)
RETURN DISTINCT a.id AS id
