UNWIND $rows AS r CREATE (:DiagnosticProtocol {id: r.id, name: r.name, tests: r.tests, version: 'v1', synthetic: true})
