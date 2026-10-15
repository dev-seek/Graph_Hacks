MATCH (c:Case)-[:PRESENTED_WITH]->(t:Term)
WHERE t.id IN $terms
WITH c, collect(DISTINCT t.id) AS shared, sum(t.ic) AS shared_ic
OPTIONAL MATCH (c)-[:RESULTED_IN]->(d:CaseDecision)-[:USED_PROTOCOL]->(p:DiagnosticProtocol)
OPTIONAL MATCH (d)-[:DECIDED_BY]->(k:Clinician)
RETURN c.case_id AS case_id, c.diagnosis_name AS diagnosis, shared, shared_ic,
       k.pseudonym AS clinician, k.specialty AS specialty, p.name AS protocol, p.tests AS tests,
       d.turnaround_days AS turnaround_days
ORDER BY shared_ic DESC LIMIT 5
