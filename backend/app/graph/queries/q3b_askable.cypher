MATCH (t:Term) WHERE t.id IN $askable
RETURN t.id AS id, t.cx_obs AS obs, t.cx_min_age_months AS min_age, t.cx_system AS system, t.cx_question AS question, t.bg AS bg, t.depth AS depth
