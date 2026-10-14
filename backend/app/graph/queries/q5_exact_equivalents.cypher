MATCH (t:Disease {id: $target})
OPTIONAL MATCH (t)-[e:EQUIVALENT_TO]-(o:Disease)
WHERE e.relation = 'E'
RETURN t.id AS target, collect(o.id) AS exact_equivalents
