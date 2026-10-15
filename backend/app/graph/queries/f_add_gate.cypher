MATCH (s:Snapshot {round: $round, at: $snap_at})
CREATE (g:Gate {id: $id, kind: $kind, at: $at, inputs_json: $inputs, rule: $rule})
CREATE (g)-[:BASED_ON]->(s)
RETURN g.id AS id
