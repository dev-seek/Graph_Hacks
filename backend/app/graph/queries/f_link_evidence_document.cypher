MATCH (e:Evidence {id: $ev_id})
MATCH (d:Document {id: $doc_id})
MERGE (e)-[:IN_DOCUMENT]->(d)
RETURN e.id AS id
