MATCH (:Case {case_id: $id})-[:HAS_ANC]->(t:Term)
RETURN t.id AS id
