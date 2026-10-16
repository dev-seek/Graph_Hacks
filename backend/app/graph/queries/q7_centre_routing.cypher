// Q7: look-alike resolved cases by IC-weighted shared ancestor terms, who solved them, with which protocol.
// IN-list form of spec Q7 (UNWIND form ran 30x slower on the pinned image; same rows, ADR-0014).
MATCH (c:Case {status: 'resolved'})-[:HAS_ANC]->(t:Term)
WHERE t.id IN $terms AND c.case_id <> $exclude
WITH c, collect(t.name) AS shared, sum(t.ic) AS shared_ic
ORDER BY shared_ic DESC LIMIT 5
MATCH (cl:Clinician)-[m:MANAGED]->(c)
WHERE ID(m) >= 0
OPTIONAL MATCH (c)-[:RESULTED_IN]->(dec:CaseDecision)-[:USED_PROTOCOL]->(p:DiagnosticProtocol)
RETURN c.case_id AS case_id, c.diagnosis_name AS diagnosis, shared, shared_ic,
       cl.pseudonym AS clinician, cl.specialty AS specialty,
       p.name AS protocol, p.tests AS tests, dec.turnaround_days AS turnaround_days
ORDER BY shared_ic DESC
