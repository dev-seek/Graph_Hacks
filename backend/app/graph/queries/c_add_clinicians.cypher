UNWIND $rows AS r CREATE (:Clinician {id: r.id, pseudonym: r.pseudonym, specialty: r.specialty, synthetic: true})
