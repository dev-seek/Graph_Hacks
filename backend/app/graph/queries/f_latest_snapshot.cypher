MATCH (s:Snapshot)
WITH s ORDER BY s.at DESC LIMIT 1
OPTIONAL MATCH (s)-[r:CANDIDATE]->(d:DiseaseRef)
RETURN s.round AS round, s.at AS at, s.kb_version AS kb_version, s.rare_mass AS rare_mass,
       s.n_findings AS n_findings, d.id AS disease, d.name AS name, r.rank AS rank, r.post AS post
ORDER BY r.rank
