MATCH (r:Round)
RETURN r.n AS n, r.kind AS kind
ORDER BY r.n DESC LIMIT 1
