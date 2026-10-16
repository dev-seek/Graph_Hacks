MATCH (c:Case)
WITH count(c) AS cases, sum(CASE WHEN c.status = 'resolved' THEN 1 ELSE 0 END) AS resolved
MATCH (k:Clinician)
WITH cases, resolved, count(k) AS clinicians
MATCH (p:DiagnosticProtocol)
RETURN cases, resolved, clinicians, count(p) AS protocols
