MERGE (s:Story {text_hash: $hash})
ON CREATE SET s.at = $at
RETURN s.text_hash AS hash
