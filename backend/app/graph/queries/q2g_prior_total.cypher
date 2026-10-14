MATCH (d:Disease)-[r:HAS_PHENOTYPE]->(:Term)
WHERE ID(r) >= 0
WITH DISTINCT d
RETURN sum(d.prior) AS total, count(d) AS n
