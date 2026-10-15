CREATE (a:Artifact {id: $id, kind: $kind, version: $version, at: $at, payload: $payload})
RETURN a.id AS id
