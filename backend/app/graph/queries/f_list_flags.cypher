MATCH (f:Flag)
RETURN f.rule_id AS rule_id, f.level AS level, f.at AS at
ORDER BY f.at
