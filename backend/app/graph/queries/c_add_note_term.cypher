MATCH (x:Term {id: $target}) CREATE (n:Note {id: $id, text: $text, at: $at, by_role: $role, synthetic: true})-[:ABOUT]->(x) RETURN n.id AS id
