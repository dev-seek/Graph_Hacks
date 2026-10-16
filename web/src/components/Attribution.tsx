"use client";

import { useLoad } from "./Journey";

type Version = {
  kb?: { hpo_version?: string; product1_version?: string; phenopacket_store_version?: string };
};

/** Versions come from /api/version; pinned fallbacks keep the statement complete if the API is down. */
export function useVersions() {
  const v = useLoad<Version>("/version", null);
  return {
    hpo: v.data?.kb?.hpo_version ?? "2026-09-01",
    orpha: (v.data?.kb?.product1_version ?? "2026-06-23").slice(0, 10),
    store: v.data?.kb?.phenopacket_store_version ?? "0.1.27",
  };
}

export function HpoStatement({ version }: { version: string }) {
  return (
    <>
      This service/product uses the Human Phenotype Ontology (version {version}). Find out more at{" "}
      <a href="http://www.human-phenotype-ontology.org">http://www.human-phenotype-ontology.org</a>
    </>
  );
}

export function OrphaCitation({ version }: { version: string }) {
  return (
    <>
      Orphadata Science: Free access data from Orphanet. © INSERM 1999. Available on{" "}
      <a href="http://sciences.orphadata.com/">http://sciences.orphadata.com/</a>. Data version {version}.
    </>
  );
}
