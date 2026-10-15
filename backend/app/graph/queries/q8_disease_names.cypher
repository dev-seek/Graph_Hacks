MATCH (d:Disease) WHERE d.id IN $ids
RETURN d.id AS id, d.name AS name
