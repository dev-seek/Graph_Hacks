MATCH (t:Term) WHERE t.id IN $ids
RETURN t.id AS id, t.name AS name
