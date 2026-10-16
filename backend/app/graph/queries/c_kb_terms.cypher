MATCH (t:Term) WHERE t.id IN $ids
RETURN t.id AS id, t.name AS name, t.ic AS ic, t.cx_system AS system
