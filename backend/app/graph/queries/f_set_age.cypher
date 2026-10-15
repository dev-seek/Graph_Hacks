MATCH (f:Family {id: $id})-[:HAS_CHILD]->(c:Child)
SET c.age_months_at_start = $age, c.sex = coalesce($sex, c.sex)
RETURN c.age_months_at_start AS age
