CALL db.idx.vector.queryNodes('Term', 'embedding', 10, vecf32($vec)) YIELD node, score
RETURN node.id AS id, node.name AS name, score
