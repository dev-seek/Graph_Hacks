MATCH (t:Term) WHERE t.id IN $ids
RETURN t.id AS id, t.name AS name, t.cx_plain_label AS plain, t.cx_question AS question,
       t.cx_why AS why, t.cx_how_to_check AS how, t.cx_obs AS obs, t.cx_system AS system
