MATCH (f:Finding)
WHERE f.active = true OR $include_inactive
OPTIONAL MATCH (f)-[:SUPPORTED_BY]->(e:Evidence)
RETURN f.id AS id, f.term_id AS term_id, f.plain_label AS label, f.status AS status,
       f.source AS source, f.onset_months AS onset, f.recorded_at AS at, f.active AS active,
       e.quote AS quote, e.start AS start, e.end AS end
ORDER BY f.recorded_at, f.id
