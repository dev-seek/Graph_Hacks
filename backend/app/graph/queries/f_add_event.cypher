MERGE (e:Event {id: $id})
ON CREATE SET e.kind = $kind, e.label = $label, e.at = $at
RETURN e.id AS id
