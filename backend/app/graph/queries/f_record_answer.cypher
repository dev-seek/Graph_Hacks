MATCH (q:Question {id: $qid})
MERGE (a:Answer {id: $aid})
ON CREATE SET a.value = $value, a.at = $at
MERGE (q)-[:ANSWERED]->(a)
RETURN a.id AS id
