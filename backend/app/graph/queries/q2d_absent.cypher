UNWIND $absent AS fid
MATCH (f:Term {id: fid})<-[:IS_A*0..10]-(x:Term)<-[r:HAS_PHENOTYPE]-(d:Disease)
WHERE d.id IN $candidates AND ID(r) >= 0
RETURN fid AS finding, d.id AS disease, max(r.freq) AS F
