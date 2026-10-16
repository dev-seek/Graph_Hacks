MATCH (c:Case {case_id: $id})
RETURN c.case_id AS case_id, c.status AS status, c.age_band AS age_band,
       c.diagnosis_name AS diagnosis, c.kb_version AS kb_version
