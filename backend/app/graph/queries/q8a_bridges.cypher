CALL algo.betweenness({nodeLabels: ['Case', 'Term'], relationshipTypes: ['PRESENTED_WITH', 'PRESENTED_IN'], samplingSize: 64, samplingSeed: 42})
YIELD node, score
WITH node, score WHERE 'Term' IN labels(node)
RETURN node.id AS term, node.name AS name, score ORDER BY score DESC LIMIT 10
