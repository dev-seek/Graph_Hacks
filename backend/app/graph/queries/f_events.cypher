MATCH (e:Event)
RETURN e.kind AS kind, e.label AS label, e.at AS at
ORDER BY e.at, e.id
