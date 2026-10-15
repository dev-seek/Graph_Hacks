MATCH (r:Round {n: $n})-[:ASKED]->(q:Question)
OPTIONAL MATCH (q)-[:ANSWERED]->(a:Answer)
RETURN r.kind AS kind, q.id AS qid, q.term_id AS term_id, q.text AS text, q.why AS why,
       q.how_to_check AS how, q.ask_doctor AS ask_doctor, q.observability AS obs, q.ig AS ig,
       a.value AS answer
ORDER BY q.pos
