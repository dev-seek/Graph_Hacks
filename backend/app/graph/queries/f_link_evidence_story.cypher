MATCH (e:Evidence {id: $ev_id})
MATCH (s:Story {text_hash: $hash})
MERGE (e)-[:IN_STORY]->(s)
RETURN e.id AS id
