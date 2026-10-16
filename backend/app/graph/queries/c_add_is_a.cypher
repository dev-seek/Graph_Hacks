UNWIND $rows AS r MATCH (a:Term {id: r.s}), (b:Term {id: r.o}) CREATE (a)-[:IS_A]->(b)
