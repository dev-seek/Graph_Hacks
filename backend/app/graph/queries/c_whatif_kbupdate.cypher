CREATE (u:KbUpdate {from_version: $from, to_version: $to, at: $at, tau2: $tau2})
WITH u
UNWIND $cases AS cid
MATCH (c:Case {case_id: cid})
CREATE (u)-[:AFFECTED]->(c)
RETURN count(c) AS affected
