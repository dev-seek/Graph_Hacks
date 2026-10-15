UNWIND $edges AS e
MATCH (a:TermRef {id: e.child})
MATCH (b:TermRef {id: e.parent})
MERGE (a)-[:IS_A]->(b)
RETURN count(e) AS n
