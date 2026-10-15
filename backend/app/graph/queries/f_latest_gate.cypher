MATCH (g:Gate)
RETURN g.kind AS kind, g.at AS at, g.inputs_json AS inputs, g.rule AS rule
ORDER BY g.at DESC LIMIT 1
