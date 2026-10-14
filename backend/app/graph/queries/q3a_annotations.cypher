MATCH (d:Disease)-[r:HAS_PHENOTYPE]->(t:Term)
WHERE d.id IN $top AND ID(r) >= 0
RETURN d.id AS disease, t.id AS term, r.freq AS freq
