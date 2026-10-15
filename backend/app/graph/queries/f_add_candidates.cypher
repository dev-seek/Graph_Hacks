MATCH (s:Snapshot {round: $round, at: $at})
UNWIND $cands AS c
MERGE (d:DiseaseRef {id: c.id})
SET d.name = c.name
MERGE (s)-[r:CANDIDATE {rank: c.rank}]->(d)
SET r.post = c.post
RETURN count(c) AS n
