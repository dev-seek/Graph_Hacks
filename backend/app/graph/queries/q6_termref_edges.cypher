MATCH (t:Term)-[:IS_A]->(p:Term)
WHERE t.id IN $ids AND p.id IN $ids
RETURN t.id AS child, p.id AS parent
