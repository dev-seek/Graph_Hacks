CALL algo.labelPropagation({nodeLabels: ['Case'], relationshipTypes: ['SIMILAR_TO'], maxIterations: 10}) YIELD node, communityId
RETURN communityId, collect(node.case_id) AS cases, count(*) AS size ORDER BY size DESC
