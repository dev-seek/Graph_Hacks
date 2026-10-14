MATCH (f:Term {id: $fid})<-[:IS_A*0..10]-(x:Term)
WITH DISTINCT x
MATCH (x)<-[r:HAS_PHENOTYPE]-(d:Disease)
WHERE ID(r) >= 0
RETURN $fid AS finding, d.id AS disease, d.prior AS prior, max(r.freq) AS F
