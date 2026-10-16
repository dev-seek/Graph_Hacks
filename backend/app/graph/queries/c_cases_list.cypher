MATCH (c:Case)
WHERE $status = '' OR c.status = $status
RETURN c.case_id AS case_id, c.status AS status, c.age_band AS age_band, c.diagnosis_name AS diagnosis
ORDER BY c.case_id LIMIT $limit
