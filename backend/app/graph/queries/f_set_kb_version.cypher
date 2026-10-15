MATCH (f:Family {id: $id})
SET f.kb_version = $kb
RETURN f.kb_version AS kb_version
