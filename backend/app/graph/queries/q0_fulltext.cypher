CALL db.idx.fulltext.queryNodes('Term', $q) YIELD node, score
RETURN node.id AS id, node.name AS name, score ORDER BY score DESC LIMIT 10
