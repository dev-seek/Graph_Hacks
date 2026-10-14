MATCH (d:Disease)-[r:HAS_PHENOTYPE]->(:Term)
WHERE ID(r) >= 0
RETURN d.id AS disease, count(r) AS n
