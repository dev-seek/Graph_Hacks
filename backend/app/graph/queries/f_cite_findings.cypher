MATCH (a:Artifact {id: $id})
UNWIND $cites AS fid
MATCH (f:Finding {id: fid})
MERGE (a)-[:CITES]->(f)
RETURN count(f) AS n
