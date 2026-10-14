UNWIND $present AS fid
MATCH (f:Term {id: fid})-[:IS_A*0..]->(a:Term)
WITH DISTINCT fid, a
MATCH (a)<-[r:LACKS_PHENOTYPE]-(d:Disease)
WHERE ID(r) >= 0
RETURN DISTINCT fid AS finding, d.id AS disease, d.prior AS prior
