MATCH (r:Round {n: $n})
MERGE (q:Question {id: $qid})
ON CREATE SET q.term_id = $term_id, q.text = $text, q.observability = $obs, q.ig = $ig,
              q.why = $why, q.how_to_check = $how, q.ask_doctor = $ask_doctor, q.pos = $pos
MERGE (r)-[:ASKED]->(q)
RETURN q.id AS id
