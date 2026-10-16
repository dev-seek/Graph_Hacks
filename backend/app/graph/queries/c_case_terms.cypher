MATCH (:Case {case_id: $id})-[:PRESENTED_WITH]->(t:Term)
RETURN t.name AS name ORDER BY name
