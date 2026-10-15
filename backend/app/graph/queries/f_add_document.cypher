MERGE (d:Document {id: $id})
ON CREATE SET d.kind = $kind, d.sha256 = $sha, d.uploaded_at = $at
RETURN d.id AS id
