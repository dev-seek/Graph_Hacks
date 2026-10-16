UNWIND $rows AS r MATCH (k:Clinician {id: r.k}), (c:Case {case_id: r.c}) CREATE (k)-[:MANAGED {from: r.from, to: r.to}]->(c)
