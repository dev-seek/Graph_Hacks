MATCH (f:Family {id: $id})-[:HAS_CHILD]->(c:Child)
RETURN f.id AS id, f.kb_version AS kb_version, f.consent_centre AS consent,
       c.age_months_at_start AS age_months, c.sex AS sex, f.created_at AS created_at
