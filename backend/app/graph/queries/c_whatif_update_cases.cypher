UNWIND $rows AS r MATCH (c:Case {case_id: r.c}) SET c.kb_version = $to, c.rare_mass_prev = r.prev, c.rare_mass = r.now
