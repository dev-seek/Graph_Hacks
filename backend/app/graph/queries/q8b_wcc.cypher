CALL algo.WCC({nodeLabels: ['Case'], relationshipTypes: ['CLOSE_TO']}) YIELD node, componentId
RETURN componentId, collect(node.case_id) AS cases, count(*) AS size ORDER BY size DESC
