MATCH (d:CaseDecision)-[u:USED_PROTOCOL]->(p:DiagnosticProtocol)
WHERE ID(u) >= 0
RETURN p.name AS protocol, p.tests AS tests, count(d) AS cases, avg(d.turnaround_days) AS avg_days
ORDER BY avg_days ASC
