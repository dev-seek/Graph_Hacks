MATCH (f:Finding {id: $id})
SET f.active = false
RETURN f.id AS id
