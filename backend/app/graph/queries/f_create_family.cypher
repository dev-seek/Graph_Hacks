MERGE (f:Family {id: $id})
ON CREATE SET f.created_at = $at, f.kb_version = $kb, f.consent_centre = $consent,
              f.token_hash = $token_hash, f.clinician_code = $code, f.demo = $demo
MERGE (f)-[:HAS_CHILD]->(c:Child)
ON CREATE SET c.age_months_at_start = $age, c.sex = $sex
RETURN f.id AS id
