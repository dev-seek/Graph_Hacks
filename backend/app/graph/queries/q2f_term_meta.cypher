MATCH (t:Term) WHERE t.id IN $ids
RETURN t.id AS id, t.bg AS bg, t.cx_system AS system, t.ic AS ic
