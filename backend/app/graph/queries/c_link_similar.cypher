UNWIND $rows AS r MATCH (a:Case {case_id: r.a}), (b:Case {case_id: r.b}) CREATE (a)-[:SIMILAR_TO {score: r.score}]->(b)
