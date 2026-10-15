MERGE (s:Snapshot {round: $round, at: $at})
ON CREATE SET s.kb_version = $kb, s.rare_mass = $rare_mass, s.n_findings = $n_findings
RETURN s.round AS round
