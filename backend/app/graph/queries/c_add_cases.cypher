UNWIND $rows AS r CREATE (c:Case) SET c += r
