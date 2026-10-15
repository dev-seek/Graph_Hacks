MERGE (f:Finding {id: $id})
ON CREATE SET f.term_id = $term_id, f.plain_label = $label, f.status = $status,
              f.source = $source, f.onset_months = $onset, f.recorded_at = $at, f.active = true
MERGE (t:TermRef {id: $term_id})
MERGE (f)-[:OBSERVED_AS]->(t)
MERGE (e:Evidence {id: $ev_id})
ON CREATE SET e.kind = $ev_kind, e.quote = $quote, e.start = $start, e.end = $end, e.at = $at
MERGE (f)-[:SUPPORTED_BY]->(e)
RETURN f.id AS id
