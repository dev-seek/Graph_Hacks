UNWIND $absent AS aid
MATCH (t:Term {id: aid})-[:IS_A*1..]->(a:Term)
WHERE a.id IN $absent
RETURN DISTINCT t.id AS redundant
