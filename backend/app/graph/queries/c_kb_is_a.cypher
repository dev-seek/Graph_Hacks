MATCH (a:Term)-[:IS_A]->(b:Term)
WHERE a.id IN $ids AND b.id IN $ids
RETURN a.id AS s, b.id AS o
