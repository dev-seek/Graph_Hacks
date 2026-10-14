UNWIND $present AS pid
MATCH (t:Term {id: pid})-[:IS_A*1..]->(a:Term)
WHERE a.id IN $present
RETURN DISTINCT a.id AS redundant
