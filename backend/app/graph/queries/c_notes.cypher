MATCH (n:Note)-[a:ABOUT]->(x)
WHERE ID(a) >= 0 AND ($target = '' OR x.case_id = $target OR x.id = $target)
RETURN n.id AS id, n.text AS text, n.at AS at, n.by_role AS role,
       labels(x)[0] AS kind, coalesce(x.case_id, x.id) AS target
ORDER BY n.at DESC LIMIT 50
