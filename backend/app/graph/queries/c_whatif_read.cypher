MATCH (u:KbUpdate)-[a:AFFECTED]->(c:Case)
WHERE ID(a) >= 0
RETURN u.from_version AS from_version, u.to_version AS to_version, u.tau2 AS tau2,
       c.case_id AS case_id, c.rare_mass_prev AS prev, c.rare_mass AS now
ORDER BY c.case_id
