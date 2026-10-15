MATCH (n) WHERE (n:Checkpoint OR n:CheckpointBlob OR n:CheckpointWrite) AND n.thread_id = $thread_id
DELETE n
RETURN count(n) AS n
