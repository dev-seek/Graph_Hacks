MATCH (a:Artifact {kind: $kind})
RETURN a.id AS id, a.version AS version, a.at AS at, a.payload AS payload
ORDER BY a.version DESC, a.at DESC LIMIT 1
