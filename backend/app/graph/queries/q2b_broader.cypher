UNWIND $present AS fid
MATCH p = (f:Term {id: fid})-[:IS_A*1..4]->(a:Term)
WHERE a.depth >= 3
WITH DISTINCT fid, a, length(p) AS hops
MATCH (a)<-[r:HAS_PHENOTYPE]-(d:Disease)
WHERE ID(r) >= 0
RETURN fid AS finding, d.id AS disease, d.prior AS prior, a.id AS via, r.freq AS freq, a.bg AS bg_via, hops
