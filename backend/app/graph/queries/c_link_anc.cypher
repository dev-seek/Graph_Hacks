UNWIND $rows AS r MATCH (c:Case {case_id: r.c}), (t:Term {id: r.t}) CREATE (c)-[:HAS_ANC]->(t)
