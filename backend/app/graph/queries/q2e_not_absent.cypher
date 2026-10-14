UNWIND $absent AS fid
MATCH (f:Term {id: fid})-[:IS_A*0..]->(a:Term)<-[r:LACKS_PHENOTYPE]-(d:Disease)
WHERE d.id IN $candidates AND ID(r) >= 0
RETURN DISTINCT fid AS finding, d.id AS disease
