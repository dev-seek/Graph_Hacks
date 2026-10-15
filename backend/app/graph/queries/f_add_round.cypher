MERGE (r:Round {n: $n})
ON CREATE SET r.kind = $kind, r.asked_at = $at
RETURN r.n AS n
