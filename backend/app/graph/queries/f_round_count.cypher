MATCH (r:Round {kind: $kind})
RETURN count(r) AS n
