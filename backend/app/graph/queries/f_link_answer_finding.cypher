MATCH (a:Answer {id: $aid})
MATCH (f:Finding {id: $fid})
MERGE (a)-[:PRODUCED]->(f)
RETURN f.id AS id
