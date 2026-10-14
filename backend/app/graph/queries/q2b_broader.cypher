UNWIND $present AS fid
MATCH p = (f:Term {id: fid})-[:IS_A*1..4]->(a:Term)<-[r:HAS_PHENOTYPE]-(d:Disease)
WHERE a.depth >= 3 AND ID(r) >= 0
RETURN fid AS finding, d.id AS disease, d.prior AS prior, a.id AS via, r.freq AS freq, a.bg AS bg_via, length(p) - 1 AS hops
