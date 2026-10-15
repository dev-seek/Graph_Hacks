MERGE (f:Flag {rule_id: $rule_id, quote_hash: $qhash})
ON CREATE SET f.level = $level, f.at = $at, f.quote = $quote
RETURN f.rule_id AS rule_id
