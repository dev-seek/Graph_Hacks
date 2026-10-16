"use client";

import { HpoStatement, OrphaCitation, useVersions } from "@/components/Attribution";
import { Card } from "@/components/ui";
import { AI_DISCLOSURE } from "@/copy";

const LIMITS = [
  "Not clinically validated. Simulated answers are cleaner than real parents' answers.",
  "Knowledge is only as good as the HPO annotations. Leaving out OMIM-sourced IEA annotations lowers coverage for some diseases that only have OMIM sources.",
  "The 'common explanation' class, multi-system decay and organ dampening are heuristics, tuned on synthetic everyday cases.",
  "Some published cases may share papers with our knowledge base. We guard against this with a leave-publication-out build for testing.",
  "Clinic data (clinicians, protocols, decisions) is synthetic and labelled as such.",
  "Published cases may appear in language-model training data. That affects the language-model baseline, not our scoring.",
  "English only for now. Lay-term coverage depends on HPO layperson synonyms and our generated plain labels.",
  "A regulatory route is needed before any real clinical use.",
];

export default function About() {
  const v = useVersions();
  return (
    <div className="max-w-[65ch] space-y-6">
      <h1 className="text-3xl">About Constellation</h1>
      <Card aria-labelledby="a-how">
        <h2 id="a-how" className="text-xl">
          How it works
        </h2>
        <p className="mt-2">
          You tell the story. Plain-language questions come in small rounds. Ordinary code, reading a FalkorDB
          graph of medical knowledge, decides when the picture is strong enough to say &ldquo;see a doctor&rdquo;
          and when to prepare notes for a specialist. Doctors get a clinical view with sources; a centre can
          share memory across cases.
        </p>
        <p className="mt-2">
          Constellation does not diagnose. For general explanation only: it uses rare-disease phenotype knowledge
          to decide which questions are most useful, but never shows a parent disease names or scores.
        </p>
      </Card>

      <Card aria-labelledby="a-data">
        <h2 id="a-data" className="text-xl">
          Data sources and versions
        </h2>
        <ul className="mt-2 list-disc space-y-2 pl-5">
          <li>
            <HpoStatement version={v.hpo} />. HPO files are used unmodified; our plain labels are kept
            separate. Citation: Gargano MA, et al. The Human Phenotype Ontology in 2024: phenotypes around
            the world. Nucleic Acids Res. 2024;52(D1):D1333–D1346.
          </li>
          <li>
            <OrphaCitation version={v.orpha} /> Changes made: prevalence classes converted to approximate
            numeric priors. Orphadata makes no endorsement of this service.
          </li>
          <li>
            GA4GH Phenopacket Store, release {v.store} (BSD-3-Clause, © 2022 Monarch Initiative). Citation:
            Danis et al., A corpus of GA4GH phenopackets: case-level phenotyping for genomic diagnostics and
            discovery. <em>HGG Advances</em> 2025, 6(1):100371. No endorsement by the Monarch Initiative is
            implied.
          </li>
          <li>Embedding model BAAI/bge-small-en-v1.5 (MIT), run locally.</li>
        </ul>
        <p className="mt-2 text-muted">
          OMIM-sourced annotations with IEA evidence are left out. Example families and the centre&apos;s cases
          are made up or built from de-identified published cases.
        </p>
      </Card>

      <Card aria-labelledby="a-lim">
        <h2 id="a-lim" className="text-xl">
          Limitations
        </h2>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          {LIMITS.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </Card>

      <Card aria-labelledby="a-ai">
        <h2 id="a-ai" className="text-xl">
          How AI is used
        </h2>
        <ul className="mt-2 list-disc space-y-2 pl-5">
          {AI_DISCLOSURE.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
        <p className="mt-2 text-muted">
          What a person wrote, reviewed or decided is recorded in the project&apos;s AI-use file in the
          repository.
        </p>
      </Card>

      <Card aria-labelledby="a-contact">
        <h2 id="a-contact" className="text-xl">
          Contact
        </h2>
        <p className="mt-2">Questions, corrections or deletion requests: see the project page on the hackathon submission.</p>
      </Card>
    </div>
  );
}
