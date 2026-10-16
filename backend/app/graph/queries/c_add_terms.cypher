UNWIND $rows AS r CREATE (:Term {id: r.id, name: r.name, ic: r.ic, system: r.system})
