MATCH (old:Finding {id: $old_id})
MATCH (new:Finding {id: $new_id})
SET old.active = false
MERGE (old)-[:REPLACED_BY]->(new)
RETURN old.id AS old_id, new.id AS new_id
