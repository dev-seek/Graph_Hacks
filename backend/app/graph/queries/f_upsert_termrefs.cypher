UNWIND $terms AS t
MERGE (n:TermRef {id: t.id})
SET n.name = t.name
RETURN count(n) AS n
