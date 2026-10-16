MATCH (k:Clinician)-[m:MANAGED]->(c:Case)
WHERE ID(m) >= 0
RETURN k.pseudonym AS clinician, k.specialty AS specialty, count(c) AS cases,
       sum(CASE WHEN c.status = 'resolved' THEN 1 ELSE 0 END) AS resolved
ORDER BY cases DESC
