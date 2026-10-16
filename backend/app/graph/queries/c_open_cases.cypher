MATCH (c:Case)
WHERE c.status IN ['open', 'referred']
OPTIONAL MATCH (c)-[:PRESENTED_WITH]->(t:Term)
RETURN c.case_id AS case_id, c.status AS status, c.kb_version AS kb_version, collect(t.id) AS terms
ORDER BY case_id
