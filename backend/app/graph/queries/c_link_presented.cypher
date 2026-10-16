UNWIND $rows AS r MATCH (c:Case {case_id: r.c}), (t:Term {id: r.t}) CREATE (c)-[:PRESENTED_WITH {status: 'present', source: r.source}]->(t), (t)-[:PRESENTED_IN]->(c)
